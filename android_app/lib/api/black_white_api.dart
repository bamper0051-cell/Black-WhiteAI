/// Main API Service combining all endpoints
library;

import 'client/api_client.dart';
import 'endpoints/auth_endpoints.dart';
import 'endpoints/agent_endpoints.dart';
import 'endpoints/tool_endpoints.dart';
import 'endpoints/workflow_endpoints.dart';
import 'endpoints/log_endpoints.dart';

class BlackWhiteApiService {
  final ApiClient _client;

  late final AuthEndpoints auth;
  late final AgentEndpoints agents;
  late final ToolEndpoints tools;
  late final WorkflowEndpoints workflows;
  late final LogEndpoints logs;

  BlackWhiteApiService({
    required String baseUrl,
    String? accessToken,
    String? refreshToken,
  }) : _client = ApiClient(
          baseUrl: baseUrl,
          accessToken: accessToken,
          refreshToken: refreshToken,
        ) {
    _initializeEndpoints();
  }

  /// Create API service from saved credentials
  static Future<BlackWhiteApiService> fromSavedCredentials() async {
    final client = await ApiClient.fromSavedCredentials();
    return BlackWhiteApiService(
      baseUrl: client.baseUrl,
      accessToken: client.accessToken,
      refreshToken: client.refreshToken,
    );
  }

  void _initializeEndpoints() {
    auth = AuthEndpoints(_client);
    agents = AgentEndpoints(_client);
    tools = ToolEndpoints(_client);
    workflows = WorkflowEndpoints(_client);
    logs = LogEndpoints(_client);
  }

  /// Get underlying API client for advanced usage
  ApiClient get client => _client;

  /// Check if user is authenticated
  bool get isAuthenticated => _client.accessToken != null;

  /// Get current access token
  String? get accessToken => _client.accessToken;
}
