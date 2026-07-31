/// Log models for retrieving system logs
library;

/// Log entry model
class LogEntry {
  final String timestamp;
  final String text;
  final String level;

  LogEntry({
    required this.timestamp,
    required this.text,
    required this.level,
  });

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    return LogEntry(
      timestamp: json['ts'] ?? json['timestamp'] ?? '',
      text: json['text'] ?? json['message'] ?? '',
      level: json['level'] ?? 'INFO',
    );
  }

  Map<String, dynamic> toJson() => {
        'ts': timestamp,
        'text': text,
        'level': level,
      };
}

/// Logs response
class LogsResponse {
  final bool ok;
  final List<LogEntry> logs;
  final String? lastError;
  final String? source;
  final String? error;

  LogsResponse({
    required this.ok,
    required this.logs,
    this.lastError,
    this.source,
    this.error,
  });

  factory LogsResponse.fromJson(Map<String, dynamic> json) {
    return LogsResponse(
      ok: json['ok'] ?? false,
      logs: (json['logs'] as List<dynamic>?)
              ?.map((e) => LogEntry.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      lastError: json['last_error'],
      source: json['source'],
      error: json['error'],
    );
  }
}
