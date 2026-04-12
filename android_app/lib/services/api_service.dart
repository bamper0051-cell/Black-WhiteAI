// api_service.dart — REST API client for BlackBugsAI admin panel
<<<<<<< HEAD
// FIXED: removed duplicate runDockerCommand, unified docker endpoints
=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

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

<<<<<<< HEAD
  static const String _demoModeKey  = 'demo_mode';
=======
  static const String _demoModeKey = 'demo_mode';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  static const String _demoTasksKey = 'demo_tasks';

  static Future<bool> isDemoMode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_demoModeKey) ?? false;
  }

  static Future<void> setDemoMode(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_demoModeKey, value);
  }

<<<<<<< HEAD
  static Future<ApiService> fromSavedConfig() async {
    final prefs = await SharedPreferences.getInstance();
    return ApiService(
      baseUrl:    prefs.getString('base_url')    ?? '',
      adminToken: prefs.getString('admin_token') ?? '',
    );
  }

  Map<String, String> get _headers => {
        'Content-Type':  'application/json',
        'X-Admin-Token': adminToken,
        'Authorization': 'Bearer $adminToken',
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      };

  Future<bool> _shouldUseDemo() async {
    final demo = await ApiService.isDemoMode();
    return demo || baseUrl.isEmpty;
  }

  Future<dynamic> _get(String path) async {
    final uri = Uri.parse('$baseUrl$path');
<<<<<<< HEAD
    final response = await http
        .get(uri, headers: _headers)
        .timeout(const Duration(seconds: 15));
=======
    final response =
        await http.get(uri, headers: _headers).timeout(const Duration(seconds: 10));
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    return _handle(response);
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await http
        .post(uri, headers: _headers, body: jsonEncode(body))
<<<<<<< HEAD
        .timeout(const Duration(seconds: 120)); // longer for AI tasks
=======
        .timeout(const Duration(seconds: 10));
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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

<<<<<<< HEAD
  // ─── System ──────────────────────────────────────────────────────────────
=======
  // ─── System ───────────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  Future<bool> ping() async {
    if (await _shouldUseDemo()) return true;
    try {
<<<<<<< HEAD
      final data = await http
          .get(Uri.parse('$baseUrl/ping'))
          .timeout(const Duration(seconds: 8));
      if (data.statusCode == 200) {
        final json = jsonDecode(data.body);
        return json['ok'] == true || json['pong'] == true;
      }
      return false;
=======
      final data = await _get('/health');
      return data['status'] == 'ok';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    } catch (_) {
      return false;
    }
  }

  Future<SystemStats> getStats() async {
<<<<<<< HEAD
    if (await _shouldUseDemo()) {
      return _demoStats(_demoAgents());
    }
    try {
      final data = await _get('/api/status');
      return SystemStats.fromJson(data);
    } catch (_) {
      return _demoStats(_demoAgents());
    }
  }

  // ─── Agents ──────────────────────────────────────────────────────────────

  Future<List<AgentInfo>> getAgents() async {
    if (await _shouldUseDemo()) return _demoAgents();
    try {
      final data = await _get('/api/agents');
      if (data is Map && data['ok'] == true) {
        final list = data['agents'] as List? ?? [];
        return list.map((j) => AgentInfo.fromJson(j)).toList();
      }
    } catch (_) {}
    return _demoAgents();
  }

  // ─── Tasks ───────────────────────────────────────────────────────────────
=======
    final data = await _get('/api/status');
    return SystemStats.fromJson(data);
  }

  // ─── Tasks ────────────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  Future<List<Task>> getTasks({String? status, int limit = 20}) async {
    final useDemo = await _shouldUseDemo();
    if (!useDemo) {
      try {
        String path = '/api/tasks?limit=$limit';
        if (status != null) path += '&status=$status';
<<<<<<< HEAD
        final raw = await _get(path);
        final list = raw is List ? raw : (raw['tasks'] as List? ?? []);
        return list.map((j) => Task.fromJson(j)).toList();
=======
        final data = await _get(path) as List;
        return data.map((j) => Task.fromJson(j)).toList();
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      } catch (_) {
        if (!await ApiService.isDemoMode()) rethrow;
      }
    }
<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    final tasks = await _loadDemoTasks();
    final filtered = status == null
        ? tasks
        : tasks.where((t) => t.status == status).toList();
    return filtered.take(limit).toList();
  }

  Future<Task> getTask(String taskId) async {
<<<<<<< HEAD
    if (await _shouldUseDemo()) {
      final tasks = await _loadDemoTasks();
      return tasks.firstWhere(
        (t) => t.id == taskId,
        orElse: () => _seedDemoTasks().first,
      );
    }
    final data = await _get('/api/tasks/$taskId');
    return Task.fromJson(data);
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
        'user_id': userId, 'type': type, 'title': title,
=======
        'user_id': userId,
        'type': type,
        'title': title,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        'payload': payload ?? {},
      });
      return data['task_id'] ?? '';
    }
<<<<<<< HEAD
    final demoTasks = await _loadDemoTasks();
    final id  = 'demo-${DateTime.now().millisecondsSinceEpoch}';
    final now = DateTime.now();
    demoTasks.insert(0, Task(
      id: id, userId: userId, type: type, title: title,
      status: 'pending', createdAt: now,
      result: payload?['text'] ?? payload?['prompt'] ?? '',
    ));
=======

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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    await _saveDemoTasks(demoTasks);
    return id;
  }

  Future<bool> cancelTask(String taskId) async {
    if (await _shouldUseDemo()) {
<<<<<<< HEAD
      return _mutateDemoTask(taskId, 'cancelled');
    }
    try {
      await _post('/api/tasks/$taskId/cancel', {});
      return true;
    } catch (_) { return false; }
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }

  Future<bool> retryTask(String taskId) async {
    if (await _shouldUseDemo()) {
<<<<<<< HEAD
      return _mutateDemoTask(taskId, 'running', clearError: true);
    }
    try {
      await _post('/api/tasks/$taskId/retry', {});
      return true;
    } catch (_) { return false; }
  }

  // ─── Agent run ────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> runAgent({
    required String agent,
    required String task,
    String mode  = 'auto',
    String? filePath,
  }) async {
    if (await _shouldUseDemo()) {
      return {
        'ok': true,
        'final': 'DEMO: $agent выполнил задачу «${task.substring(0, task.length.clamp(0, 40))}...»',
        'steps': [],
      };
    }
    try {
      final body = <String, dynamic>{
        'task': task, 'agent': agent, 'mode': mode,
        if (filePath != null) 'file_path': filePath,
      };
      final data = await _post('/api/agent/run', body);
      return Map<String, dynamic>.from(data);
    } catch (e) {
      return {'ok': false, 'error': e.toString()};
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    }
  }

  // ─── LLM Providers ────────────────────────────────────────────────────────

  Future<List<LlmProvider>> getProviders() async {
<<<<<<< HEAD
    if (await _shouldUseDemo()) return _demoProviders();
    try {
      final data = await _get('/api/providers/status') as Map<String, dynamic>;
      final activeLlm = data['active_llm'] as String?;
      final bestLlm   = data['best_llm']   as String?;
      if (activeLlm != null) {
        return [LlmProvider(
          id: activeLlm, name: activeLlm, enabled: true, isDefault: true,
          models: [activeLlm, if (bestLlm != null && bestLlm != activeLlm) bestLlm],
          currentModel: bestLlm ?? activeLlm,
        )];
      }
    } catch (_) {}
    return _demoProviders();
  }

  // ─── Shell ────────────────────────────────────────────────────────────────

  Future<String> runShell(String command) async {
    if (await _shouldUseDemo()) {
      return 'DEMO SHELL> $command\n(нет подключения к серверу)';
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    }
    final data = await _post('/api/shell', {'cmd': command});
    return data['output'] ?? '';
  }

  Future<Map<String, dynamic>> getSystemInfo() async {
<<<<<<< HEAD
    if (await _shouldUseDemo()) return {'ok': true, 'os': 'Demo'};
=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    return await _get('/api/sysinfo') as Map<String, dynamic>;
  }

  // ─── Logs ─────────────────────────────────────────────────────────────────

  Future<List<String>> getLogs({int lines = 50}) async {
<<<<<<< HEAD
    if (await _shouldUseDemo()) return _demoLogs().take(lines).toList();
    try {
      final data = await _get('/api/logs?n=$lines');
      final raw  = data['logs'] ?? data['lines'] ?? [];
      if (raw is List) {
        return raw.map((e) {
          if (e is String) return e;
          if (e is Map)   return '[${e['ts'] ?? ''}] ${e['text'] ?? ''}';
          return e.toString();
        }).toList();
      }
    } catch (_) {}
    return [];
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }

  // ─── Docker Control ───────────────────────────────────────────────────────

<<<<<<< HEAD
  Future<DockerContainerStatus> getDockerStatus() async {
    if (await _shouldUseDemo()) return _demoDockerStatus();
    try {
      // Try rc/docker first (newer endpoint), then legacy
      dynamic data;
      try {
        final raw = await _get('/api/rc/docker');
        final containers = raw['containers'] as List? ?? [];
        if (containers.isNotEmpty) {
          data = containers.first;
        }
      } catch (_) {
        data = await _get('/api/docker/status');
      }
      if (data != null) return DockerContainerStatus.fromJson(data);
    } catch (_) {}
    return _demoDockerStatus();
  }

  Future<String> runDockerCommand(String cmd) async {
    if (await _shouldUseDemo()) {
      return 'Demo: executed "$cmd"';
    }
    try {
      // Try rc/docker/action first
      final data = await _post('/api/rc/docker/action', {
        'container': 'blackbugs-main', 'action': cmd,
      });
      return data['output'] ?? data['result'] ?? 'OK';
    } catch (_) {}
    // Fallback to shell
    try {
      final data = await _post('/api/shell', {'cmd': 'docker $cmd'});
      return data['output'] ?? '';
    } catch (e) {
      return 'Error: $e';
    }
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }

  // ─── WebSocket Logs ───────────────────────────────────────────────────────

<<<<<<< HEAD
=======
  /// Подписывается на поток логов через WebSocket (ws://host:port/ws/logs)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  Stream<String> subscribeToLogs() {
    return Stream.fromFuture(_shouldUseDemo()).asyncExpand((demo) {
      if (demo) return _demoLogStream();
      final wsUrl = baseUrl
          .replaceFirst('https://', 'wss://')
          .replaceFirst('http://', 'ws://');
<<<<<<< HEAD
      try {
        final channel = WebSocketChannel.connect(Uri.parse('$wsUrl/ws/logs'));
        return channel.stream
            .map((e) => e.toString())
            .handleError((_) {});
      } catch (_) {
        return _demoLogStream();
      }
=======
      final channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/ws/logs'),
      );
      return channel.stream
          .map((event) => event.toString())
          .handleError((_) {});
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    });
  }

  // ─── Demo helpers ─────────────────────────────────────────────────────────

  List<AgentInfo> _demoAgents() => const [
<<<<<<< HEAD
        AgentInfo(id: 'neo',      name: 'AGENT NEO',    description: 'Self-tool gen · OSINT · ZIP artifacts', status: 'online', workspace: '/neo_workspace',    tasksCompleted: 24, tasksFailed: 1),
        AgentInfo(id: 'matrix',   name: 'AGENT MATRIX', description: 'Coder · OSINT · Security Analyst',      status: 'online', workspace: '/matrix_workspace', tasksCompleted: 31, tasksFailed: 3),
        AgentInfo(id: 'smith',    name: 'АГЕНТ СМИТ',   description: 'Autofix pipeline · security audit',     status: 'online', workspace: '/app',             tasksCompleted: 18, tasksFailed: 2),
        AgentInfo(id: 'anderson', name: 'MR. ANDERSON', description: 'Vuln analysis · code fix · review',     status: 'online', workspace: '/app',             tasksCompleted: 12, tasksFailed: 1),
        AgentInfo(id: 'pythia',   name: 'AGENT PYTHIA', description: 'Quick coder · project · sandbox',       status: 'online', workspace: '/app',             tasksCompleted: 44, tasksFailed: 0),
        AgentInfo(id: 'tanker',   name: 'AGENT TANKER', description: 'Red team · multitool · chains',         status: 'online', workspace: '/app',             tasksCompleted: 8,  tasksFailed: 2),
        AgentInfo(id: 'operator', name: 'OPERATOR',     description: 'Meta-agent · orchestration',            status: 'online', workspace: '/app',             tasksCompleted: 5,  tasksFailed: 0),
      ];

  SystemStats _demoStats(List<AgentInfo> agents) => SystemStats(
        totalTasks: 120, pendingTasks: 6, runningTasks: 3,
        doneTasks: 101,  failedTasks: 10, totalUsers: 5,
        agents: agents, tasksByType: const {'chat': 34, 'code': 28, 'image': 12, 'shell': 20},
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        timestamp: DateTime.now(),
      );

  List<Task> _seedDemoTasks() {
    final now = DateTime.now();
    return [
<<<<<<< HEAD
      Task(id: 'demo-1', userId: 'mobile_user', type: 'code',  title: 'Refactor auth module', status: 'running',  createdAt: now.subtract(const Duration(minutes: 12)), startedAt: now.subtract(const Duration(minutes: 10))),
      Task(id: 'demo-2', userId: 'mobile_user', type: 'chat',  title: 'Summarize incident',   status: 'done',     result: 'Готово', createdAt: now.subtract(const Duration(hours: 1)),   startedAt: now.subtract(const Duration(hours: 1)),    finishedAt: now.subtract(const Duration(minutes: 50))),
      Task(id: 'demo-3', userId: 'mobile_user', type: 'shell', title: 'Docker containers',    status: 'failed',   error: 'Permission denied', createdAt: now.subtract(const Duration(hours: 2)), startedAt: now.subtract(const Duration(hours: 2)), finishedAt: now.subtract(const Duration(hours: 2))),
      Task(id: 'demo-4', userId: 'mobile_user', type: 'image', title: 'Generate cover art',   status: 'pending',  createdAt: now.subtract(const Duration(minutes: 5))),
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
      if (data is List) return data.map((e) => Task.fromJson(e)).toList();
    } catch (_) {}
    final seeded = _seedDemoTasks();
    await _saveDemoTasks(seeded);
    return seeded;
=======
      if (data is List) {
        return data.map((e) => Task.fromJson(e)).toList();
      }
      return _seedDemoTasks();
    } catch (_) {
      final seeded = _seedDemoTasks();
      await _saveDemoTasks(seeded);
      return seeded;
    }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }

  Future<void> _saveDemoTasks(List<Task> tasks) async {
    final prefs = await SharedPreferences.getInstance();
<<<<<<< HEAD
    await prefs.setString(_demoTasksKey,
        jsonEncode(tasks.map((t) => t.toJson()).toList()));
  }

  Future<bool> _mutateDemoTask(String taskId, String newStatus,
      {bool clearError = false}) async {
    final tasks = await _loadDemoTasks();
    for (int i = 0; i < tasks.length; i++) {
      if (tasks[i].id == taskId) {
        final t = tasks[i];
        tasks[i] = Task(
          id: t.id, userId: t.userId, type: t.type, title: t.title,
          status: newStatus, result: t.result,
          error: clearError ? null : t.error,
          artifacts: t.artifacts,
          retryCount: clearError ? t.retryCount + 1 : t.retryCount,
          maxRetries: t.maxRetries, createdAt: t.createdAt,
          startedAt: clearError ? DateTime.now() : t.startedAt,
          finishedAt: clearError ? null : DateTime.now(),
        );
        await _saveDemoTasks(tasks);
        return true;
      }
    }
    return false;
  }

  DockerContainerStatus _demoDockerStatus() => const DockerContainerStatus(
        id: 'demo-container', name: 'blackbugs-main',
        status: 'running', image: 'blackbugsai:v3',
        uptime: '3h 24m', cpuPercent: 12.4, memoryMb: 512,
      );

  List<LlmProvider> _demoProviders() => const [
        LlmProvider(id: 'openai', name: 'OpenAI', enabled: true, isDefault: true,
            models: ['gpt-4.1', 'gpt-4.1-mini'], currentModel: 'gpt-4.1'),
        LlmProvider(id: 'groq', name: 'Groq', enabled: true, isDefault: false,
            models: ['llama3-70b', 'mixtral-8x7b'], currentModel: 'llama3-70b'),
        LlmProvider(id: 'deepseek', name: 'DeepSeek', enabled: true, isDefault: false,
            models: ['deepseek-coder', 'deepseek-chat'], currentModel: 'deepseek-coder'),
      ];

  List<String> _demoLogs() => [
        '[demo] blackbugsai:v3 started',
        '[demo] agent.neo >> boot complete',
        '[demo] matrix >> loaded 15 tools',
        '[demo] admin_web >> listening on :8080',
        '[demo] fish >> listening on :5100',
        '[demo] cloudflared >> tunnel active',
      ];

  Stream<String> _demoLogStream() => Stream<String>.periodic(
        const Duration(seconds: 2),
        (i) => '[demo] heartbeat ${i + 1} — all systems operational',
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      );
}
