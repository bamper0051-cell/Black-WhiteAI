/// Workflow models for workflow execution
library;

/// Workflow execute request
class WorkflowExecuteRequest {
  final String workflow;
  final Map<String, dynamic>? params;
  final String? userId;

  WorkflowExecuteRequest({
    required this.workflow,
    this.params,
    this.userId,
  });

  Map<String, dynamic> toJson() {
    final data = {'workflow': workflow};
    if (params != null) data['params'] = params;
    if (userId != null) data['user_id'] = userId;
    return data;
  }
}

/// Workflow execute response
class WorkflowExecuteResponse {
  final bool ok;
  final String? result;
  final Map<String, dynamic>? output;
  final List<dynamic>? steps;
  final String? error;

  WorkflowExecuteResponse({
    required this.ok,
    this.result,
    this.output,
    this.steps,
    this.error,
  });

  factory WorkflowExecuteResponse.fromJson(Map<String, dynamic> json) {
    return WorkflowExecuteResponse(
      ok: json['ok'] ?? false,
      result: json['result'],
      output: json['output'] as Map<String, dynamic>?,
      steps: json['steps'] as List<dynamic>?,
      error: json['error'],
    );
  }
}
