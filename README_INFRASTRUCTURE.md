# 🤖 BlackBugsAI — Multi-Agent Infrastructure v4.0

> Enterprise-grade multi-agent AI system with PostgreSQL, Redis, FastAPI, n8n workflow automation, and Telegram integration.

---

## 🎯 What's New in v4.0

### Infrastructure Improvements
- ✅ **PostgreSQL** for persistent data storage
- ✅ **Redis** for state management and task queues
- ✅ **n8n Integration** for workflow automation
- ✅ **Enhanced Nginx** with proper routing (`/api/`, `/admin/`, `/n8n/`, `/fish/`)
- ✅ **Service Isolation** - Backend, Telegram Bot, and Admin Web as separate services
- ✅ **Health Checks** - Auto-restart on failures
- ✅ **Docker Networks** - Internal communication without port exposure

### Agent Enhancements
- ✅ **Skill Memory** - Agents remember successful tool executions
- ✅ **Failure Memory** - Agents avoid repeating mistakes
- ✅ **Multi-User Separation** - All operations scoped by `user_id`
- ✅ **Enhanced BaseAgent** - New architecture with memory support

### Developer Experience
- ✅ **Monorepo Structure** - Clear separation of concerns
- ✅ **Environment-based Config** - All secrets in `.env`
- ✅ **Migration Scripts** - Easy database schema management
- ✅ **Comprehensive Documentation** - Architecture, API, deployment guides

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet / Tunnel                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Nginx :80     │
                    │  (Reverse      │
                    │   Proxy)       │
                    └───┬───┬───┬───┬┘
                        │   │   │   │
        ┌───────────────┼───┼───┼───┼──────────────┐
        │               │   │   │   │              │
    ┌───▼────┐     ┌───▼──┐│  │┌──▼────┐   ┌─────▼─────┐
    │Backend │     │Fish  ││  ││Admin  │   │    n8n    │
    │:8080   │     │:5100 ││  ││Web    │   │   :5678   │
    │        │     │      ││  ││       │   │           │
    │FastAPI │     │Flask ││  ││Aiohttp│   │Workflows  │
    └───┬────┘     └──────┘│  │└───────┘   └─────┬─────┘
        │                  │  │                   │
        └──────────────────┴──┴───────────────────┘
                           │  │
                    ┌──────▼──▼──────┐
                    │  PostgreSQL    │
                    │    :5432       │
                    └────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │    :6379    │
                    └─────────────┘
```

### Service Responsibilities

| Service | Port | Purpose |
|---------|------|---------|
| **Nginx** | 80 | Reverse proxy, SSL termination, routing |
| **Backend** | 8080 | FastAPI agent core, API endpoints |
| **Telegram Bot** | - | Isolated Telegram bot service |
| **Admin Web** | 8080 | Admin panel UI (proxied via Nginx) |
| **Fish Module** | 5100 | Isolated web module |
| **n8n** | 5678 | Workflow automation platform |
| **PostgreSQL** | 5432 | Persistent database |
| **Redis** | 6379 | Cache, queue, session store |

---

## ⚡ Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/bamper0051-cell/Black-WhiteAI.git
cd Black-WhiteAI

# 2. Configure environment
cp .env.example .env
nano .env  # Fill in your API keys and secrets

# 3. Start infrastructure
docker compose up -d

# 4. Check health
curl http://localhost/health

# 5. Open Admin Panel
open http://localhost/admin/
```

### First Time Setup

```bash
# Run database migrations
docker compose exec backend python scripts/migrate.py

# Create admin user (optional)
docker compose exec backend python scripts/create_admin.py

# View logs
docker compose logs -f backend
```

---

## 🔐 Configuration

### Required Environment Variables

Create a `.env` file with at least these values:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Admin Panel
ADMIN_WEB_TOKEN=strong_random_secret

# Database
POSTGRES_PASSWORD=secure_password_here
REDIS_PASSWORD=another_secure_password

# n8n
N8N_BASIC_AUTH_PASSWORD=n8n_password

# At least one LLM provider
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
GROQ_API_KEY=gsk_...
```

See [.env.example](.env.example) for all available options.

---

## 📡 API Routes

### Backend API (FastAPI)

| Route | Method | Description |
|-------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/api/agents/list` | GET | List available agents |
| `/api/agents/execute` | POST | Execute agent task |
| `/api/tools/list` | GET | List available tools |
| `/api/tools/execute` | POST | Execute tool |
| `/api/tasks/queue` | POST | Add task to queue |
| `/api/tasks/status/{id}` | GET | Get task status |
| `/api/memory/skills/{user_id}` | GET | Get user skill memory |
| `/api/memory/failures/{user_id}` | GET | Get user failure memory |

### Admin Panel Routes

| Route | Description |
|-------|-------------|
| `/admin/` | Admin dashboard |
| `/admin/agents` | Agent management |
| `/admin/tools` | Tool management |
| `/admin/users` | User management |
| `/admin/logs` | System logs |

### n8n Workflow Automation

| Route | Description |
|-------|-------------|
| `/n8n/` | n8n UI |
| `/n8n/webhook/*` | Webhook endpoints |

---

## 🧠 Agent Memory System

### Skill Memory

Agents automatically remember successful tool executions:

```python
from core.base_agent import BaseAgent, AgentContext

agent = ExampleAgent()
context = AgentContext(user_id="user_123", session_id="session_456")

# Execute tool - success is automatically remembered
result = agent.execute_tool(context, "web_scraper", url="https://example.com")

# Later, agent can reference similar successful executions
similar = agent.memory.get_similar_skills(context, "web_scraper", limit=5)
```

### Failure Memory

Agents avoid repeating mistakes:

```python
# If a tool fails 3+ times in 24 hours, agent will warn
recent_failures = agent.memory.get_recent_failures(context, "tool_name", hours=24)
if len(recent_failures) >= 3:
    print("This tool has been failing frequently!")
```

### Multi-User Separation

All memory is scoped by `user_id`:

```python
# User A's memories
context_a = AgentContext(user_id="alice", session_id="...")
agent.execute_tool(context_a, "tool", param="value")

# User B's memories (completely separate)
context_b = AgentContext(user_id="bob", session_id="...")
agent.execute_tool(context_b, "tool", param="value")
```

---

## 🚀 Deployment

### Local Development

```bash
# Start all services
docker compose up -d

# Restart specific service
docker compose restart backend

# View logs
docker compose logs -f backend

# Stop all services
docker compose down

# Clean restart (removes volumes)
docker compose down -v
docker compose up -d
```

### Production (GCP)

```bash
# Deploy to Google Cloud Platform
./scripts/deploy_gcp.sh

# The script will:
# 1. Create GCP Compute Engine instance
# 2. Install Docker and Docker Compose
# 3. Clone repository
# 4. Setup environment
# 5. Start all services
# 6. Configure Cloudflare tunnel (if enabled)
```

### Environment-Specific Configs

```bash
# Development
docker compose -f docker-compose.yml up -d

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With custom env file
docker compose --env-file .env.production up -d
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
docker compose exec backend pytest

# Unit tests only
docker compose exec backend pytest tests/unit/

# Integration tests
docker compose exec backend pytest tests/integration/

# With coverage
docker compose exec backend pytest --cov=core --cov-report=html
```

### Manual Testing

```bash
# Test API endpoint
curl -X POST http://localhost/api/agents/execute \
  -H "Content-Type: application/json" \
  -d '{"agent": "neo", "task": "Hello world", "user_id": "test_user"}'

# Test health check
curl http://localhost/health

# Test n8n
curl http://localhost/n8n/healthz
```

---

## 📊 Monitoring & Debugging

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f redis

# Last 100 lines
docker compose logs --tail=100 backend
```

### Database Access

```bash
# PostgreSQL
docker compose exec postgres psql -U blackbugs -d blackbugsai

# Redis
docker compose exec redis redis-cli -a REDIS_PASSWORD
```

### Service Health

```bash
# Check all containers
docker compose ps

# Check specific service health
docker compose exec backend curl localhost:8080/health

# Check resource usage
docker stats
```

---

## 🐛 Troubleshooting

### Port Conflicts

```bash
# Find what's using port 80
lsof -i :80
sudo netstat -tulpn | grep :80

# Change port in .env
HTTP_PORT=8000
docker compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose logs postgres

# Reset database
docker compose down -v postgres
docker compose up -d postgres

# Wait for health check
docker compose ps postgres
```

### Nginx Routing Issues

```bash
# Check nginx config syntax
docker compose exec nginx nginx -t

# Reload nginx
docker compose exec nginx nginx -s reload

# View nginx logs
docker compose logs nginx
```

### Agent Memory Not Working

```bash
# Check if tables exist
docker compose exec postgres psql -U blackbugs -d blackbugsai \
  -c "SELECT * FROM skill_memory LIMIT 1;"

# Run migrations
docker compose exec backend python scripts/migrate.py

# Check Redis connection
docker compose exec redis redis-cli -a REDIS_PASSWORD ping
```

---

## 📚 Documentation

- [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) - Monorepo structure and migration guide
- [API Documentation](./docs/API.md) - Complete API reference (coming soon)
- [Agent Development](./docs/AGENTS.md) - Creating custom agents (coming soon)
- [Deployment Guide](./docs/DEPLOYMENT.md) - Production deployment (coming soon)

---

## 🔧 Development

### Project Structure

```
BlackBugsAI/
├── docker-compose.yml          # Main orchestration
├── nginx.conf                  # Reverse proxy config
├── .env.example                # Environment template
├── INFRASTRUCTURE.md           # Architecture docs
│
├── core/                       # Core libraries
│   └── base_agent.py           # Enhanced BaseAgent
│
├── services/                   # Microservices (planned)
│   ├── backend/
│   ├── telegram-bot/
│   └── admin-web/
│
└── scripts/                    # Utility scripts
    ├── deploy_gcp.sh
    ├── migrate.py
    └── backup.py
```

### Adding a New Agent

```python
from core.base_agent import BaseAgent, AgentContext, AgentResult

class MyAgent(BaseAgent):
    NAME = "my_agent"
    EMOJI = "🔥"
    DESCRIPTION = "My custom agent"

    def execute(self, context: AgentContext, task: str, **kwargs) -> AgentResult:
        result = AgentResult()

        try:
            # Your logic here
            result.ok = True
            result.answer = "Task completed!"

        except Exception as e:
            result.ok = False
            result.error = str(e)

        return result
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- n8n for workflow automation
- PostgreSQL and Redis teams
- All contributors and users

---

## 📞 Support

- GitHub Issues: [Report a bug](https://github.com/bamper0051-cell/Black-WhiteAI/issues)
- Telegram: Contact via bot
- Email: (coming soon)

---

**Built with ❤️ by the BlackBugsAI Team**
