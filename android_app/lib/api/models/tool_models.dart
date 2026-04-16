/// Tool models for tool listing and management
library;

/// Tool model
class Tool {
  final String id;
  final String name;
  final String description;
  final String? category;
  final Map<String, dynamic>? parameters;

  Tool({
    required this.id,
    required this.name,
    required this.description,
    this.category,
    this.parameters,
  });

  factory Tool.fromJson(Map<String, dynamic> json) {
    return Tool(
      id: json['id'] ?? json['name'] ?? '',
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      category: json['category'],
      parameters: json['parameters'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        if (category != null) 'category': category,
        if (parameters != null) 'parameters': parameters,
      };
}

/// Tools list response
class ToolsResponse {
  final bool ok;
  final List<Tool> tools;
  final String? error;

  ToolsResponse({
    required this.ok,
    required this.tools,
    this.error,
  });

  factory ToolsResponse.fromJson(Map<String, dynamic> json) {
    return ToolsResponse(
      ok: json['ok'] ?? false,
      tools: (json['tools'] as List<dynamic>?)
              ?.map((e) => Tool.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      error: json['error'],
    );
  }
}

/// Tool delete request
class ToolDeleteRequest {
  final String toolName;

  ToolDeleteRequest({required this.toolName});

  Map<String, dynamic> toJson() => {
        'tool_name': toolName,
      };
}

/// Tool delete response
class ToolDeleteResponse {
  final bool ok;
  final String? message;
  final String? error;

  ToolDeleteResponse({
    required this.ok,
    this.message,
    this.error,
  });

  factory ToolDeleteResponse.fromJson(Map<String, dynamic> json) {
    return ToolDeleteResponse(
      ok: json['ok'] ?? false,
      message: json['message'],
      error: json['error'],
    );
  }
}
