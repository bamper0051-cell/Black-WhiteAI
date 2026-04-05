# Backend API Endpoints для Terminal Service

## Требуемые эндпоинты

Для полной функциональности Terminal Service в Android приложении, необходимо добавить следующие API эндпоинты на backend.

### 1. Execute Command

**Endpoint**: `POST /api/terminal/execute`

**Headers**:
```
Authorization: Bearer <ADMIN_TOKEN>
Content-Type: application/json
```

**Request Body**:
```json
{
  "command": "ls -la"
}
```

**Response** (Success):
```json
{
  "success": true,
  "output": "total 48\ndrwxr-xr-x 12 user user 4096 Apr 5 01:00 .\n...",
  "exit_code": 0,
  "executed_at": "2026-04-05T01:23:45Z"
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": "Command execution failed",
  "exit_code": 1,
  "executed_at": "2026-04-05T01:23:45Z"
}
```

**Python Implementation Example**:
```python
@app.route('/api/terminal/execute', methods=['POST'])
@require_token
def execute_terminal_command():
    """Execute a shell command and return output"""
    try:
        data = request.json
        command = data.get('command', '')

        if not command:
            return jsonify({'success': False, 'error': 'No command provided'}), 400

        # Security: validate command against whitelist or implement proper sandboxing
        # For production, consider using a command whitelist

        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'exit_code': result.returncode,
            'executed_at': datetime.utcnow().isoformat() + 'Z'
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Command execution timeout',
            'exit_code': -1,
            'executed_at': datetime.utcnow().isoformat() + 'Z'
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'exit_code': -1,
            'executed_at': datetime.utcnow().isoformat() + 'Z'
        }), 500
```

### 2. Get Command Suggestions

**Endpoint**: `GET /api/terminal/suggestions?query=<partial_command>`

**Headers**:
```
Authorization: Bearer <ADMIN_TOKEN>
```

**Query Parameters**:
- `query` - частичная команда для автодополнения

**Response**:
```json
{
  "suggestions": [
    "systemctl status",
    "systemctl restart",
    "systemctl stop"
  ]
}
```

**Python Implementation Example**:
```python
COMMON_COMMANDS = [
    'systemctl status',
    'systemctl restart',
    'systemctl stop',
    'docker ps',
    'docker ps -a',
    'docker logs',
    'docker compose up',
    'docker compose down',
    'ls -la',
    'cd',
    'cat',
    'tail -f',
    'grep',
    'find',
    'ps aux',
    'top',
    'htop',
    'df -h',
    'free -m',
    'netstat -tuln',
    'ss -tuln',
]

@app.route('/api/terminal/suggestions', methods=['GET'])
@require_token
def get_command_suggestions():
    """Get command suggestions based on partial input"""
    query = request.args.get('query', '').lower()

    if not query:
        return jsonify({'suggestions': COMMON_COMMANDS[:10]})

    suggestions = [cmd for cmd in COMMON_COMMANDS if query in cmd.lower()]

    return jsonify({'suggestions': suggestions[:10]})
```

### 3. Get Command History (Optional)

**Endpoint**: `GET /api/terminal/history?limit=50`

**Headers**:
```
Authorization: Bearer <ADMIN_TOKEN>
```

**Query Parameters**:
- `limit` - количество записей (default: 50)

**Response**:
```json
{
  "history": [
    {
      "id": 123,
      "command": "docker ps -a",
      "output": "CONTAINER ID   IMAGE     ...",
      "exit_code": 0,
      "executed_at": "2026-04-05T01:20:00Z"
    },
    {
      "id": 122,
      "command": "systemctl status",
      "output": "...",
      "exit_code": 0,
      "executed_at": "2026-04-05T01:15:00Z"
    }
  ]
}
```

## Соображения безопасности

### 1. Аутентификация
- Все эндпоинты должны требовать `ADMIN_TOKEN`
- Использовать `@require_token` декоратор

### 2. Валидация команд
Рекомендуется один из подходов:

**Whitelist подход** (рекомендуется для production):
```python
ALLOWED_COMMANDS = {
    'systemctl': ['status', 'restart', 'stop'],
    'docker': ['ps', 'logs', 'inspect'],
    'ls': ['-la', '-lh'],
    # ... другие разрешённые команды
}

def validate_command(command):
    """Validate command against whitelist"""
    parts = command.split()
    if not parts:
        return False

    base_cmd = parts[0]
    if base_cmd not in ALLOWED_COMMANDS:
        return False

    # Check subcommands if needed
    return True
```

**Blacklist подход** (менее безопасный):
```python
DANGEROUS_PATTERNS = [
    'rm -rf',
    'mkfs',
    'dd if=',
    '>/dev/sd',
    'format',
    ':(){:|:&};:',  # fork bomb
    # ... другие опасные команды
]

def is_dangerous_command(command):
    """Check if command contains dangerous patterns"""
    command_lower = command.lower()
    return any(pattern in command_lower for pattern in DANGEROUS_PATTERNS)
```

### 3. Sandboxing
Для дополнительной безопасности:
```python
import subprocess

def execute_sandboxed(command):
    """Execute command in sandboxed environment"""
    # Use timeout to prevent hanging
    # Use specific user with limited permissions
    # Limit resource usage
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
        user='limited_user',  # Run as limited user
        cwd='/tmp',  # Run in specific directory
    )
    return result
```

### 4. Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/terminal/execute', methods=['POST'])
@require_token
@limiter.limit("10 per minute")
def execute_terminal_command():
    # ... implementation
    pass
```

## Интеграция с существующим кодом

Рекомендуется добавить эти эндпоинты в `admin_web.py`:

```python
# В admin_web.py после существующих маршрутов

# ─── Terminal API ─────────────────────────────────────────────────────────────

@app.route('/api/terminal/execute', methods=['POST'])
@require_token
def terminal_execute():
    """Execute terminal command"""
    # ... implementation
    pass

@app.route('/api/terminal/suggestions', methods=['GET'])
@require_token
def terminal_suggestions():
    """Get command suggestions"""
    # ... implementation
    pass

@app.route('/api/terminal/history', methods=['GET'])
@require_token
def terminal_history():
    """Get command execution history"""
    # ... implementation (if storing history on backend)
    pass
```

## Тестирование

### cURL примеры:

```bash
# Execute command
curl -X POST http://localhost:8080/api/terminal/execute \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker ps"}'

# Get suggestions
curl -X GET "http://localhost:8080/api/terminal/suggestions?query=docker" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Альтернативные реализации

### Использование существующих агентов
Если у вас уже есть система выполнения команд через агентов (Matrix/Neo), можно использовать их:

```python
@app.route('/api/terminal/execute', methods=['POST'])
@require_token
def terminal_execute():
    """Execute command via agent"""
    from agent_tools_registry import execute_shell_command

    data = request.json
    command = data.get('command', '')

    # Use existing agent functionality
    result = execute_shell_command(command)

    return jsonify({
        'success': result.get('success', False),
        'output': result.get('output', ''),
        'exit_code': result.get('exit_code', -1),
        'executed_at': datetime.utcnow().isoformat() + 'Z'
    })
```

## Заметки для разработчика

1. **Приоритет безопасности**: Terminal API даёт прямой доступ к системе. Всегда используйте строгую валидацию.

2. **Логирование**: Все выполненные команды должны логироваться для аудита:
   ```python
   logger.info(f"Terminal command executed by {user}: {command}")
   ```

3. **Timeout**: Всегда устанавливайте timeout для предотвращения зависания.

4. **Error handling**: Обрабатывайте все возможные исключения.

5. **Database**: Рассмотрите сохранение истории команд в БД для синхронизации между устройствами.

## Совместимость

Эти эндпоинты совместимы с:
- `TerminalService` в Android приложении
- Существующей системой аутентификации
- Docker контейнеризацией

## Будущие улучшения

- [ ] WebSocket поддержка для real-time вывода
- [ ] Интерактивные команды (требующие ввода)
- [ ] Загрузка/выгрузка файлов
- [ ] Сессионность терминала
- [ ] Мультиплексирование (tmux/screen integration)
