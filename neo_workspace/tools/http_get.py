def run_tool(inputs: dict) -> dict:
    import urllib.request, urllib.error, json, os
    url = inputs.get('url', '')
    headers = inputs.get('headers', {}) or {}
    timeout = int(inputs.get('timeout', 10))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'NEO/1.0',
            **{str(k): str(v) for k, v in headers.items()}
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            body = r.read().decode('utf-8', errors='replace')
        out_path = os.path.join(output_dir, 'response.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(body)
        return {'ok': True, 'output': f'HTTP {status} | {len(body)} bytes\n{body[:500]}',
                'files': [out_path], 'error': ''}
    except urllib.error.HTTPError as e:
        return {'ok': False, 'output': '', 'files': [], 'error': f'HTTP {e.code}: {e.reason}'}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}