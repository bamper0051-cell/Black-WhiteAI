// gcp_models.dart — GCP server and Docker container models

class GcpServerConfig {
  final String host;
  final int    sshPort;
  final String username;
  final int    dockerPort;
  final bool   useHttps;
  final String adminToken;

  const GcpServerConfig({
    required this.host,
    this.sshPort    = 22,
    this.username   = 'ubuntu',
    this.dockerPort = 8080,
    this.useHttps   = false,
    required this.adminToken,
  });

  String get baseUrl {
    final scheme = useHttps ? 'https' : 'http';
    return '$scheme://$host:$dockerPort';
  }
}

class DockerContainerStatus {
  final String id;
  final String name;
  final String status;   // running | stopped | restarting
  final String image;
  final String uptime;
  final double cpuPercent;
  final double memoryMb;

  const DockerContainerStatus({
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
    );
  }
}
