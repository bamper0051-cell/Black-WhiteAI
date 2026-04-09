// api_service.dart — REST API client for BlackBugsAI admin panel

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
    try {
      // Try /ping first (simpler endpoint, no auth required)
      final data = await http
          .get(Uri.parse('$baseUrl/ping'))
          .timeout(const Duration(seconds: 10));
      if (data.statusCode == 200) {
        final json = jsonDecode(data.body);
        return json['ok'] == true || json['pong'] == true;
      }
      return false;
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
    String path = '/api/tasks?limit=$limit';
    if (status != null) path += '&status=$status';
    final data = await _get(path) as List;
    return data.map((j) => Task.fromJson(j)).toList();
  }

  Future<Task> getTask(String taskId) async {
    final data = await _get('/api/tasks/$taskId');
    return Task.fromJson(data);
  }

  Future<String> createTask({
    required String userId,
    required String type,
    required String title,
    Map<String, dynamic>? payload,
  }) async {
    final data = await _post('/api/tasks', {
      'user_id': userId,
      'type': type,
      'title': title,
      'payload': payload ?? {},
    });
    return data['task_id'] ?? '';
  }

  Future<bool> cancelTask(String taskId) async {
    try {
      await _post('/api/tasks/$taskId/cancel', {});
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> retryTask(String taskId) async {
    try {
      await _post('/api/tasks/$taskId/retry', {});
      return true;
    } catch (_) {
      return false;
    }
  }

  // ─── Agents ───────────────────────────────────────────────────────────────

  Future<List<AgentInfo>> getAgents() async {
    try {
      final data = await _get('/api/agents') as List;
      return data.map((j) => AgentInfo.fromJson(j)).toList();
    } catch (_) {
      // Return mock agents if endpoint not available
      return [
        const AgentInfo(
          id: 'neo',
          name: 'AGENT NEO',
          description: 'Self-tool-generating autonomous agent',
          status: 'online',
          workspace: '/app/neo_workspace',
        ),
        const AgentInfo(
          id: 'matrix',
          name: 'AGENT MATRIX',
          description: 'Universal self-evolving agent with roles',
          status: 'online',
          workspace: '/app/matrix_workspace',
        ),
        const AgentInfo(
          id: 'coder3',
          name: 'CODER 3',
          description: 'Code generation & auto-fix agent',
          status: 'online',
          workspace: '/app/agent_projects',
        ),
        const AgentInfo(
          id: 'chat',
          name: 'CHAT AGENT',
          description: 'Conversational AI with tool calling',
          status: 'online',
          workspace: '/app/artifacts',
        ),
      ];
    }
  }

  // ─── LLM Providers ────────────────────────────────────────────────────────

  Future<List<LlmProvider>> getProviders() async {
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
      return [];
    }
  }

  // ─── Shell / Admin ────────────────────────────────────────────────────────

  Future<String> runShell(String command) async {
    final data = await _post('/api/shell', {'cmd': command});
    return data['output'] ?? '';
  }

  Future<Map<String, dynamic>> getSystemInfo() async {
    return await _get('/api/sysinfo') as Map<String, dynamic>;
  }

  // ─── Logs ─────────────────────────────────────────────────────────────────

  Future<List<String>> getLogs({int lines = 50}) async {
    try {
      final data = await _get('/api/logs?lines=$lines');
      return List<String>.from(data['lines'] ?? []);
    } catch (_) {
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

  /// Alias kept for backward compatibility with docker_screen
  Future<String> runDockerCommand(String cmd) => runShellCommand(cmd);

  // ─── WebSocket Logs ───────────────────────────────────────────────────────

  /// Подписывается на поток логов через WebSocket (ws://host:port/ws/logs)
  Stream<String> subscribeToLogs() {
    final wsUrl = baseUrl
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
    final channel = WebSocketChannel.connect(
      Uri.parse('$wsUrl/ws/logs'),
    );
    return channel.stream
        .map((event) => event.toString())
        .handleError((_) {});
  }
}
