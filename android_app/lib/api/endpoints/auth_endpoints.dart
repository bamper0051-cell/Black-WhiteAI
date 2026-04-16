/// Authentication endpoints
library;

import '../client/api_client.dart';
import '../models/auth_models.dart';

class AuthEndpoints {
  final ApiClient _client;

  AuthEndpoints(this._client);

  /// Login with username and password
  Future<LoginResponse> login(LoginRequest request) async {
    try {
      final response = await _client.post(
        '/api/auth/login',
        data: request.toJson(),
      );

      final loginResponse = LoginResponse.fromJson(response.data);

      // Save tokens if login successful
      if (loginResponse.ok && loginResponse.token != null) {
        await _client.setTokens(
          accessToken: loginResponse.token!,
          refreshToken: loginResponse.token, // Use same token for refresh in this API
        );
      }

      return loginResponse;
    } catch (e) {
      return LoginResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }

  /// Register a new user
  Future<RegisterResponse> register(RegisterRequest request) async {
    try {
      final response = await _client.post(
        '/api/auth/register',
        data: request.toJson(),
      );

      final registerResponse = RegisterResponse.fromJson(response.data);

      // Save tokens if registration successful
      if (registerResponse.ok && registerResponse.token != null) {
        await _client.setTokens(
          accessToken: registerResponse.token!,
          refreshToken: registerResponse.token,
        );
      }

      return registerResponse;
    } catch (e) {
      return RegisterResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }

  /// Get current user info
  Future<UserInfoResponse> getUserInfo() async {
    try {
      final response = await _client.get('/api/auth/me');
      return UserInfoResponse.fromJson(response.data);
    } catch (e) {
      return UserInfoResponse(
        ok: false,
        error: e.toString(),
      );
    }
  }

  /// Logout (clear tokens)
  Future<void> logout() async {
    await _client.clearTokens();
  }
}
