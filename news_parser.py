import requests
import feedparser
import urllib3
from bs4 import BeautifulSoup
from database import save_news

# Отключаем SSL warnings — в Termux часто проблемы с сертификатами
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Только рабочие источники (mail.ru работает — оставляем, остальные с SSL падают)
RSS_FEEDS = {
    'mail.ru': [
        'https://news.mail.ru/rss/main/',
        'https://news.mail.ru/rss/society/',
        'https://news.mail.ru/rss/politics/',
    ],
    'yandex': [
        'https://news.yandex.ru/index.rss',
    ],
    'meduza': [
        'https://meduza.io/rss/all',
    ],
    # RT блокирует соединения вне РФ на уровне SSL → заменён на Медиазону
    'медиазона': [
        'https://zona.media/rss',
    ],
    # CNN закрыл RSS в 2024 → заменён на BBC World Service
    'bbc': [
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://feeds.bbci.co.uk/news/rss.xml',
    ],
    'bbc': [
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://feeds.bbci.co.uk/news/world/rss.xml',
    ],
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
}

TIMEOUT = 15

def _fetch_rss(url: str) -> feedparser.FeedParserDict | None:
    """Качаем с таймаутом и verify=False для Termux SSL проблем."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except requests.Timeout:
        print(f"    ⏰ Таймаут ({TIMEOUT}с): {url}", flush=True)
    except requests.RequestException as e:
        print(f"    🚫 Сеть: {e}", flush=True)
    return None

def _fetch_text(url: str, max_chars=3000) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        body = soup.find('article') or soup.find('main') or soup.body
        if body:
            return body.get_text(' ', strip=True)[:max_chars]
    except Exception as e:
        print(f"    ⚠️  fetch_text: {e}", flush=True)
    return ''

def _clean_html(text: str) -> str:
    return BeautifulSoup(text, 'html.parser').get_text(' ', strip=True) if text else ''

def parse_source(source: str, urls: list) -> int:
    for url in urls:
        print(f"    🔗 {url}", flush=True)
        feed = _fetch_rss(url)
        if feed is None or not feed.entries:
            continue

        print(f"    📰 Найдено записей: {len(feed.entries)}", flush=True)
        added = 0
        for entry in feed.entries:
            title   = (entry.get('title') or '').strip()
            link    = (entry.get('link') or '').strip()
            content = _clean_html(entry.get('summary') or entry.get('description') or '')

            if len(content) < 80 and link:
                content = _fetch_text(link)
            content = content or title

            if title and link and save_news(source, title, link, content):
                added += 1

        return added  # успех — не пробуем следующий URL

    return 0

def parse_all() -> int:
    total = 0
    for source, urls in RSS_FEEDS.items():
        print(f"\n  📡 {source}...", flush=True)
        n = parse_source(source, urls)
        print(f"  ✅ {source}: +{n} новых", flush=True)
        total += n
    print(f"\n  📦 Итого добавлено: {total}", flush=True)
    return total
