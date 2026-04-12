def run_tool(inputs: dict) -> dict:
    import urllib.request, json
    url    = inputs.get('url', '')
    data   = inputs.get('data', {})
    fmt    = inputs.get('format', 'json')
    timeout = int(inputs.get('timeout', 10))
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        if isinstance(data, str):
            try: data = json.loads(data)
            except: data = {'text': data}
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, method='POST',
            headers={'Content-Type': 'application/json', 'User-Agent': 'NEO/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            resp = r.read().decode('utf-8', errors='replace')[:500]
        ok = 200 <= status < 300
        return {'ok': ok, 'output': f'HTTP {status}: {resp}', 'files': [], 'error': '' if ok else resp}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}