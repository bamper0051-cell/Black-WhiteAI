/// Tool endpoints
library;

import '../client/api_client.dart';
import '../models/tool_models.dart';

class ToolEndpoints {
  final ApiClient _client;

  ToolEndpoints(this._client);

  /// Get all tools (combined from all agents)
  Future<ToolsResponse> getAllTools() async {
    try {
      final response = await _client.get('/api/agent/tools_all');
      return ToolsResponse.fromJson(response.data);
    } catch (e) {
      return ToolsResponse(
        ok: false,
        tools: [],
        error: e.toString(),
      );
    }
  }

  /// Get tools for a specific agent (neo)
  Future<ToolsResponse> getNeoTools() async {
    try {
      final response = await _client.get('/api/neo/tools');
      return ToolsResponse.fromJson(response.data);
    } catch (e) {
      return ToolsResponse(
        ok: false,
        tools: [],
        error: e.toString(),
      );
    }
  }

  /// Get tools for a specific agent (matrix)
  Future<ToolsResponse> getMatrixTools() async {
    try {
      final response = await _client.get('/api/matrix/tools');
      return ToolsResponse.fromJson(response.data);
    } catch (e) {
      return ToolsResponse(
        ok: false,
        tools: [],
        error: e.toString(),
      );
    }
  }

  /// Delete a tool
  Future<ToolDeleteResponse> deleteTool(ToolDeleteRequest request) async {
    try {
      final response = await _client.post(
        '/api/neo/tool/delete',
        data: request.toJson(),
      );
      return ToolDeleteResponse.fromJson(response.data);
    } catch (e) {
      return ToolDeleteResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }
}
