// ssh_tunnel_service.dart — GCP/Docker connection configuration service

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/gcp_models.dart';

class SshConnectionConfig {
  final String host;
  final int    port;
  final String username;
  final String privateKeyBase64;
  final int    remotePort;
  final bool   useHttps;
  final String adminToken;

  const SshConnectionConfig({
    required this.host,
    this.port             = 22,
    this.username         = 'ubuntu',
    this.privateKeyBase64 = '',
    this.remotePort       = 8080,
    this.useHttps         = false,
    required this.adminToken,
  });

  static const _prefHost       = 'gcp_host';
  static const _prefSshPort    = 'gcp_ssh_port';
  static const _prefUsername   = 'gcp_username';
  static const _prefPrivKey    = 'gcp_priv_key_b64';
  static const _prefRemotePort = 'gcp_docker_port';
  static const _prefUseHttps   = 'gcp_use_https';
  static const _prefAdminToken = 'admin_token';
}

class SshTunnelService {
  final SshConnectionConfig config;
  SshTunnelService(this.config);

  String buildApiUrl() {
    final scheme = config.useHttps ? 'https' : 'http';
    return '$scheme://${config.host}:${config.remotePort}';
  }

  Future<bool> testConnection() async {
    try {
      final url  = Uri.parse('${buildApiUrl()}/ping');
      final resp = await http.get(url, headers: {
        'X-Admin-Token':  config.adminToken,
        'Authorization': 'Bearer ${config.adminToken}',
      }).timeout(const Duration(seconds: 10));
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (_) {
      return false;
    }
  }

  static Future<void> saveConfig(SshConnectionConfig cfg) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(SshConnectionConfig._prefHost,       cfg.host);
    await prefs.setInt   (SshConnectionConfig._prefSshPort,    cfg.port);
    await prefs.setString(SshConnectionConfig._prefUsername,   cfg.username);
    await prefs.setString(SshConnectionConfig._prefPrivKey,    cfg.privateKeyBase64);
    await prefs.setInt   (SshConnectionConfig._prefRemotePort, cfg.remotePort);
    await prefs.setBool  (SshConnectionConfig._prefUseHttps,   cfg.useHttps);
    await prefs.setString(SshConnectionConfig._prefAdminToken, cfg.adminToken);

    final scheme = cfg.useHttps ? 'https' : 'http';
    await prefs.setString('base_url', '$scheme://${cfg.host}:${cfg.remotePort}');
  }

  static Future<SshConnectionConfig?> loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final host  = prefs.getString(SshConnectionConfig._prefHost);
    if (host == null || host.isEmpty) return null;

    return SshConnectionConfig(
      host:             host,
      port:             prefs.getInt   (SshConnectionConfig._prefSshPort)    ?? 22,
      username:         prefs.getString(SshConnectionConfig._prefUsername)   ?? 'ubuntu',
      privateKeyBase64: prefs.getString(SshConnectionConfig._prefPrivKey)    ?? '',
      remotePort:       prefs.getInt   (SshConnectionConfig._prefRemotePort) ?? 8080,
      useHttps:         prefs.getBool  (SshConnectionConfig._prefUseHttps)   ?? false,
      adminToken:       prefs.getString(SshConnectionConfig._prefAdminToken) ?? '',
    );
  }

  static Future<SshTunnelService?> fromSavedConfig() async {
    final cfg = await loadConfig();
    if (cfg == null) return null;
    return SshTunnelService(cfg);
  }

  GcpServerConfig toGcpConfig() => GcpServerConfig(
        host:       config.host,
        sshPort:    config.port,
        username:   config.username,
        dockerPort: config.remotePort,
        useHttps:   config.useHttps,
        adminToken: config.adminToken,
      );
}
