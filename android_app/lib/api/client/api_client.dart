/// API Client with Dio, token authentication, and automatic token refresh
library;

import 'package:dio/dio.dart';
import 'package:dio_smart_retry/dio_smart_retry.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  late final Dio _dio;
  final String baseUrl;
  String? _accessToken;
  String? _refreshToken;

  static const String _accessTokenKey = 'api_access_token';
  static const String _refreshTokenKey = 'api_refresh_token';

  ApiClient({
    required this.baseUrl,
    String? accessToken,
    String? refreshToken,
  })  : _accessToken = accessToken,
        _refreshToken = refreshToken {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add retry interceptor
    _dio.interceptors.add(RetryInterceptor(
      dio: _dio,
      retries: 3,
      retryDelays: const [
        Duration(seconds: 1),
        Duration(seconds: 2),
        Duration(seconds: 3),
      ],
    ));

    // Add auth interceptor
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
          options.headers['X-Admin-Token'] = _accessToken;
          options.headers['X-Api-Key'] = _accessToken;
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        // Handle 401 errors - attempt token refresh
        if (error.response?.statusCode == 401 && _refreshToken != null) {
          try {
            await _refreshAccessToken();
            // Retry the request with new token
            final options = error.requestOptions;
            options.headers['Authorization'] = 'Bearer $_accessToken';
            options.headers['X-Admin-Token'] = _accessToken;
            options.headers['X-Api-Key'] = _accessToken;
            final response = await _dio.fetch(options);
            return handler.resolve(response);
          } catch (e) {
            // Refresh failed, clear tokens
            await clearTokens();
            return handler.next(error);
          }
        }
        return handler.next(error);
      },
    ));

    // Add logging interceptor (debug mode only)
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      error: true,
      logPrint: (log) => print('[API] $log'),
    ));
  }

  /// Create API client from saved credentials
  static Future<ApiClient> fromSavedCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('base_url') ?? '';
    final accessToken = prefs.getString(_accessTokenKey);
    final refreshToken = prefs.getString(_refreshTokenKey);

    return ApiClient(
      baseUrl: baseUrl,
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
  }

  /// Set access token
  Future<void> setAccessToken(String token) async {
    _accessToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessTokenKey, token);
  }

  /// Set refresh token
  Future<void> setRefreshToken(String token) async {
    _refreshToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_refreshTokenKey, token);
  }

  /// Set both tokens at once
  Future<void> setTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    await setAccessToken(accessToken);
    if (refreshToken != null) {
      await setRefreshToken(refreshToken);
    }
  }

  /// Clear all tokens
  Future<void> clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_refreshTokenKey);
  }

  /// Get current access token
  String? get accessToken => _accessToken;

  /// Get current refresh token
  String? get refreshToken => _refreshToken;

  /// Refresh access token using refresh token
  Future<void> _refreshAccessToken() async {
    if (_refreshToken == null) {
      throw Exception('No refresh token available');
    }

    final response = await _dio.post(
      '/api/auth/refresh',
      data: {'refresh_token': _refreshToken},
    );

    if (response.statusCode == 200 && response.data['ok'] == true) {
      final newAccessToken = response.data['token'] as String?;
      if (newAccessToken != null) {
        await setAccessToken(newAccessToken);
      }

      // Update refresh token if provided
      final newRefreshToken = response.data['refresh_token'] as String?;
      if (newRefreshToken != null) {
        await setRefreshToken(newRefreshToken);
      }
    } else {
      throw Exception('Token refresh failed');
    }
  }

  /// Make a GET request
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _dio.get<T>(
      path,
      queryParameters: queryParameters,
      options: options,
      cancelToken: cancelToken,
    );
  }

  /// Make a POST request
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
      cancelToken: cancelToken,
    );
  }

  /// Make a PUT request
  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _dio.put<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
      cancelToken: cancelToken,
    );
  }

  /// Make a DELETE request
  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _dio.delete<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
      cancelToken: cancelToken,
    );
  }

  /// Get underlying Dio instance for advanced usage
  Dio get dio => _dio;
}
