/// Log endpoints
library;

import '../client/api_client.dart';
import '../models/log_models.dart';

class LogEndpoints {
  final ApiClient _client;

  LogEndpoints(this._client);

  /// Get system logs
  ///
  /// Parameters:
  /// - [n]: Number of logs to retrieve (max 500, default 100)
  /// - [level]: Filter by log level (INFO, WARN, ERROR)
  /// - [userId]: Filter by user ID
  Future<LogsResponse> getLogs({
    int n = 100,
    String? level,
    String? userId,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'n': n.clamp(1, 500),
      };

      if (level != null && level.isNotEmpty) {
        queryParams['level'] = level;
      }

      if (userId != null && userId.isNotEmpty) {
        queryParams['user_id'] = userId;
      }

      final response = await _client.get(
        '/api/logs',
        queryParameters: queryParams,
      );

      return LogsResponse.fromJson(response.data);
    } catch (e) {
      return LogsResponse(
        ok: false,
        logs: [],
        error: e.toString(),
      );
    }
  }
}
