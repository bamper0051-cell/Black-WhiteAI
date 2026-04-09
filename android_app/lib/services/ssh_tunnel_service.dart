// ssh_tunnel_service.dart — GCP/Docker connection service
//
// Android не позволяет легко создавать нативные SSH-туннели без нативных
// библиотек. Данный сервис реализует подключение напрямую к публичному IP GCP
// через HTTP/HTTPS на порту Docker-контейнера. SSH credentials сохраняются
// в SharedPreferences для будущего использования нативной SSH-библиотеки.

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/gcp_models.dart';

class SshConnectionConfig {
  /// Публичный IP или hostname GCP виртуальной машины
  final String host;

  /// SSH порт (дефолт 22)
  final int port;

  /// SSH пользователь (дефолт ubuntu)
  final String username;

  /// Приватный SSH-ключ в base64 (сохраняется для будущей нативной интеграции)
  final String privateKeyBase64;

  /// Порт Docker сервиса на GCP VM (дефолт 8080)
  final int remotePort;

  /// Использовать HTTPS вместо HTTP
  final bool useHttps;

  /// Токен авторизации администратора
  final String adminToken;

  const SshConnectionConfig({
    required this.host,
    this.port = 22,
    this.username = 'ubuntu',
    this.privateKeyBase64 = '',
    this.remotePort = 8080,
    this.useHttps = false,
    required this.adminToken,
  });

  static const String _prefHost = 'gcp_host';
  static const String _prefSshPort = 'gcp_ssh_port';
  static const String _prefUsername = 'gcp_username';
  static const String _prefPrivKey = 'gcp_priv_key_b64';
  static const String _prefRemotePort = 'gcp_docker_port';
  static const String _prefUseHttps = 'gcp_use_https';
  static const String _prefAdminToken = 'admin_token';
}

class SshTunnelService {
  final SshConnectionConfig config;

  SshTunnelService(this.config);

  /// Возвращает базовый URL API в зависимости от конфигурации.
  /// Подключение идёт напрямую к публичному IP GCP на порту Docker-сервиса.
  String buildApiUrl() {
    final scheme = config.useHttps ? 'https' : 'http';
    return '$scheme://${config.host}:${config.remotePort}';
  }

  /// Проверяет доступность сервера через GET /api/health
  Future<bool> testConnection() async {
    try {
      final url = Uri.parse('${buildApiUrl()}/api/health');
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer ${config.adminToken}',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
  }

  /// Сохраняет конфигурацию в SharedPreferences
  static Future<void> saveConfig(SshConnectionConfig cfg) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(SshConnectionConfig._prefHost, cfg.host);
    await prefs.setInt(SshConnectionConfig._prefSshPort, cfg.port);
    await prefs.setString(SshConnectionConfig._prefUsername, cfg.username);
    await prefs.setString(SshConnectionConfig._prefPrivKey, cfg.privateKeyBase64);
    await prefs.setInt(SshConnectionConfig._prefRemotePort, cfg.remotePort);
    await prefs.setBool(SshConnectionConfig._prefUseHttps, cfg.useHttps);
    await prefs.setString(SshConnectionConfig._prefAdminToken, cfg.adminToken);

    // Синхронизируем base_url для совместимости с остальным кодом
    final scheme = cfg.useHttps ? 'https' : 'http';
    await prefs.setString('base_url', '$scheme://${cfg.host}:${cfg.remotePort}');
  }

  /// Загружает конфигурацию из SharedPreferences
  static Future<SshConnectionConfig?> loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final host = prefs.getString(SshConnectionConfig._prefHost);
    if (host == null || host.isEmpty) return null;

    return SshConnectionConfig(
      host: host,
      port: prefs.getInt(SshConnectionConfig._prefSshPort) ?? 22,
      username: prefs.getString(SshConnectionConfig._prefUsername) ?? 'ubuntu',
      privateKeyBase64: prefs.getString(SshConnectionConfig._prefPrivKey) ?? '',
      remotePort: prefs.getInt(SshConnectionConfig._prefRemotePort) ?? 8080,
      useHttps: prefs.getBool(SshConnectionConfig._prefUseHttps) ?? false,
      adminToken: prefs.getString(SshConnectionConfig._prefAdminToken) ?? '',
    );
  }

  /// Создаёт SshTunnelService из сохранённой конфигурации
  static Future<SshTunnelService?> fromSavedConfig() async {
    final cfg = await loadConfig();
    if (cfg == null) return null;
    return SshTunnelService(cfg);
  }

  /// Конвертирует конфигурацию в GcpServerConfig (для совместимости)
  GcpServerConfig toGcpConfig() => GcpServerConfig(
        host: config.host,
        sshPort: config.port,
        username: config.username,
        dockerPort: config.remotePort,
        useHttps: config.useHttps,
        adminToken: config.adminToken,
      );
}
