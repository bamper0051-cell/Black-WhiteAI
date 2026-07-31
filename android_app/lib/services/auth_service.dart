// auth_service.dart — Login, register, session management
// Supports two auth modes:
//   'login' — username + password via /api/auth/login
//   'token' — direct admin token (X-Admin-Token / Bearer)

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthResult {
  final bool    ok;
  final String? token;
  final String? username;
  final String? role;
  final String? error;

  const AuthResult({
    required this.ok,
    this.token, this.username, this.role, this.error,
  });
}

class AuthService {
  final String baseUrl;
  AuthService({required this.baseUrl});

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

  // ── Server auth ───────────────────────────────────────────────────────────

  Future<AuthResult> login(String username, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: _headers,
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 10));

      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      if (resp.statusCode == 200 && data['ok'] == true) {
        return AuthResult(ok: true,
            token: data['token'], username: data['username'], role: data['role']);
      }
      return AuthResult(ok: false, error: data['error'] ?? 'Login failed');
    } catch (e) {
      return AuthResult(ok: false, error: 'Ошибка подключения: $e');
    }
  }

  Future<AuthResult> register(String username, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/register'),
        headers: _headers,
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 10));

      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      if ((resp.statusCode == 200 || resp.statusCode == 201) && data['ok'] == true) {
        return AuthResult(ok: true,
            token: data['token'], username: data['username'], role: data['role']);
      }
      return AuthResult(ok: false, error: data['error'] ?? 'Registration failed');
    } catch (e) {
      return AuthResult(ok: false, error: 'Ошибка подключения: $e');
    }
  }

  // ── Token mode ─────────────────────────────────────────────────────────────

  Future<AuthResult> validateToken(String token) async {
    try {
      final resp = await http.get(
        Uri.parse('$baseUrl/api/status'),
        headers: {'X-Admin-Token': token, 'Authorization': 'Bearer $token'},
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode == 200) {
        return AuthResult(ok: true, token: token, username: 'admin', role: 'admin');
      }
      if (resp.statusCode == 401 || resp.statusCode == 403) {
        return AuthResult(ok: false, error: 'Неверный токен');
      }
      // 404 = endpoint missing but server alive
      if (resp.statusCode == 404) {
        return AuthResult(ok: true, token: token, username: 'admin', role: 'admin');
      }
      return AuthResult(ok: false, error: 'Сервер вернул ${resp.statusCode}');
    } catch (e) {
      return AuthResult(ok: false, error: 'Ошибка подключения: $e');
    }
  }

  // ── Ping ───────────────────────────────────────────────────────────────────

  Future<bool> ping() async {
    try {
      final resp = await http
          .get(Uri.parse('$baseUrl/ping'))
          .timeout(const Duration(seconds: 6));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Session persistence ────────────────────────────────────────────────────

  static Future<void> saveSession({
    required String baseUrl,
    required String token,
    required String username,
    required String role,
    required String authMode,  // 'login' | 'token'
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url',    baseUrl);
    await prefs.setString('admin_token', token);
    await prefs.setString('username',    username);
    await prefs.setString('role',        role);
    await prefs.setString('auth_mode',   authMode);
  }

  static Future<Map<String, String?>> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'base_url':  prefs.getString('base_url'),
      'token':     prefs.getString('admin_token'),
      'username':  prefs.getString('username'),
      'role':      prefs.getString('role'),
      'auth_mode': prefs.getString('auth_mode'),
    };
  }

  /// Clears credentials but keeps base_url + auth_mode
  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('admin_token');
    await prefs.remove('username');
    await prefs.remove('role');
  }

  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  static bool isLoggedIn(Map<String, String?> session) =>
      session['token'] != null &&
      session['token']!.isNotEmpty &&
      session['base_url'] != null;
}
