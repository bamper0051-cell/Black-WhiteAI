/// Authentication models for login, register, and token refresh
library;

/// Login request
class LoginRequest {
  final String username;
  final String password;

  LoginRequest({
    required this.username,
    required this.password,
  });

  Map<String, dynamic> toJson() => {
        'username': username,
        'password': password,
      };
}

/// Login response
class LoginResponse {
  final bool ok;
  final String? username;
  final String? token;
  final String? role;
  final String? error;

  LoginResponse({
    required this.ok,
    this.username,
    this.token,
    this.role,
    this.error,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      ok: json['ok'] ?? false,
      username: json['username'],
      token: json['token'],
      role: json['role'],
      error: json['error'],
    );
  }
}

/// Register request
class RegisterRequest {
  final String username;
  final String password;

  RegisterRequest({
    required this.username,
    required this.password,
  });

  Map<String, dynamic> toJson() => {
        'username': username,
        'password': password,
      };
}

/// Register response
class RegisterResponse {
  final bool ok;
  final String? username;
  final String? token;
  final String? role;
  final String? error;

  RegisterResponse({
    required this.ok,
    this.username,
    this.token,
    this.role,
    this.error,
  });

  factory RegisterResponse.fromJson(Map<String, dynamic> json) {
    return RegisterResponse(
      ok: json['ok'] ?? false,
      username: json['username'],
      token: json['token'],
      role: json['role'],
      error: json['error'],
    );
  }
}

/// Token refresh request
class RefreshTokenRequest {
  final String refreshToken;

  RefreshTokenRequest({required this.refreshToken});

  Map<String, dynamic> toJson() => {
        'refresh_token': refreshToken,
      };
}

/// Token refresh response
class RefreshTokenResponse {
  final bool ok;
  final String? token;
  final String? refreshToken;
  final String? error;

  RefreshTokenResponse({
    required this.ok,
    this.token,
    this.refreshToken,
    this.error,
  });

  factory RefreshTokenResponse.fromJson(Map<String, dynamic> json) {
    return RefreshTokenResponse(
      ok: json['ok'] ?? false,
      token: json['token'],
      refreshToken: json['refresh_token'],
      error: json['error'],
    );
  }
}

/// User info response
class UserInfoResponse {
  final bool ok;
  final String? username;
  final String? role;
  final String? error;

  UserInfoResponse({
    required this.ok,
    this.username,
    this.role,
    this.error,
  });

  factory UserInfoResponse.fromJson(Map<String, dynamic> json) {
    return UserInfoResponse(
      ok: json['ok'] ?? false,
      username: json['username'],
      role: json['role'],
      error: json['error'],
    );
  }
}
