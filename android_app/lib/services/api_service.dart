// api_service.dart — REST API client for BlackBugsAI admin panel

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/models.dart';
import '../models/gcp_models.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  final String baseUrl;
  final String adminToken;

  ApiService({required this.baseUrl, required this.adminToken});

  static const String _demoModeKey = 'demo_mode';
  static const String _demoTasksKey = 'demo_tasks';

  static Future<bool> isDemoMode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_demoModeKey) ?? false;
  }

  static Future<void> setDemoMode(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_demoModeKey, value);
  }

  /// Создаёт экземпляр ApiService из сохранённых настроек SharedPreferences
  static Future<ApiService> fromSavedConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('base_url') ?? '';
    final token = prefs.getString('admin_token') ?? '';
    return ApiService(baseUrl: baseUrl, adminToken: token);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'X-Admin-Token': adminToken,
      };

  Future<bool> _shouldUseDemo() async {
    final demo = await ApiService.isDemoMode();
    return demo || baseUrl.isEmpty;
  }

  Future<dynamic> _get(String path) async {
    final uri = Uri.parse('$baseUrl$path');
    final response =
        await http.get(uri, headers: _headers).timeout(const Duration(seconds: 10));
    return _handle(response);
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await http
        .post(uri, headers: _headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 10));
    return _handle(response);
  }

  dynamic _handle(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return {};
      return jsonDecode(response.body);
    }
    String msg = 'HTTP ${response.statusCode}';
    try {
      final j = jsonDecode(response.body);
      msg = j['error'] ?? j['message'] ?? msg;
    } catch (_) {}
    throw ApiException(response.statusCode, msg);
  }

  // ─── System ───────────────────────────────────────────────────────────────

  Future<bool> ping() async {
    if (await _shouldUseDemo()) return true;
    try {
      final data = await _get('/health');
      return data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  Future<SystemStats> getStats() async {
    final data = await _get('/api/status');
    return SystemStats.fromJson(data);
  }

  // ─── Tasks ────────────────────────────────────────────────────────────────

  Future<List<Task>> getTasks({String? status, int limit = 20}) async {
    final useDemo = await _shouldUseDemo();
    if (!useDemo) {
      try {
        String path = '/api/tasks?limit=$limit';
        if (status != null) path += '&status=$status';
        final data = await _get(path) as List;
        return data.map((j) => Task.fromJson(j)).toList();
      } catch (_) {
        if (!await ApiService.isDemoMode()) rethrow;
      }
    }

    final tasks = await _loadDemoTasks();
    final filtered = status == null
        ? tasks
        : tasks.where((t) => t.status == status).toList();
    return filtered.take(limit).toList();
  }

  Future<Task> getTask(String taskId) async {
    final useDemo = await _shouldUseDemo();
    if (!useDemo) {
      try {
        final data = await _get('/api/tasks/$taskId');
        return Task.fromJson(data);
      } catch (_) {
        if (!await ApiService.isDemoMode()) rethrow;
      }
    }

    final tasks = await _loadDemoTasks();
    return tasks.firstWhere(
      (t) => t.id == taskId,
      orElse: () => _seedDemoTasks().first,
    );
  }

  Future<String> createTask({
    required String userId,
    required String type,
    required String title,
    Map<String, dynamic>? payload,
  }) async {
    final useDemo = await _shouldUseDemo();
    if (!useDemo) {
      final data = await _post('/api/tasks', {
        'user_id': userId,
        'type': type,
        'title': title,
        'payload': payload ?? {},
      });
      return data['task_id'] ?? '';
    }

    final demoTasks = await _loadDemoTasks();
    final id = 'demo-${DateTime.now().millisecondsSinceEpoch}';
    final now = DateTime.now();
    demoTasks.insert(
      0,
      Task(
        id: id,
        userId: userId,
        type: type,
        title: title,
        status: 'pending',
        createdAt: now,
        startedAt: now,
        finishedAt: now,
        result: payload?['text'] ?? payload?['prompt'] ?? '',
      ),
    );
    await _saveDemoTasks(demoTasks);
    return id;
  }

  Future<bool> cancelTask(String taskId) async {
    if (await _shouldUseDemo()) {
      final tasks = await _loadDemoTasks();
      for (int i = 0; i < tasks.length; i++) {
        if (tasks[i].id == taskId) {
          tasks[i] = Task(
            id: tasks[i].id,
            userId: tasks[i].userId,
            type: tasks[i].type,
            title: tasks[i].title,
            status: 'cancelled',
            result: tasks[i].result,
            error: tasks[i].error,
            artifacts: tasks[i].artifacts,
            retryCount: tasks[i].retryCount,
            maxRetries: tasks[i].maxRetries,
            createdAt: tasks[i].createdAt,
            startedAt: tasks[i].startedAt,
            finishedAt: DateTime.now(),
          );
          await _saveDemoTasks(tasks);
          return true;
        }
      }
      return false;
    }

    try {
      await _post('/api/tasks/$taskId/cancel', {});
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> retryTask(String taskId) async {
    if (await _shouldUseDemo()) {
      final tasks = await _loadDemoTasks();
      for (int i = 0; i < tasks.length; i++) {
        if (tasks[i].id == taskId) {
          tasks[i] = Task(
            id: tasks[i].id,
            userId: tasks[i].userId,
            type: tasks[i].type,
            title: tasks[i].title,
            status: 'running',
            result: tasks[i].result,
            error: null,
            artifacts: tasks[i].artifacts,
            retryCount: tasks[i].retryCount + 1,
            maxRetries: tasks[i].maxRetries,
            createdAt: tasks[i].createdAt,
            startedAt: DateTime.now(),
            finishedAt: null,
          );
          await _saveDemoTasks(tasks);
          return true;
        }
      }
      return false;
    }

    try {
      await _post('/api/tasks/$taskId/retry', {});
      return true;
    } catch (_) {
      return false;
    }
  }

  // ─── Agents ───────────────────────────────────────────────────────────────

  Future<List<AgentInfo>> getAgents() async {
    if (await _shouldUseDemo()) {
      return _demoAgents();
    }
    try {
      final data = await _get('/api/agents') as List;
      return data.map((j) => AgentInfo.fromJson(j)).toList();
    } catch (_) {
      // Return mock agents if endpoint not available
      return _demoAgents();
    }
  }

  // ─── LLM Providers ────────────────────────────────────────────────────────

  Future<List<LlmProvider>> getProviders() async {
    if (await _shouldUseDemo()) {
      return _demoProviders();
    }
    try {
      final data = await _get('/api/providers/status') as Map<String, dynamic>;
      // Backend returns active/best provider info, not a list
      // Return a synthetic list from the status response
      final providers = <LlmProvider>[];
      final activeLlm = data['active_llm'] as String?;
      final bestLlm = data['best_llm'] as String?;
      if (activeLlm != null) {
        final modelsList = <String>[activeLlm];
        if (bestLlm != null && bestLlm != activeLlm) {
          modelsList.add(bestLlm);
        }
        providers.add(LlmProvider(
          id: activeLlm,
          name: activeLlm,
          enabled: true,
          isDefault: true,
          models: modelsList,
          currentModel: bestLlm ?? activeLlm,
        ));
      }
      return providers;
    } catch (_) {
      if (await ApiService.isDemoMode()) {
        return _demoProviders();
      }
      return [];
    }
  }

  // ─── Shell / Admin ────────────────────────────────────────────────────────

  Future<String> runShell(String command) async {
    if (await _shouldUseDemo()) {
      return 'DEMO SHELL> $command\n(no remote server connected)';
    }
    final data = await _post('/api/shell', {'cmd': command});
    return data['output'] ?? '';
  }

  Future<Map<String, dynamic>> getSystemInfo() async {
    return await _get('/api/sysinfo') as Map<String, dynamic>;
  }

  // ─── Logs ─────────────────────────────────────────────────────────────────

  Future<List<String>> getLogs({int lines = 50}) async {
    if (await _shouldUseDemo()) {
      return _demoLogs().take(lines).toList();
    }
    try {
      final data = await _get('/api/logs?lines=$lines');
      return List<String>.from(data['lines'] ?? []);
    } catch (_) {
      if (await ApiService.isDemoMode()) {
        return _demoLogs().take(lines).toList();
      }
      return [];
    }
  }

  // ─── Docker Control ───────────────────────────────────────────────────────

  /// Получает статус Docker-контейнеров (GET /api/rc/docker)
  Future<DockerContainerStatus> getDockerStatus() async {
    final data = await _get('/api/rc/docker') as Map<String, dynamic>;
    // Backend returns {ok, containers: [...]}
    final containers = data['containers'] as List?;
    if (containers != null && containers.isNotEmpty) {
      return DockerContainerStatus.fromJson(containers.first as Map<String, dynamic>);
    }
    return const DockerContainerStatus(
      id: '',
      name: 'unknown',
      status: 'unknown',
      image: '',
      uptime: '-',
      cpuPercent: 0,
      memoryMb: 0,
    );
  }

  /// Выполняет shell-команду на сервере (POST /api/rc/shell)
  Future<String> runShellCommand(String cmd) async {
    final data = await _post('/api/rc/shell', {'cmd': cmd});
    return data['output'] ?? data['result'] ?? '';
  }

  /// Выполняет действие Docker для контейнера (POST /api/rc/docker/action)
  Future<String> runDockerCommand(String action, {String? container}) async {
    final payload = <String, dynamic>{'action': action};
    if (container != null && container.isNotEmpty) {
      payload['container'] = container;
    }

    final data = await _post('/api/rc/docker/action', payload);
    return data['output'] ?? data['result'] ?? data['message'] ?? '';
  }

  // ─── WebSocket Logs ───────────────────────────────────────────────────────

  /// Подписывается на поток логов через WebSocket (ws://host:port/ws/logs)
  Stream<String> subscribeToLogs() {
    return Stream.fromFuture(_shouldUseDemo()).asyncExpand((demo) {
      if (demo) return _demoLogStream();
      final wsUrl = baseUrl
          .replaceFirst('https://', 'wss://')
          .replaceFirst('http://', 'ws://');
      final channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/ws/logs'),
      );
      return channel.stream
          .map((event) => event.toString())
          .handleError((_) {});
    });
  }

  // ─── Demo helpers ─────────────────────────────────────────────────────────

  List<AgentInfo> _demoAgents() => const [
        AgentInfo(
          id: 'neo',
          name: 'AGENT NEO',
          description: 'Self-tool-generating autonomous agent',
          status: 'online',
          workspace: '/app/neo_workspace',
          tasksCompleted: 24,
          tasksFailed: 1,
        ),
        AgentInfo(
          id: 'matrix',
          name: 'AGENT MATRIX',
          description: 'Universal self-evolving agent with roles',
          status: 'online',
          workspace: '/app/matrix_workspace',
          tasksCompleted: 31,
          tasksFailed: 3,
        ),
        AgentInfo(
          id: 'coder3',
          name: 'CODER 3',
          description: 'Code generation & auto-fix agent',
          status: 'online',
          workspace: '/app/agent_projects',
          tasksCompleted: 18,
          tasksFailed: 2,
        ),
        AgentInfo(
          id: 'chat',
          name: 'CHAT AGENT',
          description: 'Conversational AI with tool calling',
          status: 'online',
          workspace: '/app/artifacts',
          tasksCompleted: 44,
          tasksFailed: 0,
        ),
      ];

  SystemStats _demoStats(List<AgentInfo> agents) => SystemStats(
        totalTasks: 120,
        pendingTasks: 6,
        runningTasks: 3,
        doneTasks: 101,
        failedTasks: 10,
        totalUsers: 5,
        agents: agents,
        tasksByType: const {
          'chat': 34,
          'code': 28,
          'image': 12,
          'tts': 8,
          'shell': 20,
        },
        timestamp: DateTime.now(),
      );

  List<Task> _seedDemoTasks() {
    final now = DateTime.now();
    return [
      Task(
        id: 'demo-1',
        userId: 'mobile_user',
        type: 'code',
        title: 'Refactor auth module',
        status: 'running',
        result: 'Generating patch for auth module...',
        createdAt: now.subtract(const Duration(minutes: 12)),
        startedAt: now.subtract(const Duration(minutes: 10)),
      ),
      Task(
        id: 'demo-2',
        userId: 'mobile_user',
        type: 'chat',
        title: 'Summarize incident report',
        status: 'done',
        result: 'Incident resolved. Summary ready.',
        createdAt: now.subtract(const Duration(hours: 1)),
        startedAt: now.subtract(const Duration(hours: 1, minutes: 5)),
        finishedAt: now.subtract(const Duration(minutes: 50)),
      ),
      Task(
        id: 'demo-3',
        userId: 'mobile_user',
        type: 'shell',
        title: 'List docker containers',
        status: 'failed',
        error: 'Permission denied',
        createdAt: now.subtract(const Duration(hours: 2)),
        startedAt: now.subtract(const Duration(hours: 2)),
        finishedAt: now.subtract(const Duration(hours: 2, minutes: 0, seconds: 30)),
      ),
      Task(
        id: 'demo-4',
        userId: 'mobile_user',
        type: 'image',
        title: 'Generate cover art',
        status: 'pending',
        createdAt: now.subtract(const Duration(minutes: 5)),
      ),
    ];
  }

  Future<List<Task>> _loadDemoTasks() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_demoTasksKey);
    if (raw == null || raw.isEmpty) {
      final seeded = _seedDemoTasks();
      await _saveDemoTasks(seeded);
      return seeded;
    }
    try {
      final data = jsonDecode(raw);
      if (data is List) {
        return data.map((e) => Task.fromJson(e)).toList();
      }
      return _seedDemoTasks();
    } catch (_) {
      final seeded = _seedDemoTasks();
      await _saveDemoTasks(seeded);
      return seeded;
    }
  }

  Future<void> _saveDemoTasks(List<Task> tasks) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _demoTasksKey,
      jsonEncode(tasks.map((t) => t.toJson()).toList()),
    );
  }

  DockerContainerStatus _demoDockerStatus() => const DockerContainerStatus(
        id: 'demo-container',
        name: 'blackbugs-ai',
        status: 'running',
        image: 'blackbugsai:latest',
        uptime: '3h 24m',
        cpuPercent: 12.4,
        memoryMb: 512,
      );

  List<LlmProvider> _demoProviders() => const [
        LlmProvider(
          id: 'openai',
          name: 'OpenAI',
          enabled: true,
          isDefault: true,
          models: ['gpt-4.1', 'gpt-4.1-mini'],
          currentModel: 'gpt-4.1',
        ),
        LlmProvider(
          id: 'groq',
          name: 'Groq',
          enabled: true,
          isDefault: false,
          models: ['llama3-70b', 'mixtral-8x7b'],
          currentModel: 'llama3-70b',
        ),
        LlmProvider(
          id: 'anthropic',
          name: 'Anthropic',
          enabled: true,
          isDefault: false,
          models: ['claude-3.5-sonnet'],
          currentModel: 'claude-3.5-sonnet',
        ),
      ];

  List<String> _demoLogs() => [
        '[demo] agent.neo >> boot complete',
        '[demo] matrix >> new task: code refactor',
        '[demo] coder3 >> patch generated',
        '[demo] docker >> container healthy',
        '[demo] chat >> session started',
      ];

  Stream<String> _demoLogStream() => Stream<String>.periodic(
        const Duration(seconds: 1),
        (i) => '[demo] log line ${i + 1}',
      );
}
