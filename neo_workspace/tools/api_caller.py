def run_tool(inputs: dict) -> dict:
    import urllib.request, urllib.parse, json, os
    url    = inputs.get('url', '')
    method = inputs.get('method', 'GET').upper()
    auth   = inputs.get('auth_header', '')   # e.g. "Bearer TOKEN" or "token TOKEN"
    params = inputs.get('params', {}) or {}
    body   = inputs.get('body', {})
    timeout = int(inputs.get('timeout', 15))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        if params:
            url = url + '?' + urllib.parse.urlencode(params)
        hdrs = {'Content-Type': 'application/json', 'Accept': 'application/json',
                'User-Agent': 'NEO/1.0'}
        if auth:
            hdrs['Authorization'] = auth
        data = None
        if body and method in ('POST', 'PUT', 'PATCH'):
            if isinstance(body, str):
                try: body = json.loads(body)
                except: pass
            data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            resp_body = r.read().decode('utf-8', errors='replace')
        out_path = os.path.join(output_dir, 'api_response.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(resp_body)
        try:
            parsed = json.loads(resp_body)
            summary = json.dumps(parsed, ensure_ascii=False, indent=2)[:600]
        except Exception:
            summary = resp_body[:600]
        return {'ok': True, 'output': f'HTTP {status}\n{summary}', 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}