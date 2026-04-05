import 'dart:async';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

/// Local database service for storing commands and memory
class DatabaseService {
  static Database? _database;
  static final DatabaseService instance = DatabaseService._init();

  DatabaseService._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('blackbugsai.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future<void> _createDB(Database db, int version) async {
    // Commands table
    await db.execute('''
      CREATE TABLE commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        command TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        last_used TEXT
      )
    ''');

    // Memory/context table
    await db.execute('''
      CREATE TABLE memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        context_key TEXT NOT NULL,
        context_value TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    ''');

    // Execution history
    await db.execute('''
      CREATE TABLE execution_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_id INTEGER,
        output TEXT,
        status TEXT,
        executed_at TEXT NOT NULL,
        FOREIGN KEY (command_id) REFERENCES commands (id)
      )
    ''');
  }

  // Commands CRUD operations
  Future<int> insertCommand(Map<String, dynamic> command) async {
    final db = await database;
    return await db.insert('commands', command);
  }

  Future<List<Map<String, dynamic>>> getAllCommands() async {
    final db = await database;
    return await db.query('commands', orderBy: 'last_used DESC');
  }

  Future<Map<String, dynamic>?> getCommand(int id) async {
    final db = await database;
    final results = await db.query(
      'commands',
      where: 'id = ?',
      whereArgs: [id],
    );
    return results.isNotEmpty ? results.first : null;
  }

  Future<int> updateCommand(int id, Map<String, dynamic> command) async {
    final db = await database;
    return await db.update(
      'commands',
      command,
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> deleteCommand(int id) async {
    final db = await database;
    return await db.delete(
      'commands',
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  // Memory CRUD operations
  Future<int> saveMemory(String key, String value) async {
    final db = await database;
    final now = DateTime.now().toIso8601String();

    final existing = await db.query(
      'memory',
      where: 'context_key = ?',
      whereArgs: [key],
    );

    if (existing.isNotEmpty) {
      return await db.update(
        'memory',
        {'context_value': value, 'updated_at': now},
        where: 'context_key = ?',
        whereArgs: [key],
      );
    } else {
      return await db.insert('memory', {
        'context_key': key,
        'context_value': value,
        'created_at': now,
        'updated_at': now,
      });
    }
  }

  Future<String?> getMemory(String key) async {
    final db = await database;
    final results = await db.query(
      'memory',
      where: 'context_key = ?',
      whereArgs: [key],
    );
    return results.isNotEmpty ? results.first['context_value'] as String? : null;
  }

  Future<List<Map<String, dynamic>>> getAllMemory() async {
    final db = await database;
    return await db.query('memory', orderBy: 'updated_at DESC');
  }

  Future<int> deleteMemory(String key) async {
    final db = await database;
    return await db.delete(
      'memory',
      where: 'context_key = ?',
      whereArgs: [key],
    );
  }

  // Execution history
  Future<int> saveExecution(Map<String, dynamic> execution) async {
    final db = await database;
    return await db.insert('execution_history', execution);
  }

  Future<List<Map<String, dynamic>>> getExecutionHistory({int limit = 50}) async {
    final db = await database;
    return await db.query(
      'execution_history',
      orderBy: 'executed_at DESC',
      limit: limit,
    );
  }

  Future<void> close() async {
    final db = await database;
    await db.close();
  }
}
