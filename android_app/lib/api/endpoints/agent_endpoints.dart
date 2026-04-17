/// Agent endpoints
library;

import '../client/api_client.dart';
import '../models/agent_models.dart';

class AgentEndpoints {
  final ApiClient _client;

  AgentEndpoints(this._client);

  /// Get list of all agents
  Future<AgentsResponse> getAgents() async {
    try {
      final response = await _client.get('/api/agents');
      return AgentsResponse.fromJson(response.data);
    } catch (e) {
      return AgentsResponse(
        ok: false,
        agents: [],
        error: e.toString(),
      );
    }
  }

  /// Run a task with a specific agent
  Future<AgentRunResponse> runAgent(AgentRunRequest request) async {
    try {
      final response = await _client.post(
        '/api/agent/run',
        data: request.toJson(),
      );
      return AgentRunResponse.fromJson(response.data);
    } catch (e) {
      return AgentRunResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }
}
