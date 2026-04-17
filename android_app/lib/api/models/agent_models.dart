/// Agent models for agent listing and execution
library;

/// Agent model
class Agent {
  final String id;
  final String name;
  final String emoji;
  final String description;
  final List<String> modes;
  final List<String> access;
  final String status;
  final int tasksCompleted;
  final int tasksFailed;

  Agent({
    required this.id,
    required this.name,
    required this.emoji,
    required this.description,
    required this.modes,
    required this.access,
    required this.status,
    this.tasksCompleted = 0,
    this.tasksFailed = 0,
  });

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      emoji: json['emoji'] ?? '🤖',
      description: json['description'] ?? '',
      modes: (json['modes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      access: (json['access'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      status: json['status'] ?? 'offline',
      tasksCompleted: json['tasksCompleted'] ?? 0,
      tasksFailed: json['tasksFailed'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'emoji': emoji,
        'description': description,
        'modes': modes,
        'access': access,
        'status': status,
        'tasksCompleted': tasksCompleted,
        'tasksFailed': tasksFailed,
      };
}

/// Agents list response
class AgentsResponse {
  final bool ok;
  final List<Agent> agents;
  final String? error;

  AgentsResponse({
    required this.ok,
    required this.agents,
    this.error,
  });

  factory AgentsResponse.fromJson(Map<String, dynamic> json) {
    return AgentsResponse(
      ok: json['ok'] ?? false,
      agents: (json['agents'] as List<dynamic>?)
              ?.map((e) => Agent.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      error: json['error'],
    );
  }
}

/// Agent run request
class AgentRunRequest {
  final String agent;
  final String task;
  final String? mode;
  final String? filePath;
  final String? userId;

  AgentRunRequest({
    required this.agent,
    required this.task,
    this.mode,
    this.filePath,
    this.userId,
  });

  Map<String, dynamic> toJson() {
    final data = {
      'agent': agent,
      'task': task,
    };
    if (mode != null) data['mode'] = mode;
    if (filePath != null) data['file_path'] = filePath;
    if (userId != null) data['user_id'] = userId;
    return data;
  }
}

/// Agent run response
class AgentRunResponse {
  final bool ok;
  final String? result;
  final String? final_;
  final List<dynamic>? steps;
  final List<dynamic>? generatedTools;
  final String? zipPath;
  final String? error;

  AgentRunResponse({
    required this.ok,
    this.result,
    this.final_,
    this.steps,
    this.generatedTools,
    this.zipPath,
    this.error,
  });

  factory AgentRunResponse.fromJson(Map<String, dynamic> json) {
    return AgentRunResponse(
      ok: json['ok'] ?? false,
      result: json['result'],
      final_: json['final'],
      steps: json['steps'] as List<dynamic>?,
      generatedTools: json['generated_tools'] as List<dynamic>?,
      zipPath: json['zip_path'],
      error: json['error'],
    );
  }
}
