"""
BlackBugsAI — Central Configuration
Brand: BlackBugsAI | Platform: AI Agent Marketplace
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / '.env')

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND = {
    'name':     'BlackBugsAI',
    'tagline':  'Autonomous AI Agent Platform',
    'version':  '1.0.0',
    'emoji':    '🖤🐛',
    'url':      'https://blackbugsai.com',
    'support':  '@blackbugsai_support',
}

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_ADMINS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM = {
    'provider': os.getenv('LLM_PROVIDER', 'openrouter'),
    'model':    os.getenv('LLM_MODEL', 'openai/gpt-4o-mini'),
    'api_key':  os.getenv('LLM_API_KEY', ''),
    'planner_model':  os.getenv('PLANNER_MODEL', 'openai/gpt-4o'),
    'executor_model': os.getenv('EXECUTOR_MODEL', 'openai/gpt-4o-mini'),
}

# ── Database ──────────────────────────────────────────────────────────────────
DB_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data/blackbugsai.db')

# ── Redis / Queue ─────────────────────────────────────────────────────────────
REDIS_URL    = os.getenv('REDIS_URL', '')   # пусто → SQLite queue fallback
QUEUE_WORKERS = int(os.getenv('QUEUE_WORKERS', 2))

# ── Proxy / Tor ────────────────────────────────────────────────────────────────
PROXY = {
    'enabled':  os.getenv('PROXY_ENABLED', '').lower() == 'true',
    'url':      os.getenv('PROXY_URL', ''),          # http://user:pass@host:port
    'tor':      os.getenv('TOR_ENABLED', '').lower() == 'true',
    'tor_port': int(os.getenv('TOR_PORT', 9050)),
    'rotate':   os.getenv('PROXY_ROTATE', '').lower() == 'true',  # менять каждый запрос
}

# ── Admin Web Panel ───────────────────────────────────────────────────────────
ADMIN_WEB_PORT  = int(os.getenv('ADMIN_WEB_PORT', 8080))
ADMIN_WEB_TOKEN = os.getenv('ADMIN_WEB_TOKEN', 'changeme')

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv('JWT_SECRET', 'change_me_in_production')
JWT_EXPIRE  = int(os.getenv('JWT_EXPIRE_HOURS', 24))

# ── Monetization / Billing ────────────────────────────────────────────────────
BILLING = {
    'enabled':  os.getenv('BILLING_ENABLED', 'false').lower() == 'true',
    'currency': os.getenv('BILLING_CURRENCY', 'USD'),
    'provider': os.getenv('BILLING_PROVIDER', 'telegram_stars'),  # telegram_stars | stripe | crypto
}

PLANS = {
    'free': {
        'name': '🆓 Free',
        'price': 0,
        'tasks_per_day':    10,
        'tools':            ['tts', 'image_gen', 'web_search', 'python_sandbox'],
        'file_mb':          10,
        'agent_rounds':     3,
        'priority':         0,
    },
    'pro': {
        'name': '⭐ Pro',
        'price': 9.99,
        'tasks_per_day':    100,
        'tools':            ['*'],   # все инструменты
        'file_mb':          500,
        'agent_rounds':     10,
        'priority':         1,
    },
    'business': {
        'name': '🚀 Business',
        'price': 49.99,
        'tasks_per_day':    -1,      # безлимит
        'tools':            ['*'],
        'file_mb':          -1,
        'agent_rounds':     20,
        'priority':         2,
        'white_label':      True,
        'api_access':       True,
    },
    'enterprise': {
        'name': '🏢 Enterprise',
        'price': 0,    # по договору
        'tasks_per_day':    -1,
        'tools':            ['*'],
        'file_mb':          -1,
        'agent_rounds':     -1,
        'priority':         3,
        'dedicated_workers': True,
        'custom_tools':     True,
        'sla':              True,
    },
}

# ── Tool sandbox security levels ──────────────────────────────────────────────
SANDBOX = {
    'timeout_default': 30,
    'timeout_max':     300,
    'docker_enabled':  os.getenv('DOCKER_SANDBOX', 'false').lower() == 'true',
    'docker_image':    'python:3.11-slim',
    'allowed_imports': ['os','sys','json','re','math','datetime','pathlib',
                        'requests','httpx','bs4','PIL','numpy','pandas'],
    'blocked_imports': ['subprocess','socket','ctypes','importlib'],
}

# ── Paths ─────────────────────────────────────────────────────────────────────
PATHS = {
    'data':      BASE_DIR / 'data',
    'artifacts': BASE_DIR / 'data' / 'artifacts',
    'logs':      BASE_DIR / 'data' / 'logs',
    'uploads':   BASE_DIR / 'data' / 'uploads',
    'projects':  BASE_DIR / 'data' / 'projects',
    'plugins':   BASE_DIR / 'plugins',
}

for path in PATHS.values():
    path.mkdir(parents=True, exist_ok=True)
