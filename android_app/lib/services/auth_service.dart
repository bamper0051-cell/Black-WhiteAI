// auth_service.dart — Login, register, session management

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthResult {
  final bool ok;
  final String? token;
  final String? username;
  final String? role;
  final String? error;

  const AuthResult({required this.ok, this.token, this.username, this.role, this.error});
}

class AuthService {
  final String baseUrl;

  AuthService({required this.baseUrl});

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

  Future<AuthResult> login(String username, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: _headers,
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 10));

      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      if (resp.statusCode == 200 && data['ok'] == true) {
        return AuthResult(
          ok: true,
          token: data['token'],
          username: data['username'],
          role: data['role'],
        );
      }
      return AuthResult(ok: false, error: data['error'] ?? 'Login failed');
    } catch (e) {
      return AuthResult(ok: false, error: 'Connection error: $e');
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
        return AuthResult(
          ok: true,
          token: data['token'],
          username: data['username'],
          role: data['role'],
        );
      }
      return AuthResult(ok: false, error: data['error'] ?? 'Registration failed');
    } catch (e) {
      return AuthResult(ok: false, error: 'Connection error: $e');
    }
  }

  Future<bool> ping() async {
    try {
      final resp = await http
          .get(Uri.parse('$baseUrl/ping'))
          .timeout(const Duration(seconds: 5));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Persist session ─────────────────────────────────────────────────────────

  static Future<void> saveSession({
    required String baseUrl,
    required String token,
    required String username,
    required String role,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', baseUrl);
    await prefs.setString('admin_token', token);
    await prefs.setString('username', username);
    await prefs.setString('role', role);
  }

  static Future<Map<String, String?>> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'base_url': prefs.getString('base_url'),
      'token': prefs.getString('admin_token'),
      'username': prefs.getString('username'),
      'role': prefs.getString('role'),
    };
  }

  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('admin_token');
    await prefs.remove('username');
    await prefs.remove('role');
    // Keep base_url so user doesn't have to re-enter server address
  }

  static bool isLoggedIn(Map<String, String?> session) {
    return session['token'] != null && session['base_url'] != null;
  }
}
