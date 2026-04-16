// models.dart — Data models for BlackBugsAI
// FIXED: added 'id' field to AgentInfo, added workspace field

class AgentInfo {
  final String  id;
  final String? name;
  final String? description;
  final String? status;       // online | offline | busy | active | idle
  final String? workspace;
  final String? emoji;
  final bool?   available;
  final int     tasksCompleted;
  final int     tasksFailed;
  final DateTime? lastActive;

  const AgentInfo({
    required this.id,
    this.name,
    this.description,
    this.status,
    this.workspace,
    this.emoji,
    this.available,
    this.tasksCompleted = 0,
    this.tasksFailed    = 0,
    this.lastActive,
  });

  factory AgentInfo.fromJson(Map<String, dynamic> j) => AgentInfo(
        id:          j['id']          ?? j['name']?.toString().toLowerCase() ?? '',
        name:        j['name']?.toString(),
        description: (j['description'] ?? j['desc'])?.toString(),
        status:      (j['status'])?.toString() ?? 'idle',
        workspace:   j['workspace']?.toString(),
        emoji:       j['emoji']?.toString(),
        available:   j['available'] == true || j['available'] == 1,
        tasksCompleted: (j['tasks_completed'] ?? j['tasksCompleted'] as num? ?? 0).toInt(),
        tasksFailed:    (j['tasks_failed']    ?? j['tasksFailed']    as num? ?? 0).toInt(),
        lastActive: j['last_active'] != null
            ? DateTime.tryParse(j['last_active'].toString())
            : null,
      );

  bool get isOnline => status == 'online' || status == 'active';
  bool get isBusy   => status == 'busy' || status == 'running';
}

class Task {
  final String id;
  final String userId;
  final String type;
  final String title;
  final String status;   // pending | running | done | failed | cancelled
  final String? result;
  final String? error;
  final List<Artifact> artifacts;
  final int retryCount;
  final int maxRetries;
  final DateTime  createdAt;
  final DateTime? startedAt;
  final DateTime? finishedAt;

  const Task({
    required this.id,
    required this.userId,
    required this.type,
    required this.title,
    required this.status,
    this.result,
    this.error,
    this.artifacts    = const [],
    this.retryCount   = 0,
    this.maxRetries   = 2,
    required this.createdAt,
    this.startedAt,
    this.finishedAt,
  });

  factory Task.fromJson(Map<String, dynamic> j) {
    List<Artifact> arts = [];
    try {
      final raw = j['artifacts'];
      if (raw is List) arts = raw.map((a) => Artifact.fromJson(a)).toList();
    } catch (_) {}
    return Task(
      id:         j['id']         ?? j['task_id'] ?? '',
      userId:     j['user_id']    ?? '',
      type:       j['type']       ?? j['task_type'] ?? '',
      title:      j['title']      ?? j['task']    ?? 'Task',
      status:     j['status']     ?? 'pending',
      result:     j['result'],
      error:      j['error'],
      artifacts:  arts,
      retryCount: j['retry_count'] ?? 0,
      maxRetries: j['max_retries'] ?? 2,
      createdAt:  DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
      startedAt:  j['started_at']  != null ? DateTime.tryParse(j['started_at'])  : null,
      finishedAt: j['finished_at'] != null ? DateTime.tryParse(j['finished_at']) : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id, 'user_id': userId, 'type': type, 'title': title,
        'status': status, 'result': result, 'error': error,
        'artifacts': artifacts.map((a) => a.toJson()).toList(),
        'retry_count': retryCount, 'max_retries': maxRetries,
        'created_at':  createdAt.toIso8601String(),
        'started_at':  startedAt?.toIso8601String(),
        'finished_at': finishedAt?.toIso8601String(),
      };

  bool get isDone      => status == 'done';
  bool get isFailed    => status == 'failed';
  bool get isRunning   => status == 'running';
  bool get isPending   => status == 'pending';
  bool get isCancelled => status == 'cancelled';

  Duration? get duration {
    if (startedAt == null || finishedAt == null) return null;
    return finishedAt!.difference(startedAt!);
  }
}

class Artifact {
  final String   id;
  final String   taskId;
  final String   name;
  final String   path;
  final String   mimeType;
  final int      sizeBytes;
  final DateTime createdAt;

  const Artifact({
    required this.id,       required this.taskId,
    required this.name,     required this.path,
    required this.mimeType, required this.sizeBytes,
    required this.createdAt,
  });

  factory Artifact.fromJson(Map<String, dynamic> j) => Artifact(
        id:        j['id']        ?? '',
        taskId:    j['task_id']   ?? '',
        name:      j['name']      ?? '',
        path:      j['path']      ?? '',
        mimeType:  j['mime_type'] ?? 'application/octet-stream',
        sizeBytes: j['size_bytes'] ?? 0,
        createdAt: DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
      );

  String get sizeFormatted {
    if (sizeBytes < 1024)         return '${sizeBytes}B';
    if (sizeBytes < 1024 * 1024)  return '${(sizeBytes / 1024).toStringAsFixed(1)}KB';
    return '${(sizeBytes / 1024 / 1024).toStringAsFixed(1)}MB';
  }

  bool get isImage => mimeType.startsWith('image/') ||
      name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.gif');
  bool get isAudio => mimeType.startsWith('audio/');
  bool get isCode  => name.endsWith('.py') || name.endsWith('.js') ||
      name.endsWith('.dart') || name.endsWith('.txt');
  bool get isZip   => name.endsWith('.zip');

  Map<String, dynamic> toJson() => {
        'id': id, 'task_id': taskId, 'name': name, 'path': path,
        'mime_type': mimeType, 'size_bytes': sizeBytes,
        'created_at': createdAt.toIso8601String(),
      };
}

class SystemStats {
  final int totalTasks;
  final int pendingTasks;
  final int runningTasks;
  final int doneTasks;
  final int failedTasks;
  final int totalUsers;
  final List<AgentInfo>    agents;
  final Map<String, int>   tasksByType;
  final DateTime           timestamp;

  // Extended fields for dashboard
  final double? cpu;
  final double? ram;
  final int?    users;
  final int?    activeTasks;
  final int?    tasksDone;
  final String? botStatus;
  final String? llmProvider;
  final String? tunnelUrl;
  final String? version;
  final List<dynamic> recentTasks;

  const SystemStats({
    required this.totalTasks,   required this.pendingTasks,
    required this.runningTasks, required this.doneTasks,
    required this.failedTasks,  required this.totalUsers,
    required this.agents,       required this.tasksByType,
    required this.timestamp,
    this.cpu, this.ram, this.users, this.activeTasks, this.tasksDone,
    this.botStatus, this.llmProvider, this.tunnelUrl, this.version,
    this.recentTasks = const [],
  });

  factory SystemStats.fromJson(Map<String, dynamic> j) {
    final queue = j['queue'] as Map<String, dynamic>? ?? {};
    final sys   = j['system'] as Map<String, dynamic>? ?? {};
    return SystemStats(
      totalTasks:   (queue['total']   as num?)?.toInt() ?? (j['total_tasks']   as num?)?.toInt() ?? 0,
      pendingTasks: (queue['pending'] as num?)?.toInt() ?? (j['pending']       as num?)?.toInt() ?? 0,
      runningTasks: (queue['running'] as num?)?.toInt() ?? (j['running']       as num?)?.toInt() ?? 0,
      doneTasks:    (queue['done']    as num?)?.toInt() ?? (j['done']          as num?)?.toInt() ?? 0,
      failedTasks:  (queue['failed']  as num?)?.toInt() ?? (j['failed']        as num?)?.toInt() ?? 0,
      totalUsers:   ((j['users_total'] ?? j['total_users']) as num?)?.toInt() ?? 0,
      agents:       (j['agents'] as List? ?? []).map((a) => AgentInfo.fromJson(a as Map<String, dynamic>)).toList(),
      tasksByType:  Map<String, int>.from(j['tasks_by_type'] ?? {}),
      timestamp:    DateTime.now(),
      // Extended
      cpu:         (sys['cpu_percent'] ?? j['cpu'] as num?)?.toDouble(),
      ram:         (sys['ram_percent'] ?? j['ram'] as num?)?.toDouble(),
      users:       (j['users'] ?? j['users_total'] as num?)?.toInt(),
      activeTasks: (queue['running'] as num?)?.toInt() ?? (j['active_tasks'] as num?)?.toInt(),
      tasksDone:   (queue['done']    as num?)?.toInt() ?? (j['done_tasks']   as num?)?.toInt(),
      botStatus:   j['bot_status']?.toString() ?? (j['bot'] != null ? 'running' : null),
      llmProvider: j['llm_provider']?.toString() ?? j['provider']?.toString(),
      tunnelUrl:   j['tunnel_url']?.toString(),
      version:     j['version']?.toString(),
      recentTasks: (j['recent_tasks'] ?? j['tasks'] ?? []) as List,
    );
  }

  double get successRate {
    final total = doneTasks + failedTasks;
    if (total == 0) return 1.0;
    return doneTasks / total;
  }
}

class LlmProvider {
  final String id;
  final String name;
  final bool   enabled;
  final bool   isDefault;
  final List<String> models;
  final String? currentModel;

  const LlmProvider({
    required this.id,       required this.name,
    required this.enabled,  required this.isDefault,
    required this.models,   this.currentModel,
  });

  factory LlmProvider.fromJson(Map<String, dynamic> j) => LlmProvider(
        id:           j['id']             ?? '',
        name:         j['name']           ?? '',
        enabled:      j['enabled']        ?? false,
        isDefault:    j['is_default']     ?? false,
        models:       List<String>.from(j['models'] ?? []),
        currentModel: j['current_model'],
      );
}

class AppConfig {
  final String baseUrl;
  final String adminToken;
  const AppConfig({required this.baseUrl, required this.adminToken});
}
