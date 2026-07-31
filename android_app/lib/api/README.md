# BlackWhiteAI Flutter API Client

A clean architecture Flutter API client for the BlackWhiteAI backend with Dio, token authentication, and automatic token refresh support.

## Features

- ✅ **Dio HTTP Client** - Modern, powerful HTTP client with interceptors
- ✅ **Token Authentication** - Bearer token and multiple auth header support
- ✅ **Automatic Token Refresh** - Seamless token refresh on 401 errors
- ✅ **Retry Logic** - Automatic retry with exponential backoff
- ✅ **Typed Models** - Fully typed request/response models
- ✅ **Clean Architecture** - Organized into client, models, and endpoints
- ✅ **Persistent Storage** - Token persistence with SharedPreferences

## Structure

```
lib/api/
├── client/
│   └── api_client.dart          # Base Dio client with interceptors
├── models/
│   ├── auth_models.dart         # Auth request/response models
│   ├── agent_models.dart        # Agent models
│   ├── tool_models.dart         # Tool models
│   ├── workflow_models.dart     # Workflow models
│   └── log_models.dart          # Log models
├── endpoints/
│   ├── auth_endpoints.dart      # Login, register, user info
│   ├── agent_endpoints.dart     # Agent listing and execution
│   ├── tool_endpoints.dart      # Tool management
│   ├── workflow_endpoints.dart  # Workflow execution
│   └── log_endpoints.dart       # System logs
├── black_white_api.dart         # Main service combining all endpoints
└── api.dart                     # Export file
```

## Installation

Add dependencies to `pubspec.yaml`:

```yaml
dependencies:
  dio: ^5.4.0
  dio_smart_retry: ^6.0.0
  shared_preferences: ^2.2.2
```

## Usage

### Initialize the API Client

```dart
import 'package:blackbugsai/api/api.dart';

// Create new instance
final api = BlackWhiteApiService(
  baseUrl: 'https://your-server.com',
  accessToken: 'optional_token',
);

// Or load from saved credentials
final api = await BlackWhiteApiService.fromSavedCredentials();
```

### Authentication

```dart
// Login
final loginResponse = await api.auth.login(
  LoginRequest(
    username: 'admin',
    password: 'password123',
  ),
);

if (loginResponse.ok) {
  print('Logged in as: ${loginResponse.username}');
  print('Token: ${loginResponse.token}');
}

// Register
final registerResponse = await api.auth.register(
  RegisterRequest(
    username: 'newuser',
    password: 'securepass',
  ),
);

// Get user info
final userInfo = await api.auth.getUserInfo();

// Logout
await api.auth.logout();
```

### Agents

```dart
// List all agents
final agentsResponse = await api.agents.getAgents();

for (final agent in agentsResponse.agents) {
  print('${agent.emoji} ${agent.name}: ${agent.description}');
}

// Run an agent task
final runResponse = await api.agents.runAgent(
  AgentRunRequest(
    agent: 'smith',
    task: 'Analyze this code for vulnerabilities',
    mode: 'auto',
  ),
);

if (runResponse.ok) {
  print('Result: ${runResponse.result}');
}
```

### Tools

```dart
// Get all tools
final toolsResponse = await api.tools.getAllTools();

for (final tool in toolsResponse.tools) {
  print('${tool.name}: ${tool.description}');
}

// Get specific agent tools
final neoTools = await api.tools.getNeoTools();
final matrixTools = await api.tools.getMatrixTools();

// Delete a tool
final deleteResponse = await api.tools.deleteTool(
  ToolDeleteRequest(toolName: 'my_custom_tool'),
);
```

### Workflows

```dart
// Execute a workflow
final workflowResponse = await api.workflows.executeWorkflow(
  WorkflowExecuteRequest(
    workflow: 'security_audit',
    params: {
      'target': 'https://example.com',
      'depth': 3,
    },
  ),
);

if (workflowResponse.ok) {
  print('Workflow result: ${workflowResponse.result}');
}
```

### Logs

```dart
// Get system logs
final logsResponse = await api.logs.getLogs(
  n: 100,
  level: 'ERROR',
);

for (final log in logsResponse.logs) {
  print('[${log.timestamp}] ${log.level}: ${log.text}');
}
```

## Advanced Usage

### Custom Requests

Access the underlying Dio client for custom requests:

```dart
final response = await api.client.get('/api/custom/endpoint');
```

### Token Management

```dart
// Check if authenticated
if (api.isAuthenticated) {
  print('Current token: ${api.accessToken}');
}

// Manually set tokens
await api.client.setTokens(
  accessToken: 'new_access_token',
  refreshToken: 'new_refresh_token',
);

// Clear tokens
await api.client.clearTokens();
```

### Error Handling

All endpoint methods return typed response objects with an `ok` field and optional `error` field:

```dart
final response = await api.agents.getAgents();

if (!response.ok) {
  print('Error: ${response.error}');
} else {
  // Use response.agents
}
```

## Supported Endpoints

### Auth
- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/register` - Register new user
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh access token (automatic)

### Agents
- `GET /api/agents` - List all agents
- `POST /api/agent/run` - Run agent task

### Tools
- `GET /api/agent/tools_all` - Get all tools
- `GET /api/neo/tools` - Get NEO agent tools
- `GET /api/matrix/tools` - Get MATRIX agent tools
- `POST /api/neo/tool/delete` - Delete a tool

### Workflows
- `POST /api/workflow/execute` - Execute a workflow

### Logs
- `GET /api/logs` - Get system logs (with filters)

## Authentication Headers

The client supports multiple authentication methods:
- `Authorization: Bearer <token>`
- `X-Admin-Token: <token>`
- `X-Api-Key: <token>`

All three headers are sent automatically when a token is set.

## Token Refresh

The client automatically handles 401 Unauthorized responses by:
1. Attempting to refresh the access token using the refresh token
2. Retrying the original request with the new token
3. Clearing tokens if refresh fails

## License

Part of the BlackWhiteAI project.
