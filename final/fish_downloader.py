import os
import json
import shutil
import subprocess
import requests
import time
import re
from datetime import datetime
from urllib.parse import urlparse
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False
from fish_config import PAGES_DIR, DOWNLOADS_DIR, USE_SELENIUM, BASE_DIR
import fish_utils as utils

PAGES_JSON = os.path.join(PAGES_DIR, "pages.json")
ACTIVE_FILE = os.path.join(BASE_DIR, 'data', 'active.txt')

if not os.path.exists(PAGES_JSON):
    with open(PAGES_JSON, "w") as f:
        json.dump({}, f)

# Домены которые требуют JavaScript для рендеринга — requests даст пустышку.
# Для них сообщаем заранее а не зависаем молча.
JS_HEAVY_DOMAINS = {
    'vk.com', 'vk.ru',
    'facebook.com', 'fb.com', 'instagram.com',
    'twitter.com', 'x.com',
    'tiktok.com',
    'linkedin.com',
    'gmail.com', 'mail.google.com',
    'youtube.com',
    'netflix.com',
    'discord.com', 'discord.gg',
    'notion.so',
    'figma.com',
    'react.dev', 'nextjs.org',
}

# Признаки что сервер вернул JS-скелет без реального контента
_JS_MARKERS = [
    'window.__INITIAL_STATE__',
    'window.__NEXT_DATA__',
    'window.__NUXT__',
    '__REACT_APP__',
    '<div id="app"></div>',
    '<div id="root"></div>',
    'application/javascript',
    'ReactDOM.render',
    'vue.config.js',
]


class PageDownloader:

    # Заголовки реального браузера Chrome на Windows — VK и подобные
    # проверяют их и блокируют ботов с минимальным User-Agent.
    _BROWSER_HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

    @staticmethod
    def _is_js_heavy(url):
        """Проверяем по домену — нужен ли JavaScript для рендеринга."""
        try:
            domain = urlparse(url).netloc.lower().lstrip('www.')
            # Проверяем и сам домен, и его родительский (vk.com → vk.com)
            return domain in JS_HEAVY_DOMAINS or \
                   '.'.join(domain.split('.')[-2:]) in JS_HEAVY_DOMAINS
        except Exception:
            return False

    @staticmethod
    def _detect_js_skeleton(html):
        """Проверяем HTML на признаки пустого JS-скелета."""
        if not html:
            return True
        # Если контент меньше 5КБ — скорее всего скелет
        if len(html) < 5000:
            return True
        for marker in _JS_MARKERS:
            if marker in html:
                return True
        return False

    @staticmethod
    def download_page(url, on_status=None):
        """
        Скачивает HTML страницы.

        on_status — callback(str) для отправки промежуточных статусов пользователю.
        Это важно для медленных сайтов — иначе пользователь видит тишину 30 секунд.

        Порядок попыток:
          1. Если домен заведомо JS-heavy (VK, Facebook и т.д.) — сразу предупреждаем
             и предлагаем wget-зеркало вместо одностраничного requests.
          2. Selenium если включён в конфиге.
          3. requests.Session с реальными браузерными заголовками и follow_redirects.
          4. Проверяем результат на JS-скелет — предупреждаем если страница пустая.
        """
        def _status(msg):
            if on_status:
                on_status(msg)
            print(msg, flush=True)

        _status("🔍 Анализирую URL...")

        # Предупреждение для JS-heavy сайтов — до любой попытки скачивания
        if PageDownloader._is_js_heavy(url):
            _status(
                "⚠️ {} требует JavaScript для рендеринга.\n"
                "requests получит пустой скелет без контента.\n"
                "Пробую всё равно, но результат может быть неполным.\n"
                "💡 Для полного клона используй кнопку «🌐 Весь сайт» (wget).".format(
                    urlparse(url).netloc)
            )

        # Попытка через Selenium (рендерит JS)
        if USE_SELENIUM:
            _status("🤖 Запускаю Selenium...")
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.support.ui import WebDriverWait
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument(
                    '--user-agent=' + PageDownloader._BROWSER_HEADERS['User-Agent'])
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(30)
                driver.get(url)
                # Ждём пока JS отработает
                time.sleep(3)
                html = driver.page_source
                driver.quit()
                _status("✅ Selenium: страница получена ({} KB)".format(len(html) // 1024))
                return html
            except Exception as e:
                _status("⚠️ Selenium недоступен: {}. Переключаюсь на requests.".format(e))

        # Попытка через requests.Session
        _status("📡 Подключаюсь к серверу...")
        try:
            session = requests.Session()
            session.headers.update(PageDownloader._BROWSER_HEADERS)

            # Первый запрос — получаем cookies (как настоящий браузер)
            _status("🍪 Получаю cookies...")
            resp = session.get(
                url,
                timeout=20,
                allow_redirects=True,
                verify=True,
            )

            _status("📄 Читаю контент ({} KB)...".format(len(resp.content) // 1024))

            html = resp.text

            # Проверяем что получили реальный контент, а не JS-скелет
            if PageDownloader._detect_js_skeleton(html):
                _status(
                    "⚠️ Сервер вернул JS-скелет без контента ({} KB).\n"
                    "Страница требует выполнения JavaScript в браузере.\n"
                    "Страница сохранена как есть — скрипты будут работать,\n"
                    "но визуально она может выглядеть пустой.".format(len(html) // 1024)
                )
            else:
                _status("✅ Страница получена ({} KB, код {})".format(
                    len(html) // 1024, resp.status_code))

            return html

        except requests.exceptions.SSLError as e:
            # SSL ошибка — пробуем без проверки сертификата
            _status("⚠️ SSL ошибка, пробую без проверки сертификата...")
            try:
                resp = requests.get(
                    url, headers=PageDownloader._BROWSER_HEADERS,
                    timeout=20, verify=False
                )
                import urllib3
                urllib3.disable_warnings()
                return resp.text
            except Exception as e2:
                raise Exception("SSL: {} | fallback: {}".format(e, e2))

        except requests.exceptions.ConnectionError as e:
            raise Exception("❌ Не удалось подключиться к {}: {}".format(
                urlparse(url).netloc, e))

        except requests.exceptions.Timeout:
            raise Exception("❌ Таймаут — сервер {} не ответил за 20 секунд".format(
                urlparse(url).netloc))

        except Exception as e:
            raise Exception("❌ Ошибка загрузки: {}".format(e))

    @staticmethod
    def download_full_site(url, output_dir):
        domain = urlparse(url).netloc
        safe_domain = re.sub(r'[^\w.-]', '_', domain)
        target = os.path.join(output_dir, safe_domain)
        os.makedirs(target, exist_ok=True)

        cmd = [
    'wget',
    '--page-requisites',
    '--adjust-extension',
    '--convert-links',
    '--no-host-directories',
    '--no-parent',
    '--level=2',
    '--domains', domain,
    '--directory-prefix=' + target,
    '--accept', 'html,htm,css,js,png,jpg,jpeg,gif,svg,ico',
    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    '--header', 'Accept-Language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    '--load-cookies', 'cookies.txt',   # если есть куки, можно сохранить заранее
    url
]
        try:
            subprocess.run(cmd, check=True, timeout=120)
        except subprocess.TimeoutExpired:
            print("wget превысил таймаут, но часть файлов могла быть скачана.")
        except Exception as e:
            raise Exception(f"Ошибка wget: {e}")

        index_path = None
        for root, dirs, files in os.walk(target):
            if 'index.html' in files:
                index_path = os.path.join(root, 'index.html')
                break
        return index_path, target

    @staticmethod
    def save_page(html, source_url, page_type='single', extra_data=None):
        timestamp = int(time.time())
        domain = urlparse(source_url).netloc.replace('.', '_')
        filename = f"{timestamp}_{domain}.html"
        filepath = os.path.join(PAGES_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        with open(PAGES_JSON, 'r') as f:
            pages = json.load(f)

        page_id = str(timestamp)
        pages[page_id] = {
            'filename': filename,
            'url': source_url,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'size': len(html),
            'type': page_type
        }
        if extra_data:
            pages[page_id].update(extra_data)

        with open(PAGES_JSON, 'w') as f:
            json.dump(pages, f, indent=2)
        return page_id

    @staticmethod
    def save_full_site(source_url, local_path):
        timestamp = int(time.time())
        page_id = str(timestamp)

        with open(PAGES_JSON, 'r') as f:
            pages = json.load(f)

        pages[page_id] = {
            'filename': os.path.basename(local_path),
            'url': source_url,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'size': 0,
            'type': 'full_site',
            'path': local_path
        }

        with open(PAGES_JSON, 'w') as f:
            json.dump(pages, f, indent=2)
        return page_id

    @staticmethod
    def get_all_pages():
        with open(PAGES_JSON, 'r') as f:
            return json.load(f)

    @staticmethod
    def set_active_page(page_id):
        pages = PageDownloader.get_all_pages()
        if page_id not in pages:
            return False
        meta = pages[page_id]

        if meta.get('type') == 'full_site':
            src_path = meta['path']
            dst_path = 'static/current_site'
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)

            index_rel_path = None
            for root, dirs, files in os.walk(dst_path):
                if 'index.html' in files:
                    rel = os.path.relpath(os.path.join(root, 'index.html'), dst_path)
                    index_rel_path = rel.replace('\\', '/')
                    break

            with open('templates/index.html', 'w', encoding='utf-8') as f:
                if index_rel_path:
                    f.write(f'<meta http-equiv="refresh" content="0;url=/static/current_site/{index_rel_path}">')
                else:
                    f.write(f'<meta http-equiv="refresh" content="0;url=/static/current_site/{os.path.basename(meta["path"])}/index.html">')
        else:
            src = os.path.join(PAGES_DIR, meta['filename'])
            dst = "templates/index.html"
            shutil.copy2(src, dst)

        # Сохраняем ID активной страницы
        os.makedirs(os.path.dirname(ACTIVE_FILE), exist_ok=True)
        with open(ACTIVE_FILE, 'w') as f:
            f.write(page_id)
        return True

    @staticmethod
    def clone_page(page_id):
        pages = PageDownloader.get_all_pages()
        if page_id not in pages:
            return None
        original = pages[page_id]
        if original.get('type') == 'full_site':
            src_path = original['path']
            new_timestamp = int(time.time())
            new_path = os.path.join(DOWNLOADS_DIR, f"clone_{new_timestamp}")
            shutil.copytree(src_path, new_path)
            new_id = PageDownloader.save_full_site(original['url'], new_path)
        else:
            src_file = os.path.join(PAGES_DIR, original['filename'])
            with open(src_file, 'r', encoding='utf-8') as f:
                html = f.read()
            new_id = PageDownloader.save_page(html, original['url'], original['type'])
        return new_id

    @staticmethod
    def get_active_page_info():
        """Возвращает информацию об активной странице: ID, URL, тип"""
        if not os.path.exists(ACTIVE_FILE):
            return None
        try:
            with open(ACTIVE_FILE, 'r') as f:
                page_id = f.read().strip()
        except:
            return None

        pages = PageDownloader.get_all_pages()
        if page_id not in pages:
            return None
        meta = pages[page_id]
        return page_id, meta['url'], meta.get('type', 'single')

downloader = PageDownloader()
