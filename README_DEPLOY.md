# BlackBugsAI — Руководство по деплою и исправлениям

## ✅ Что было исправлено

### admin_web.py
- Добавлен эндпоинт `/api/agents` — возвращает список всех 7 агентов
- Расширен `/api/agent/run` — теперь поддерживает **все агенты**:
  - `smith` → agents/smith.py + fallback agent_tools_registry
  - `neo` → agent_neo.py
  - `matrix` → agent_matrix.py  
  - `anderson` → agents/anderson.py (НОВЫЙ)
  - `pythia` → agents/pythia.py (НОВЫЙ)
  - `tanker` → agents/tanker.py (НОВЫЙ)
  - `operator` → agents/operator.py (НОВЫЙ)
- Универсальный `_result_to_json()` конвертер для AgentResult

### admin_panel.html
- Добавлены страницы в сайдбар: MR.ANDERSON, PYTHIA, TANKER, OPERATOR
- Добавлены HTML-страницы для каждого нового агента
- Добавлены JS-функции: `runGenericAgent()`, `setAgentTask()`, `clearAgentOut()`
- Расширена таблица nav() dispatch

### Android App (Flutter)
- `settings_screen.dart` — убран дублированный `dispose()`, исправлены ссылки на `prefs`
- `api_service.dart` — убран дублированный `runDockerCommand()`, добавлен `/api/agents`
- `models.dart` — добавлено поле `id` в `AgentInfo`
- `neon_theme.dart` — переход на `google_fonts` (не нужны локальные файлы шрифтов)
- `pubspec.yaml` — заменён на `google_fonts: ^6.1.0`, убраны несуществующие assets

### GitHub Actions
- `.github/workflows/build-apk.yml` — чистый workflow, убраны конфликты

---

## 🚀 Деплой (Docker)

### Первый запуск
```bash
# 1. Заполни .env
cp .env.example .env
nano .env

# ОБЯЗАТЕЛЬНО:
# TELEGRAM_BOT_TOKEN=...
# ADMIN_WEB_TOKEN=твой_секретный_токен  (минимум 20 символов)
# LLM_API_KEY=...  или GROQ_API_KEY=... или DEEPSEEK_API_KEY=...

# 2. Запусти
docker compose up -d

# 3. Проверь
docker compose ps
curl http://localhost:8080/ping
```

### Admin Panel
```
URL:   http://<IP>:8080
Токен: значение ADMIN_WEB_TOKEN из .env
```

### Конфликт Fish + Admin Panel (уже исправлен)
В текущем `docker-compose.yml`:
- `FISH_TUNNEL_DISABLED=true` — fish НЕ запускает tunnel
- `TUNNEL_TARGET_PORT=80` — tunnel идёт через nginx
- Nginx проксирует `/fish/*` → port 5100
- Только admin_web управляет tunnel через `/api/tunnel/start`

### Smoke-check после обновления Docker-конфигов
```bash
docker compose -f docker-compose.yml config
```

### Rollback (если нужно быстро откатить деплой)
```bash
git restore Dockerfile docker-compose.yml
docker compose down
docker compose up -d --build
```

---

## 📱 Сборка APK

### Способ 1: GitHub Actions (рекомендуется)
1. Залей проект на GitHub
2. Actions → **Build BlackBugsAI APK** → **Run workflow**
3. После сборки: Actions → последний запуск → Artifacts → `BlackBugsAI-Release-APKs`

### Способ 2: Создать Release с APK
1. Actions → **Build BlackBugsAI APK** → Run workflow
2. В поле `release_tag` введи: `v1.1.0`
3. APK автоматически появятся в Releases

### Подключение приложения к серверу
1. Установи APK (arm64 для большинства телефонов)
2. Открой → введи URL: `http://<IP>:8080`
3. Введи токен: значение `ADMIN_WEB_TOKEN` из `.env`

---

## 🤖 Агенты

| Агент | Доступ | Назначение |
|-------|--------|-----------|
| 🕵️ SMITH | god/adm | Autofix pipeline, security audit |
| 🧠 NEO | god/adm/vip | Self-tool gen, OSINT, ZIP artifacts |
| 🟥 MATRIX | god/adm/vip | Coder + OSINT + Security Analyst |
| 🔍 ANDERSON | все роли | Анализ уязвимостей, code fix, review |
| 💻 PYTHIA | все роли | Quick coder, project, sandbox |
| 🛡 TANKER | все роли | Red team, multitool, pipelines |
| 🎯 OPERATOR | god/owner | Мета-агент, оркестрирует всех |

### Как запустить агента через API
```bash
curl -X POST http://localhost:8080/api/agent/run \
  -H "X-Admin-Token: твой_токен" \
  -H "Content-Type: application/json" \
  -d '{"agent": "pythia", "task": "Напиши Flask API с JWT", "mode": "auto"}'
```

---

## 🔑 .env минимум для работы

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
ADMIN_WEB_TOKEN=my_super_secret_admin_token_32chars
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
TTS_PROVIDER=edge
TTS_VOICE=ru-RU-DmitryNeural
FISH_TUNNEL_DISABLED=true
TUNNEL_TARGET_PORT=80
```
