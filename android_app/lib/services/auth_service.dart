// auth_service.dart — Login, register, session management
// Supports two auth modes:
<<<<<<< HEAD
//   'login' — username + password via /api/auth/login
//   'token' — direct admin token (X-Admin-Token / Bearer)
=======
//   'login'  — username + password via /api/auth/login
//   'token'  — direct admin token (X-Admin-Token / Bearer)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthResult {
<<<<<<< HEAD
  final bool    ok;
=======
  final bool ok;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final String? token;
  final String? username;
  final String? role;
  final String? error;

<<<<<<< HEAD
  const AuthResult({
    required this.ok,
    this.token, this.username, this.role, this.error,
  });
=======
  const AuthResult({required this.ok, this.token, this.username, this.role, this.error});
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}

class AuthService {
  final String baseUrl;
<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  AuthService({required this.baseUrl});

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

<<<<<<< HEAD
  // ── Server auth ───────────────────────────────────────────────────────────
=======
  // ── Server auth mode ─────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  Future<AuthResult> login(String username, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: _headers,
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 10));

      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      if (resp.statusCode == 200 && data['ok'] == true) {
<<<<<<< HEAD
        return AuthResult(ok: true,
            token: data['token'], username: data['username'], role: data['role']);
=======
        return AuthResult(
          ok: true,
          token: data['token'],
          username: data['username'],
          role: data['role'],
        );
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
        return AuthResult(ok: true,
            token: data['token'], username: data['username'], role: data['role']);
=======
        return AuthResult(
          ok: true,
          token: data['token'],
          username: data['username'],
          role: data['role'],
        );
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      }
      return AuthResult(ok: false, error: data['error'] ?? 'Registration failed');
    } catch (e) {
      return AuthResult(ok: false, error: 'Ошибка подключения: $e');
    }
  }

<<<<<<< HEAD
  // ── Token mode ─────────────────────────────────────────────────────────────

  Future<AuthResult> validateToken(String token) async {
    try {
      final resp = await http.get(
        Uri.parse('$baseUrl/api/status'),
        headers: {'X-Admin-Token': token, 'Authorization': 'Bearer $token'},
=======
  // ── Token mode ───────────────────────────────────────────────────────────────

  /// Validates a raw admin token by hitting /ping or /api/stats
  Future<AuthResult> validateToken(String token) async {
    try {
      final resp = await http.get(
        Uri.parse('$baseUrl/api/stats'),
        headers: {
          'Authorization': 'Bearer $token',
          'X-Admin-Token': token,
        },
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode == 200) {
        return AuthResult(ok: true, token: token, username: 'admin', role: 'admin');
      }
      if (resp.statusCode == 401 || resp.statusCode == 403) {
        return AuthResult(ok: false, error: 'Неверный токен');
      }
<<<<<<< HEAD
      // 404 = endpoint missing but server alive
=======
      // If endpoint doesn't exist but server is alive, token is accepted
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      if (resp.statusCode == 404) {
        return AuthResult(ok: true, token: token, username: 'admin', role: 'admin');
      }
      return AuthResult(ok: false, error: 'Сервер вернул ${resp.statusCode}');
    } catch (e) {
      return AuthResult(ok: false, error: 'Ошибка подключения: $e');
    }
  }

<<<<<<< HEAD
  // ── Ping ───────────────────────────────────────────────────────────────────
=======
  // ── Ping ─────────────────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  Future<bool> ping() async {
    try {
      final resp = await http
          .get(Uri.parse('$baseUrl/ping'))
<<<<<<< HEAD
          .timeout(const Duration(seconds: 6));
=======
          .timeout(const Duration(seconds: 5));
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

<<<<<<< HEAD
  // ── Session persistence ────────────────────────────────────────────────────

=======
  // ── Session persistence ──────────────────────────────────────────────────────

  /// [authMode] must be 'login' or 'token'
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  static Future<void> saveSession({
    required String baseUrl,
    required String token,
    required String username,
    required String role,
<<<<<<< HEAD
    required String authMode,  // 'login' | 'token'
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url',    baseUrl);
    await prefs.setString('admin_token', token);
    await prefs.setString('username',    username);
    await prefs.setString('role',        role);
    await prefs.setString('auth_mode',   authMode);
=======
    required String authMode,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', baseUrl);
    await prefs.setString('admin_token', token);
    await prefs.setString('username', username);
    await prefs.setString('role', role);
    await prefs.setString('auth_mode', authMode);
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }

  static Future<Map<String, String?>> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    return {
<<<<<<< HEAD
      'base_url':  prefs.getString('base_url'),
      'token':     prefs.getString('admin_token'),
      'username':  prefs.getString('username'),
      'role':      prefs.getString('role'),
      'auth_mode': prefs.getString('auth_mode'),
    };
  }

  /// Clears credentials but keeps base_url + auth_mode
=======
      'base_url':   prefs.getString('base_url'),
      'token':      prefs.getString('admin_token'),
      'username':   prefs.getString('username'),
      'role':       prefs.getString('role'),
      'auth_mode':  prefs.getString('auth_mode'),
    };
  }

  /// Clears credentials but keeps base_url and auth_mode
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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

<<<<<<< HEAD
  static bool isLoggedIn(Map<String, String?> session) =>
      session['token'] != null &&
      session['token']!.isNotEmpty &&
      session['base_url'] != null;
=======
  static bool isLoggedIn(Map<String, String?> session) {
    return session['token'] != null &&
        session['token']!.isNotEmpty &&
        session['base_url'] != null;
  }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}
