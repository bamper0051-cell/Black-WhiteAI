/// Example usage of the BlackWhiteAI API client
/// This file demonstrates how to use the new API client in your Flutter app
library;

import 'package:blackbugsai/api/api.dart';

/// Example: Initialize and use the API client
Future<void> exampleUsage() async {
  // 1. Create API service from saved credentials (recommended for app startup)
  final api = await BlackWhiteApiService.fromSavedCredentials();

  // Or create with explicit credentials
  // final api = BlackWhiteApiService(
  //   baseUrl: 'https://your-server.com',
  //   accessToken: 'your_token',
  // );

  // 2. Check authentication status
  if (!api.isAuthenticated) {
    print('Not authenticated, need to login');

    // Perform login
    final loginResponse = await api.auth.login(
      LoginRequest(
        username: 'admin',
        password: 'changeme_secret_token',
      ),
    );

    if (loginResponse.ok) {
      print('✅ Logged in as: ${loginResponse.username}');
      print('Token: ${loginResponse.token}');
    } else {
      print('❌ Login failed: ${loginResponse.error}');
      return;
    }
  }

  // 3. Get list of agents
  print('\n📋 Fetching agents...');
  final agentsResponse = await api.agents.getAgents();

  if (agentsResponse.ok) {
    print('✅ Found ${agentsResponse.agents.length} agents:');
    for (final agent in agentsResponse.agents) {
      print('  ${agent.emoji} ${agent.name} - ${agent.description}');
      print('    Modes: ${agent.modes.join(", ")}');
      print('    Status: ${agent.status}');
    }
  } else {
    print('❌ Failed to fetch agents: ${agentsResponse.error}');
  }

  // 4. Run an agent task
  print('\n🤖 Running agent task...');
  final runResponse = await api.agents.runAgent(
    AgentRunRequest(
      agent: 'smith',
      task: 'Check system status',
      mode: 'auto',
    ),
  );

  if (runResponse.ok) {
    print('✅ Agent task completed');
    print('Result: ${runResponse.result}');
    if (runResponse.steps != null) {
      print('Steps: ${runResponse.steps}');
    }
  } else {
    print('❌ Agent task failed: ${runResponse.error}');
  }

  // 5. Get tools
  print('\n🔧 Fetching tools...');
  final toolsResponse = await api.tools.getAllTools();

  if (toolsResponse.ok) {
    print('✅ Found ${toolsResponse.tools.length} tools:');
    for (final tool in toolsResponse.tools.take(5)) {
      print('  • ${tool.name}: ${tool.description}');
    }
  } else {
    print('❌ Failed to fetch tools: ${toolsResponse.error}');
  }

  // 6. Get logs
  print('\n📜 Fetching recent logs...');
  final logsResponse = await api.logs.getLogs(
    n: 10,
    level: 'INFO',
  );

  if (logsResponse.ok) {
    print('✅ Found ${logsResponse.logs.length} log entries:');
    for (final log in logsResponse.logs) {
      print('  [${log.timestamp}] ${log.level}: ${log.text}');
    }
  } else {
    print('❌ Failed to fetch logs: ${logsResponse.error}');
  }

  // 7. Execute a workflow
  print('\n⚙️ Executing workflow...');
  final workflowResponse = await api.workflows.executeWorkflow(
    WorkflowExecuteRequest(
      workflow: 'health_check',
      params: {'verbose': true},
    ),
  );

  if (workflowResponse.ok) {
    print('✅ Workflow executed successfully');
    print('Result: ${workflowResponse.result}');
  } else {
    print('❌ Workflow failed: ${workflowResponse.error}');
  }
}

/// Example: Integration with existing Flutter widget
class ApiExampleWidget {
  final BlackWhiteApiService api;

  ApiExampleWidget(this.api);

  /// Fetch and display agents
  Future<List<Agent>> fetchAgents() async {
    final response = await api.agents.getAgents();
    if (response.ok) {
      return response.agents;
    }
    throw Exception(response.error ?? 'Failed to fetch agents');
  }

  /// Run agent task with error handling
  Future<String?> runAgentTask({
    required String agentId,
    required String task,
  }) async {
    try {
      final response = await api.agents.runAgent(
        AgentRunRequest(
          agent: agentId,
          task: task,
          mode: 'auto',
        ),
      );

      if (response.ok) {
        return response.result ?? response.final_;
      } else {
        throw Exception(response.error);
      }
    } catch (e) {
      print('Error running agent task: $e');
      rethrow;
    }
  }

  /// Stream logs (polling approach)
  Stream<List<LogEntry>> streamLogs({
    Duration interval = const Duration(seconds: 5),
    int count = 20,
  }) async* {
    while (true) {
      final response = await api.logs.getLogs(n: count);
      if (response.ok) {
        yield response.logs;
      }
      await Future.delayed(interval);
    }
  }
}

/// Example: Replace old ApiService usage
///
/// OLD CODE:
/// ```dart
/// final oldApi = ApiService(
///   baseUrl: baseUrl,
///   adminToken: token,
/// );
/// final response = await oldApi._get('/api/agents');
/// ```
///
/// NEW CODE:
/// ```dart
/// final newApi = BlackWhiteApiService(
///   baseUrl: baseUrl,
///   accessToken: token,
/// );
/// final response = await newApi.agents.getAgents();
/// ```
///
/// Benefits:
/// - Type-safe responses
/// - Automatic token refresh
/// - Better error handling
/// - Cleaner API
/// - Retry logic built-in
