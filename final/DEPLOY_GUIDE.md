# BlackBugsAI v5 — Deploy Guide

## 🚀 Быстрый старт (GCP / любой VPS)

```bash
# 1. Клонируй / распакуй проект
cd /opt && unzip BlackBugsAI_v5_FINAL.zip && mv final blackbugsai
cd /opt/blackbugsai

# 2. Настрой .env
cp .env.example .env
nano .env   # обязательно: BOT_TOKEN, ADMIN_WEB_TOKEN, API ключи

# 3. Запусти одной командой (устанавливает Docker если нет)
bash deploy_gcp.sh
```

## 🌐 Глобальный доступ (панель из любой точки мира)

### Вариант А — Cloudflare Tunnel (встроен в docker-compose)
```bash
docker compose up -d
# URL появится в логах:
docker compose logs cloudflare | grep trycloudflare
```

### Вариант Б — Открыть порт в GCP Firewall
```bash
gcloud compute firewall-rules create allow-8080 \
  --allow tcp:8080 --source-ranges 0.0.0.0/0
# Доступ: http://EXTERNAL_IP:8080/panel
```

## 🔑 Подключение к Admin Panel

Открой `admin_panel.html` в браузере или перейди на `http://SERVER:8080/panel`

| Поле | Значение |
|------|---------|
| Server URL | `http://IP:8080` или `https://xxx.trycloudflare.com` |
| Admin Token | значение `ADMIN_WEB_TOKEN` из `.env` |

## ✅ Что исправлено в v5 FINAL

### agent_matrix.py
- `SANDBOX_TIMEOUT = 600` (было 60)
- `same_error_count` инициализируется ДО цикла (был `NameError` на попытке 2)
- `sandbox_timeout` растёт до 340с (было max 90с — pip install падал)
- Добавлены `get_stats()`, `delete_tool()`, `stop_all_processes()`

### agent_neo.py
- `sandbox_timeout` = 60+attempt×40 (было 20+attempt×10)
- Максимум до 340с для тяжёлых pip install

### admin_web.py — новые SSE роуты
| Роут | Описание |
|------|----------|
| `POST /api/matrix/tools/generate` | SSE стриминг генерации через LLM |
| `POST /api/matrix/tools/github` | SSE установка с GitHub |
| `POST /api/matrix/run/stream` | SSE выполнение задачи Matrix |
| `GET /api/matrix/stats` | Статистика инструментов |
| `POST /api/matrix/warmup` | Инит встроенных инструментов |
| `GET/PUT /api/matrix/tools/<n>/code` | Просмотр и редактирование кода |
| `POST /api/matrix/tools/test` | Тест инструмента с inputs |
| `DELETE /api/matrix/tools/<n>` | Удаление |
| `POST /api/matrix/stop-all` | Стоп sandbox процессов |
| `GET /api/matrix/pentest-tools` | Статус pentest инструментов |

### admin_panel.html — полностью новая
- Подключение по URL+Token — работает из любой точки мира
- Live SSE прогресс-бар при генерации инструментов
- Редактор кода с тестом и удалением
- 9 готовых примеров промтов для Tool Generator
- Shell terminal с историей команд (↑/↓)
- Вкладка Global Access с инструкцией GCP + Cloudflare

## 🐳 docker-compose.yml

```yaml
services:
  bot:          # основной бот + admin panel :8080
  cloudflare:   # tunnel → публичный HTTPS URL без белого IP
```

## 📋 Полезные команды

```bash
docker compose logs -f bot           # логи в реальном времени
docker compose logs cloudflare       # Cloudflare tunnel URL
docker compose restart bot           # горячий перезапуск
docker compose down && docker compose up -d  # полный перезапуск
docker compose exec bot python3 -c "from agent_matrix import warmup; warmup()"
```
