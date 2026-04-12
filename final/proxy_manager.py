"""
BlackBugsAI — Proxy / Tor Manager
Управляет прокси для HTTP-запросов агентов.
"""
import os, time, random
import config

class ProxyManager:
    def __init__(self):
        self._pool  = self._load_pool()
        self._idx   = 0
        self._cfg   = config.PROXY

    def _load_pool(self) -> list:
        proxies = []
        cfg = config.PROXY
        if cfg.get('url'):
            proxies.append(cfg['url'])
        pool_file = os.getenv('PROXY_LIST_FILE', '')
        if pool_file and os.path.exists(pool_file):
            with open(pool_file) as f:
                proxies += [l.strip() for l in f if l.strip() and not l.startswith('#')]
        if cfg.get('tor'):
            port = cfg.get('tor_port', 9050)
            proxies.append(f'socks5://127.0.0.1:{port}')
        return proxies

    def get_proxy(self):
        if not self._cfg.get('enabled') or not self._pool:
            return None
        url = random.choice(self._pool) if self._cfg.get('rotate') else self._pool[self._idx % len(self._pool)]
        self._idx += 1
        return {'http': url, 'https': url}

    def get_session(self):
        import requests
        s = requests.Session()
        proxy = self.get_proxy()
        if proxy:
            s.proxies.update(proxy)
            s.verify = False
        return s

    def rotate_tor(self) -> bool:
        if not self._cfg.get('tor'): return False
        try:
            from stem import Signal
            from stem.control import Controller
            with Controller.from_port(port=9051) as ctrl:
                ctrl.authenticate()
                ctrl.signal(Signal.NEWNYM)
                time.sleep(2)
            return True
        except Exception as e:
            print(f"  ⚠️ Tor rotate: {e}", flush=True)
            return False

    def check(self) -> dict:
        try:
            s = self.get_session()
            r = s.get('https://api.ipify.org?format=json', timeout=10)
            proxy = self.get_proxy()
            return {'ok': True, 'ip': r.json().get('ip','?'),
                    'proxy': list(proxy.values())[0] if proxy else 'direct'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @property
    def enabled(self) -> bool:
        return self._cfg.get('enabled', False) and bool(self._pool)

    def info(self) -> str:
        if not self.enabled:
            return "🌐 Прокси выключен"
        mode = "🧅 Tor" if self._cfg.get('tor') else "🔀 Прокси"
        return f"{mode}: {len(self._pool)} адресов"

proxy_manager = ProxyManager()

def get_session():
    return proxy_manager.get_session()

def get_proxy():
    return proxy_manager.get_proxy()
