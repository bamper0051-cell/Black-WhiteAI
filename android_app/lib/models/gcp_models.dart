<<<<<<< HEAD
// gcp_models.dart — GCP server and Docker container models

class GcpServerConfig {
  final String host;
  final int    sshPort;
  final String username;
  final int    dockerPort;
  final bool   useHttps;
=======
// gcp_models.dart — GCP сервер и Docker модели

class GcpServerConfig {
  static const String _keyHost = 'gcp_host';
  static const String _keySshPort = 'gcp_ssh_port';
  static const String _keyUsername = 'gcp_username';
  static const String _keyDockerPort = 'gcp_docker_port';
  static const String _keyUseHttps = 'gcp_use_https';
  static const String _keyAdminToken = 'admin_token';

  final String host;
  final int sshPort;
  final String username;
  final int dockerPort;
  final bool useHttps;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final String adminToken;

  const GcpServerConfig({
    required this.host,
<<<<<<< HEAD
    this.sshPort    = 22,
    this.username   = 'ubuntu',
    this.dockerPort = 8080,
    this.useHttps   = false,
=======
    this.sshPort = 22,
    this.username = 'ubuntu',
    this.dockerPort = 8080,
    this.useHttps = false,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    required this.adminToken,
  });

  String get baseUrl {
    final scheme = useHttps ? 'https' : 'http';
    return '$scheme://$host:$dockerPort';
  }
<<<<<<< HEAD
=======

  Map<String, dynamic> toJson() => {
        _keyHost: host,
        _keySshPort: sshPort,
        _keyUsername: username,
        _keyDockerPort: dockerPort,
        _keyUseHttps: useHttps,
        _keyAdminToken: adminToken,
      };

  factory GcpServerConfig.fromJson(Map<String, dynamic> j) => GcpServerConfig(
        host: j[_keyHost] ?? '',
        sshPort: j[_keySshPort] ?? 22,
        username: j[_keyUsername] ?? 'ubuntu',
        dockerPort: j[_keyDockerPort] ?? 8080,
        useHttps: j[_keyUseHttps] ?? false,
        adminToken: j[_keyAdminToken] ?? '',
      );

  static Map<String, String> prefsKeys() => {
        'host': _keyHost,
        'sshPort': _keySshPort,
        'username': _keyUsername,
        'dockerPort': _keyDockerPort,
        'useHttps': _keyUseHttps,
        'adminToken': _keyAdminToken,
      };
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}

class DockerContainerStatus {
  final String id;
  final String name;
<<<<<<< HEAD
  final String status;   // running | stopped | restarting
=======
  final String status; // running / stopped / restarting
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final String image;
  final String uptime;
  final double cpuPercent;
  final double memoryMb;

  const DockerContainerStatus({
<<<<<<< HEAD
    required this.id,      required this.name,
    required this.status,  required this.image,
    required this.uptime,  required this.cpuPercent,
    required this.memoryMb,
  });

  bool get isRunning    => status == 'running';
  bool get isStopped    => status == 'stopped' || status == 'exited';
  bool get isRestarting => status == 'restarting';

  factory DockerContainerStatus.fromJson(Map<String, dynamic> j) {
    final rawStatus = j['status'] as String? ?? 'unknown';
    String normalized;
    if (j['running'] == true || rawStatus.toLowerCase().startsWith('up')) {
      normalized = 'running';
    } else if (rawStatus.toLowerCase().startsWith('restarting')) {
      normalized = 'restarting';
    } else {
      normalized = 'stopped';
    }
    return DockerContainerStatus(
      id:         j['id']          ?? '',
      name:       j['name']        ?? '',
      status:     normalized,
      image:      j['image']       ?? '',
      uptime:     rawStatus,
      cpuPercent: (j['cpu_percent'] as num?)?.toDouble() ?? 0.0,
      memoryMb:   (j['memory_mb']   as num?)?.toDouble() ?? 0.0,
=======
    required this.id,
    required this.name,
    required this.status,
    required this.image,
    required this.uptime,
    required this.cpuPercent,
    required this.memoryMb,
  });

  bool get isRunning => status == 'running';
  bool get isStopped => status == 'stopped' || status == 'exited';
  bool get isRestarting => status == 'restarting';

  factory DockerContainerStatus.fromJson(Map<String, dynamic> j) {
    // Normalize status: "Up X days" → "running", "Exited..." → "stopped"
    final rawStatus = j['status'] as String? ?? 'unknown';
    String normalizedStatus;
    if (j['running'] == true || rawStatus.toLowerCase().startsWith('up')) {
      normalizedStatus = 'running';
    } else if (rawStatus.toLowerCase().startsWith('restarting')) {
      normalizedStatus = 'restarting';
    } else {
      normalizedStatus = 'stopped';
    }
    return DockerContainerStatus(
      id: j['id'] ?? '',
      name: j['name'] ?? '',
      status: normalizedStatus,
      image: j['image'] ?? '',
      uptime: rawStatus,
      cpuPercent: (j['cpu_percent'] as num?)?.toDouble() ?? 0.0,
      memoryMb: (j['memory_mb'] as num?)?.toDouble() ?? 0.0,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }
}
