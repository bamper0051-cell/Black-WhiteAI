import 'dart:convert';
import 'package:http/http.dart' as http;
import 'database_service.dart';

/// Terminal service for executing commands through the API
class TerminalService {
  final String baseUrl;
  final String token;
  final DatabaseService _db = DatabaseService.instance;

  TerminalService({required this.baseUrl, required this.token});

  /// Execute a command remotely via API
  Future<Map<String, dynamic>> executeRemoteCommand(String command) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/terminal/execute'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'command': command}),
      );

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        // Save execution to history
        await _db.saveExecution({
          'command_id': null,
          'output': result['output'] ?? '',
          'status': 'success',
          'executed_at': DateTime.now().toIso8601String(),
        });

        return {
          'success': true,
          'output': result['output'] ?? '',
          'error': null,
        };
      } else {
        final error = 'Failed to execute command: ${response.statusCode}';
        await _db.saveExecution({
          'command_id': null,
          'output': error,
          'status': 'error',
          'executed_at': DateTime.now().toIso8601String(),
        });

        return {
          'success': false,
          'output': '',
          'error': error,
        };
      }
    } catch (e) {
      final error = 'Exception: $e';
      await _db.saveExecution({
        'command_id': null,
        'output': error,
        'status': 'error',
        'executed_at': DateTime.now().toIso8601String(),
      });

      return {
        'success': false,
        'output': '',
        'error': error,
      };
    }
  }

  /// Execute a saved command
  Future<Map<String, dynamic>> executeSavedCommand(int commandId) async {
    final command = await _db.getCommand(commandId);
    if (command == null) {
      return {
        'success': false,
        'output': '',
        'error': 'Command not found',
      };
    }

    // Update last_used timestamp
    await _db.updateCommand(commandId, {
      ...command,
      'last_used': DateTime.now().toIso8601String(),
    });

    return await executeRemoteCommand(command['command'] as String);
  }

  /// Get command suggestions from API
  Future<List<String>> getCommandSuggestions(String partial) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/terminal/suggestions?query=$partial'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);
        return List<String>.from(result['suggestions'] ?? []);
      }
    } catch (e) {
      // Return empty list on error
    }

    return [];
  }

  /// Get terminal history
  Future<List<Map<String, dynamic>>> getHistory({int limit = 50}) async {
    return await _db.getExecutionHistory(limit: limit);
  }

  /// Save a command for later use
  Future<int> saveCommand({
    required String name,
    required String command,
    String? description,
  }) async {
    return await _db.insertCommand({
      'name': name,
      'command': command,
      'description': description,
      'created_at': DateTime.now().toIso8601String(),
    });
  }

  /// Get all saved commands
  Future<List<Map<String, dynamic>>> getSavedCommands() async {
    return await _db.getAllCommands();
  }

  /// Delete a saved command
  Future<bool> deleteCommand(int id) async {
    final result = await _db.deleteCommand(id);
    return result > 0;
  }
}
