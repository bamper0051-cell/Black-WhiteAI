def run_tool(inputs: dict) -> dict:
    import urllib.request, urllib.parse, json, os
    url = inputs.get('url', '')
    data = inputs.get('data', {})
    content_type = inputs.get('content_type', 'json')
    headers = inputs.get('headers', {}) or {}
    timeout = int(inputs.get('timeout', 15))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        if isinstance(data, str):
            try: data = json.loads(data)
            except: pass
        if content_type == 'json':
            body = json.dumps(data).encode('utf-8')
            ct = 'application/json'
        else:
            body = urllib.parse.urlencode(data if isinstance(data, dict) else {}).encode()
            ct = 'application/x-www-form-urlencoded'
        req = urllib.request.Request(url, data=body, method='POST',
            headers={'Content-Type': ct, 'User-Agent': 'NEO/1.0',
                     **{str(k): str(v) for k, v in headers.items()}})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            resp = r.read().decode('utf-8', errors='replace')
        out_path = os.path.join(output_dir, 'response.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(resp)
        return {'ok': True, 'output': f'HTTP {status}\n{resp[:500]}', 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}