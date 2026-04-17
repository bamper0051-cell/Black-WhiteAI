/// Workflow endpoints
library;

import '../client/api_client.dart';
import '../models/workflow_models.dart';

class WorkflowEndpoints {
  final ApiClient _client;

  WorkflowEndpoints(this._client);

  /// Execute a workflow
  Future<WorkflowExecuteResponse> executeWorkflow(
    WorkflowExecuteRequest request,
  ) async {
    try {
      final response = await _client.post(
        '/api/workflow/execute',
        data: request.toJson(),
      );
      return WorkflowExecuteResponse.fromJson(response.data);
    } catch (e) {
      return WorkflowExecuteResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }
}
