# Migration Guide: Old ApiService → New BlackWhiteApiService

This guide helps you migrate from the old `ApiService` to the new `BlackWhiteApiService` with Dio.

## Quick Comparison

| Feature | Old ApiService | New BlackWhiteApiService |
|---------|----------------|--------------------------|
| HTTP Client | `http` package | `dio` package |
| Token Auth | Manual headers | Automatic interceptors |
| Token Refresh | Manual | Automatic on 401 |
| Retry Logic | None | Automatic with backoff |
| Type Safety | Partial | Full typed models |
| Error Handling | Manual parsing | Built-in |

## Installation

### 1. Update `pubspec.yaml`

The new packages are already added:
```yaml
dependencies:
  dio: ^5.4.0
  dio_smart_retry: ^6.0.0
```

Run:
```bash
flutter pub get
```

### 2. Import the New API

```dart
// OLD
import 'package:blackbugsai/services/api_service.dart';

// NEW
import 'package:blackbugsai/api/api.dart';
```

## Migration Examples

### Initialization

```dart
// OLD
final api = ApiService(
  baseUrl: 'https://example.com',
  adminToken: 'your_token',
);

// Or from saved config
final api = await ApiService.fromSavedConfig();

// NEW
final api = BlackWhiteApiService(
  baseUrl: 'https://example.com',
  accessToken: 'your_token',
);

// Or from saved credentials
final api = await BlackWhiteApiService.fromSavedCredentials();
```

### Login

```dart
// OLD - manual request
final response = await api._post('/api/auth/login', {
  'username': 'admin',
  'password': 'password',
});
if (response['ok'] == true) {
  final token = response['token'];
}

// NEW - typed request/response
final loginResponse = await api.auth.login(
  LoginRequest(
    username: 'admin',
    password: 'password',
  ),
);
if (loginResponse.ok) {
  final token = loginResponse.token;
}
```

### Get Agents

```dart
// OLD
try {
  final response = await api._get('/api/agents');
  final agents = (response['agents'] as List)
      .map((json) => Agent.fromJson(json))
      .toList();
} catch (e) {
  // Handle error
}

// NEW
final agentsResponse = await api.agents.getAgents();
if (agentsResponse.ok) {
  final agents = agentsResponse.agents; // Already typed!
} else {
  print('Error: ${agentsResponse.error}');
}
```

### Run Agent Task

```dart
// OLD
final response = await api._post('/api/agent/run', {
  'agent': 'smith',
  'task': 'Analyze code',
  'mode': 'auto',
});

// NEW
final runResponse = await api.agents.runAgent(
  AgentRunRequest(
    agent: 'smith',
    task: 'Analyze code',
    mode: 'auto',
  ),
);
```

### Get Logs

```dart
// OLD
final response = await api._get('/api/logs?n=100&level=ERROR');
final logs = response['logs'];

// NEW
final logsResponse = await api.logs.getLogs(
  n: 100,
  level: 'ERROR',
);
final logs = logsResponse.logs; // List<LogEntry>
```

### Get Tools

```dart
// OLD
final response = await api._get('/api/agent/tools_all');
final tools = response['tools'];

// NEW
final toolsResponse = await api.tools.getAllTools();
final tools = toolsResponse.tools; // List<Tool>
```

## Key Improvements

### 1. Automatic Token Refresh

The new client automatically handles token refresh:

```dart
// OLD - manual refresh
if (response.statusCode == 401) {
  // Manually refresh token
  await refreshToken();
  // Retry request
}

// NEW - automatic
// Just make the request, token refresh is automatic!
final response = await api.agents.getAgents();
```

### 2. Type Safety

```dart
// OLD - manual parsing
final agent = Agent(
  id: json['id'],
  name: json['name'],
  // ... manual field mapping
);

// NEW - automatic parsing
final agent = agentsResponse.agents.first; // Already typed!
print(agent.name); // IDE autocomplete works!
```

### 3. Error Handling

```dart
// OLD
try {
  final response = await api._get('/api/agents');
  if (response['ok'] != true) {
    throw Exception(response['error']);
  }
} catch (e) {
  // Handle error
}

// NEW
final response = await api.agents.getAgents();
if (!response.ok) {
  print('Error: ${response.error}'); // Error message included
  return;
}
// Use response.agents
```

### 4. Retry Logic

```dart
// OLD - no retry
final response = await api._get('/api/agents');
// If it fails due to network, it just fails

// NEW - automatic retry
final response = await api.agents.getAgents();
// Automatically retries up to 3 times with exponential backoff
```

## Common Patterns

### Pattern 1: Fetching Data for UI

```dart
// OLD
Future<void> loadAgents() async {
  try {
    setState(() => _isLoading = true);
    final response = await _api._get('/api/agents');
    if (response['ok'] == true) {
      setState(() {
        _agents = (response['agents'] as List)
            .map((json) => Agent.fromJson(json))
            .toList();
      });
    }
  } catch (e) {
    _showError(e.toString());
  } finally {
    setState(() => _isLoading = false);
  }
}

// NEW
Future<void> loadAgents() async {
  setState(() => _isLoading = true);
  try {
    final response = await _api.agents.getAgents();
    if (response.ok) {
      setState(() => _agents = response.agents);
    } else {
      _showError(response.error ?? 'Unknown error');
    }
  } catch (e) {
    _showError(e.toString());
  } finally {
    setState(() => _isLoading = false);
  }
}
```

### Pattern 2: Authenticated Requests

```dart
// OLD
Map<String, String> get _headers => {
  'Content-Type': 'application/json',
  'X-Admin-Token': adminToken,
};

// NEW
// Headers are automatically added by interceptors!
// Just make the request:
final response = await api.agents.getAgents();
```

### Pattern 3: Token Management

```dart
// OLD
final prefs = await SharedPreferences.getInstance();
await prefs.setString('admin_token', token);

// NEW
await api.client.setAccessToken(token);
// Automatically saved to SharedPreferences
```

## Step-by-Step Migration

### For Each Screen/Widget:

1. **Replace the import**
   ```dart
   // import 'package:blackbugsai/services/api_service.dart';
   import 'package:blackbugsai/api/api.dart';
   ```

2. **Update the API instance**
   ```dart
   // final api = ApiService(...);
   final api = BlackWhiteApiService(...);
   ```

3. **Replace API calls**
   - Use the new typed endpoints
   - Remove manual JSON parsing
   - Update error handling

4. **Test thoroughly**
   - Verify authentication works
   - Check all API calls
   - Test error scenarios

## Troubleshooting

### Issue: "Type 'dynamic' is not a subtype of..."

**Solution**: The new API returns typed models. Update your code:
```dart
// OLD
final agents = response['agents'] as List;

// NEW
final agents = response.agents; // Already List<Agent>
```

### Issue: Token not persisting

**Solution**: Use the new token management:
```dart
await api.client.setTokens(
  accessToken: token,
  refreshToken: token, // Or separate refresh token
);
```

### Issue: Need to access raw Dio client

**Solution**: Access via `api.client.dio`:
```dart
final dioClient = api.client.dio;
// Use for advanced scenarios
```

## Benefits Summary

✅ **Less Code** - Typed models eliminate manual parsing
✅ **More Reliable** - Automatic retries and token refresh
✅ **Better DX** - IDE autocomplete and type checking
✅ **Easier Testing** - Cleaner interfaces to mock
✅ **Future Proof** - Clean architecture for growth

## Need Help?

Check the following files:
- `lib/api/README.md` - Full API documentation
- `lib/api/example_usage.dart` - Usage examples
- `lib/api/api.dart` - API exports

## Keeping Both (Gradual Migration)

You can use both APIs during migration:

```dart
import 'package:blackbugsai/services/api_service.dart' as old;
import 'package:blackbugsai/api/api.dart';

// Use old API
final oldApi = old.ApiService(...);

// Use new API
final newApi = BlackWhiteApiService(...);

// Migrate screen by screen
```
