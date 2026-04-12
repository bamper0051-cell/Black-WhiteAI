def run_tool(inputs):
    import urllib.request, re
    from pathlib import Path
    url = inputs.get('url', '').strip()
    output_dir = inputs.get('output_dir', '/tmp')
    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read(200000).decode('utf-8','replace')
        text = re.sub(r'<[^>]+>',' ',html)
        text = re.sub(r' +',' ',text).strip()[:6000]
        f = Path(output_dir) / ('page_' + str(abs(hash(url))%99999) + '.txt')
        f.write_text(text, encoding='utf-8')
        return {'ok': True, 'output': text[:3000], 'files': [str(f)], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}