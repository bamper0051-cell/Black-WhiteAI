// api_service.dart — REST API client for BlackBugsAI admin panel

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

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

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $adminToken',
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

  Future<dynamic> _postNoAuth(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
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
      final data = await _get('/api/health');
      return data['status'] == 'ok';
    } catch (_) {
      // Fallback to /health
      try {
        final uri = Uri.parse('$baseUrl/health');
        final response =
            await http.get(uri).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          return data['status'] == 'ok';
        }
      } catch (_) {}
      return false;
    }
  }

  Future<SystemStats> getStats() async {
    final data = await _get('/api/stats');
    return SystemStats.fromJson(data);
  }

  // ─── App Auth (login / register) ──────────────────────────────────────────

  /// Register a new user. Returns [AppAuthResult] with token and username.
  Future<AppAuthResult> register(String username, String password) async {
    final data = await _postNoAuth('/api/app/register', {
      'username': username,
      'password': password,
    });
    if (data['ok'] != true) {
      throw ApiException(400, data['error'] ?? 'Registration failed');
    }
    return AppAuthResult(
      token: data['token'] as String,
      username: data['username'] as String,
    );
  }

  /// Login an existing user. Returns [AppAuthResult] with token and username.
  Future<AppAuthResult> login(String username, String password) async {
    final data = await _postNoAuth('/api/app/login', {
      'username': username,
      'password': password,
    });
    if (data['ok'] != true) {
      throw ApiException(401, data['error'] ?? 'Login failed');
    }
    return AppAuthResult(
      token: data['token'] as String,
      username: data['username'] as String,
    );
  }

  /// Logout — invalidate the current session token by sending it in the body.
  Future<void> logout(String appToken) async {
    try {
      await _postNoAuth('/api/app/logout', {'token': appToken});
    } catch (_) {}
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
      final data = await _get('/api/providers') as List;
      return data.map((j) => LlmProvider.fromJson(j)).toList();
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
    return await _get('/api/system') as Map<String, dynamic>;
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
}

/// Result returned by [ApiService.login] and [ApiService.register].
class AppAuthResult {
  final String token;
  final String username;
  const AppAuthResult({required this.token, required this.username});
}
