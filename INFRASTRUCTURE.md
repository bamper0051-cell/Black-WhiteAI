# 🏗️ BlackBugsAI — Monorepo Project Structure

## 📋 Overview

This is a **monorepo** architecture for the BlackBugsAI multi-agent system, designed for scalability, maintainability, and clean separation of concerns.

## 🎯 Design Principles

1. **Service Isolation**: Each service is independently deployable
2. **Shared Libraries**: Common code is centralized in `libs/`
3. **Clear Boundaries**: Backend, frontend, and infrastructure are separated
4. **Docker Native**: All services run in containers with proper networking
5. **Environment-based Configuration**: All secrets and configs via `.env`

## 📁 Proposed Directory Structure

```
BlackBugsAI/                          # Root monorepo
├── .env.example                      # Environment configuration template
├── docker-compose.yml                # Main orchestration file
├── nginx.conf                        # Reverse proxy configuration
├── README.md                         # Main documentation
├── INFRASTRUCTURE.md                 # This file
│
├── services/                         # Microservices
│   ├── backend/                      # FastAPI Backend (Agent Core)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Configuration loader
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── agents.py             # Agent endpoints
│   │   │   ├── tasks.py              # Task queue endpoints
│   │   │   ├── tools.py              # Tool management endpoints
│   │   │   └── health.py             # Health check endpoints
│   │   ├── core/                     # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── agent_base.py         # BaseAgent implementation
│   │   │   ├── agent_registry.py     # Agent registration
│   │   │   ├── tool_registry.py      # Tool registration
│   │   │   └── task_queue.py         # Task queue implementation
│   │   ├── agents/                   # Agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── neo_agent.py
│   │   │   ├── matrix_agent.py
│   │   │   ├── coder_agent.py
│   │   │   └── brain_agent.py
│   │   ├── models/                   # Database models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── agent.py
│   │   │   ├── task.py
│   │   │   └── memory.py             # Skill & failure memory
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── database.py
│   │       ├── redis_client.py
│   │       └── logger.py
│   │
│   ├── telegram-bot/                 # Telegram Bot Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── bot_main.py               # Main bot entry point
│   │   ├── handlers/                 # Message handlers
│   │   │   ├── __init__.py
│   │   │   ├── commands.py
│   │   │   ├── callbacks.py
│   │   │   └── messages.py
│   │   ├── keyboards.py              # Bot keyboards/UI
│   │   └── client.py                 # Backend API client
│   │
│   ├── admin-web/                    # Admin Panel (current admin_web.py)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── admin_web.py              # Main web server
│   │   ├── static/                   # Static assets
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── images/
│   │   └── templates/                # HTML templates
│   │       ├── admin_panel_v4.html
│   │       └── admin_panel_login.html
│   │
│   └── fish-module/                  # Fish Web Module (isolated)
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── fish_web.py               # Flask server
│       ├── fish_utils.py
│       └── fish_db.py
│
├── libs/                             # Shared libraries
│   ├── __init__.py
│   ├── llm/                          # LLM abstraction
│   │   ├── __init__.py
│   │   ├── providers.py              # Provider implementations
│   │   ├── router.py                 # LLM router
│   │   └── checker.py                # LLM health checker
│   ├── auth/                         # Authentication
│   │   ├── __init__.py
│   │   ├── jwt.py                    # JWT handling
│   │   └── user_auth.py              # User authentication
│   ├── storage/                      # Storage abstractions
│   │   ├── __init__.py
│   │   ├── postgres.py               # PostgreSQL client
│   │   └── redis.py                  # Redis client
│   └── common/                       # Common utilities
│       ├── __init__.py
│       ├── logging.py
│       ├── exceptions.py
│       └── constants.py
│
├── migrations/                       # Database migrations
│   ├── postgres/                     # PostgreSQL migrations
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_memory_tables.sql
│   │   └── 003_add_user_separation.sql
│   └── redis/                        # Redis setup scripts
│       └── init.lua
│
├── scripts/                          # Deployment & utility scripts
│   ├── deploy_gcp.sh                 # GCP deployment
│   ├── init.sh                       # Initial setup
│   ├── backup.py                     # Backup script
│   └── migrate.sh                    # Run migrations
│
├── tests/                            # Test suite
│   ├── unit/                         # Unit tests
│   │   ├── test_agents.py
│   │   ├── test_tools.py
│   │   └── test_memory.py
│   ├── integration/                  # Integration tests
│   │   ├── test_api.py
│   │   └── test_workflows.py
│   └── e2e/                          # End-to-end tests
│       └── test_telegram_bot.py
│
├── docs/                             # Documentation
│   ├── API.md                        # API documentation
│   ├── AGENTS.md                     # Agent documentation
│   ├── DEPLOYMENT.md                 # Deployment guide
│   └── ARCHITECTURE.md               # Architecture overview
│
└── data/                             # Runtime data (gitignored)
    ├── postgres/                     # PostgreSQL data
    ├── redis/                        # Redis persistence
    ├── logs/                         # Application logs
    ├── uploads/                      # User uploads
    └── workspaces/                   # Agent workspaces
        ├── neo/
        └── matrix/
```

## 🔄 Migration Strategy

### Phase 1: Reorganize Existing Code (Week 1)
1. Create new directory structure
2. Move existing Python files to appropriate services
3. Extract shared code to `libs/`
4. Update imports

### Phase 2: Service Isolation (Week 2)
1. Create separate Dockerfiles for each service
2. Update docker-compose.yml with new services
3. Implement inter-service communication via HTTP/Redis
4. Test service independence

### Phase 3: Database Migration (Week 3)
1. Design PostgreSQL schema
2. Migrate SQLite data to PostgreSQL
3. Implement Redis for task queue and caching
4. Add memory tables for skill/failure tracking

### Phase 4: Testing & Documentation (Week 4)
1. Write unit tests for core components
2. Integration tests for API endpoints
3. E2E tests for critical workflows
4. Update documentation

## 🌐 Network Architecture

```
Internet/Tunnel
       ↓
    Nginx:80
       ↓
   ┌───┴────┬──────────┬──────────┐
   ↓        ↓          ↓          ↓
Backend  Fish    Admin-Web    n8n
:8080    :5100                :5678
   ↓        ↓          ↓          ↓
   └────────┴──────────┴──────────┘
              ↓        ↓
          PostgreSQL  Redis
           :5432      :6379
```

## 🔐 Security Considerations

1. **Network Isolation**: Services communicate via internal Docker network
2. **No Direct Exposure**: Only Nginx is exposed to the internet
3. **Environment Variables**: All secrets are in `.env` (never committed)
4. **Health Checks**: All services have health checks for auto-restart
5. **User Separation**: Multi-tenant support with `user_id` in all operations

## 📊 Data Flow

### Agent Execution Flow
```
User (Telegram) → telegram-bot service
                      ↓
                  Backend API (/api/agents/execute)
                      ↓
                  Task Queue (Redis)
                      ↓
                  Agent Worker (BaseAgent)
                      ↓
                  Skill Memory Check (PostgreSQL)
                      ↓
                  Tool Execution
                      ↓
                  Result + Memory Update
                      ↓
                  Response to User
```

### Memory System Flow
```
Tool Success → Skill Memory (PostgreSQL)
               ├─ user_id
               ├─ tool_name
               ├─ input_params
               ├─ output_result
               └─ timestamp

Tool Failure → Failure Memory (PostgreSQL)
               ├─ user_id
               ├─ tool_name
               ├─ error_message
               ├─ input_params
               └─ timestamp
```

## 🚀 Deployment

### Local Development
```bash
# 1. Setup environment
cp .env.example .env
nano .env  # Fill in your values

# 2. Start infrastructure
docker compose up -d postgres redis

# 3. Run migrations
./scripts/migrate.sh

# 4. Start all services
docker compose up -d

# 5. Check health
curl http://localhost/health
```

### Production (GCP)
```bash
# Deploy to GCP with automated script
./scripts/deploy_gcp.sh
```

## 🧪 Testing

```bash
# Run all tests
docker compose exec backend pytest

# Run specific test suite
docker compose exec backend pytest tests/unit/
docker compose exec backend pytest tests/integration/

# Check coverage
docker compose exec backend pytest --cov=core --cov-report=html
```

## 📈 Monitoring

- **Logs**: `docker compose logs -f [service-name]`
- **Health**: `curl http://localhost/health`
- **Metrics**: PostgreSQL queries, Redis stats, Agent execution times
- **Admin Panel**: `http://localhost/admin/`

## 🔧 Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :80 -i :5432 -i :6379

# Stop conflicting services
docker compose down

# Restart with clean state
docker compose up -d --force-recreate
```

### Database Issues
```bash
# Reset PostgreSQL
docker compose down -v
docker compose up -d postgres
./scripts/migrate.sh
```

### Service Restart
```bash
# Restart specific service
docker compose restart backend

# View logs
docker compose logs -f backend
```

## 📚 Additional Resources

- [API Documentation](./docs/API.md)
- [Agent Development Guide](./docs/AGENTS.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Architecture Overview](./docs/ARCHITECTURE.md)

## 🤝 Contributing

1. Create feature branch from `main`
2. Make changes in appropriate service directory
3. Add tests for new functionality
4. Update documentation
5. Submit PR with detailed description

## 📝 License

See [LICENSE](./LICENSE) file for details.
