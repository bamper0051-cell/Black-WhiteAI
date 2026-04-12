// models.dart — Data models for BlackBugsAI
<<<<<<< HEAD
// FIXED: added 'id' field to AgentInfo, added workspace field
=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

class AgentInfo {
  final String id;
  final String name;
  final String description;
<<<<<<< HEAD
  final String status;       // online | offline | busy
  final String workspace;
  final int    tasksCompleted;
  final int    tasksFailed;
=======
  final String status; // online | offline | busy
  final String workspace;
  final int tasksCompleted;
  final int tasksFailed;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final DateTime? lastActive;

  const AgentInfo({
    required this.id,
    required this.name,
    required this.description,
    required this.status,
<<<<<<< HEAD
    this.workspace = '',
    this.tasksCompleted = 0,
    this.tasksFailed    = 0,
=======
    required this.workspace,
    this.tasksCompleted = 0,
    this.tasksFailed = 0,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    this.lastActive,
  });

  factory AgentInfo.fromJson(Map<String, dynamic> j) => AgentInfo(
<<<<<<< HEAD
        id:          j['id']          ?? j['name']?.toString().toLowerCase() ?? '',
        name:        j['name']        ?? '',
        description: j['description'] ?? j['desc'] ?? '',
        status:      j['status']      ?? 'offline',
        workspace:   j['workspace']   ?? '',
        tasksCompleted: j['tasks_completed']  ?? j['tasksCompleted'] ?? 0,
        tasksFailed:    j['tasks_failed']     ?? j['tasksFailed']    ?? 0,
=======
        id: j['id'] ?? '',
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        status: j['status'] ?? 'offline',
        workspace: j['workspace'] ?? '',
        tasksCompleted: j['tasks_completed'] ?? 0,
        tasksFailed: j['tasks_failed'] ?? 0,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        lastActive: j['last_active'] != null
            ? DateTime.tryParse(j['last_active'])
            : null,
      );

  bool get isOnline => status == 'online';
<<<<<<< HEAD
  bool get isBusy   => status == 'busy';
=======
  bool get isBusy => status == 'busy';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}

class Task {
  final String id;
  final String userId;
  final String type;
  final String title;
<<<<<<< HEAD
  final String status;   // pending | running | done | failed | cancelled
=======
  final String status; // pending | running | done | failed | cancelled
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final String? result;
  final String? error;
  final List<Artifact> artifacts;
  final int retryCount;
  final int maxRetries;
<<<<<<< HEAD
  final DateTime  createdAt;
=======
  final DateTime createdAt;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
    this.artifacts    = const [],
    this.retryCount   = 0,
    this.maxRetries   = 2,
=======
    this.artifacts = const [],
    this.retryCount = 0,
    this.maxRetries = 2,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    required this.createdAt,
    this.startedAt,
    this.finishedAt,
  });

  factory Task.fromJson(Map<String, dynamic> j) {
    List<Artifact> arts = [];
    try {
<<<<<<< HEAD
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
=======
      final rawArts = j['artifacts'];
      if (rawArts != null && rawArts is List) {
        arts = rawArts.map((a) => Artifact.fromJson(a)).toList();
      }
    } catch (_) {}

    return Task(
      id: j['id'] ?? '',
      userId: j['user_id'] ?? '',
      type: j['type'] ?? '',
      title: j['title'] ?? 'Без названия',
      status: j['status'] ?? 'pending',
      result: j['result'],
      error: j['error'],
      artifacts: arts,
      retryCount: j['retry_count'] ?? 0,
      maxRetries: j['max_retries'] ?? 2,
      createdAt: DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
      startedAt: j['started_at'] != null
          ? DateTime.tryParse(j['started_at'])
          : null,
      finishedAt: j['finished_at'] != null
          ? DateTime.tryParse(j['finished_at'])
          : null,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }

  Map<String, dynamic> toJson() => {
<<<<<<< HEAD
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
=======
        'id': id,
        'user_id': userId,
        'type': type,
        'title': title,
        'status': status,
        'result': result,
        'error': error,
        'artifacts': artifacts.map((a) => a.toJson()).toList(),
        'retry_count': retryCount,
        'max_retries': maxRetries,
        'created_at': createdAt.toIso8601String(),
        'started_at': startedAt?.toIso8601String(),
        'finished_at': finishedAt?.toIso8601String(),
      };

  bool get isDone => status == 'done';
  bool get isFailed => status == 'failed';
  bool get isRunning => status == 'running';
  bool get isPending => status == 'pending';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  bool get isCancelled => status == 'cancelled';

  Duration? get duration {
    if (startedAt == null || finishedAt == null) return null;
    return finishedAt!.difference(startedAt!);
  }
}

class Artifact {
<<<<<<< HEAD
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
=======
  final String id;
  final String taskId;
  final String name;
  final String path;
  final String mimeType;
  final int sizeBytes;
  final DateTime createdAt;

  const Artifact({
    required this.id,
    required this.taskId,
    required this.name,
    required this.path,
    required this.mimeType,
    required this.sizeBytes,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    required this.createdAt,
  });

  factory Artifact.fromJson(Map<String, dynamic> j) => Artifact(
<<<<<<< HEAD
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
=======
        id: j['id'] ?? '',
        taskId: j['task_id'] ?? '',
        name: j['name'] ?? '',
        path: j['path'] ?? '',
        mimeType: j['mime_type'] ?? 'application/octet-stream',
        sizeBytes: j['size_bytes'] ?? 0,
        createdAt:
            DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
      );

  String get sizeFormatted {
    if (sizeBytes < 1024) return '${sizeBytes}B';
    if (sizeBytes < 1024 * 1024) return '${(sizeBytes / 1024).toStringAsFixed(1)}KB';
    return '${(sizeBytes / 1024 / 1024).toStringAsFixed(1)}MB';
  }

  bool get isImage =>
      mimeType.startsWith('image/') ||
      name.endsWith('.jpg') ||
      name.endsWith('.png') ||
      name.endsWith('.gif');

  bool get isAudio => mimeType.startsWith('audio/');
  bool get isCode =>
      name.endsWith('.py') ||
      name.endsWith('.js') ||
      name.endsWith('.dart') ||
      name.endsWith('.txt');
  bool get isZip => name.endsWith('.zip');

  Map<String, dynamic> toJson() => {
        'id': id,
        'task_id': taskId,
        'name': name,
        'path': path,
        'mime_type': mimeType,
        'size_bytes': sizeBytes,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
  final List<AgentInfo>    agents;
  final Map<String, int>   tasksByType;
  final DateTime           timestamp;

  const SystemStats({
    required this.totalTasks,   required this.pendingTasks,
    required this.runningTasks, required this.doneTasks,
    required this.failedTasks,  required this.totalUsers,
    required this.agents,       required this.tasksByType,
=======
  final List<AgentInfo> agents;
  final Map<String, int> tasksByType;
  final DateTime timestamp;

  const SystemStats({
    required this.totalTasks,
    required this.pendingTasks,
    required this.runningTasks,
    required this.doneTasks,
    required this.failedTasks,
    required this.totalUsers,
    required this.agents,
    required this.tasksByType,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    required this.timestamp,
  });

  factory SystemStats.fromJson(Map<String, dynamic> j) {
<<<<<<< HEAD
    final queue = j['queue'] as Map<String, dynamic>? ?? {};
    return SystemStats(
      totalTasks:   (queue['total']   as num?)?.toInt() ?? j['total_tasks']   ?? 0,
      pendingTasks: (queue['pending'] as num?)?.toInt() ?? j['pending']       ?? 0,
      runningTasks: (queue['running'] as num?)?.toInt() ?? j['running']       ?? 0,
      doneTasks:    (queue['done']    as num?)?.toInt() ?? j['done']          ?? 0,
      failedTasks:  (queue['failed']  as num?)?.toInt() ?? j['failed']        ?? 0,
      totalUsers:   j['users_total'] ?? j['total_users'] ?? 0,
      agents:       (j['agents'] as List? ?? [])
                        .map((a) => AgentInfo.fromJson(a)).toList(),
      tasksByType:  Map<String, int>.from(j['tasks_by_type'] ?? {}),
      timestamp:    DateTime.now(),
=======
    // Parse from /api/status response
    final queue = j['queue'] as Map<String, dynamic>? ?? {};

    // Compute individual task counts with fallbacks
    final pending = (queue['pending'] as num?)?.toInt() ?? j['pending'] ?? 0;
    final running = (queue['running'] as num?)?.toInt() ?? j['running'] ?? 0;
    final done = (queue['done'] as num?)?.toInt() ?? j['done'] ?? 0;
    final failed = (queue['failed'] as num?)?.toInt() ?? j['failed'] ?? 0;

    // Compute totalTasks: prefer queue['total'], fall back to sum of counts, then j['total_tasks']
    int totalTasks;
    if (queue['total'] != null) {
      totalTasks = (queue['total'] as num).toInt();
    } else if (queue.isNotEmpty) {
      // Sum all numeric values in queue when 'total' is missing
      totalTasks = queue.values.whereType<num>().fold(0, (sum, val) => sum + val.toInt());
    } else {
      totalTasks = j['total_tasks'] ?? 0;
    }

    return SystemStats(
      totalTasks: totalTasks,
      pendingTasks: pending,
      runningTasks: running,
      doneTasks: done,
      failedTasks: failed,
    return SystemStats(
      totalTasks: (queue['total'] as num?)?.toInt() ?? j['total_tasks'] ?? 0,
      pendingTasks: (queue['pending'] as num?)?.toInt() ?? j['pending'] ?? 0,
      runningTasks: (queue['running'] as num?)?.toInt() ?? j['running'] ?? 0,
      doneTasks: (queue['done'] as num?)?.toInt() ?? j['done'] ?? 0,
      failedTasks: (queue['failed'] as num?)?.toInt() ?? j['failed'] ?? 0,
      totalUsers: j['users_total'] ?? j['total_users'] ?? 0,
      agents: (j['agents'] as List? ?? [])
          .map((a) => AgentInfo.fromJson(a))
          .toList(),
      tasksByType: Map<String, int>.from(j['tasks_by_type'] ?? {}),
      timestamp: DateTime.now(),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
  final bool   enabled;
  final bool   isDefault;
=======
  final bool enabled;
  final bool isDefault;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final List<String> models;
  final String? currentModel;

  const LlmProvider({
<<<<<<< HEAD
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
=======
    required this.id,
    required this.name,
    required this.enabled,
    required this.isDefault,
    required this.models,
    this.currentModel,
  });

  factory LlmProvider.fromJson(Map<String, dynamic> j) => LlmProvider(
        id: j['id'] ?? '',
        name: j['name'] ?? '',
        enabled: j['enabled'] ?? false,
        isDefault: j['is_default'] ?? false,
        models: List<String>.from(j['models'] ?? []),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        currentModel: j['current_model'],
      );
}

class AppConfig {
  final String baseUrl;
  final String adminToken;
<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  const AppConfig({required this.baseUrl, required this.adminToken});
}
