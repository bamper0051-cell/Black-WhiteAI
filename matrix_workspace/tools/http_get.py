def run_tool(inputs):
    import urllib.request, urllib.parse, json as _j
    url = inputs.get('url', '').strip()
    params = inputs.get('params', {})
    headers = inputs.get('headers', {})
    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}
    if params and isinstance(params, dict):
        url = url + ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0',**headers})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(100000).decode('utf-8','replace')
        try: result = _j.dumps(_j.loads(body), ensure_ascii=False, indent=2)[:4000]
        except: result = body[:4000]
        return {'ok': True, 'output': result, 'files': [], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}