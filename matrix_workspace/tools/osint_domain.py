def run_tool(inputs):
    import urllib.request, subprocess, socket
    from pathlib import Path
    domain = inputs.get('domain', inputs.get('url', '')).strip()
    domain = domain.replace('https://','').replace('http://','').split('/')[0]
    output_dir = inputs.get('output_dir', '/tmp')
    if not domain: return {'ok': False, 'output': 'Нужен domain', 'files': [], 'error': 'missing'}
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    sep = chr(10)
    lines = ['OSINT: ' + domain]
    try: lines.append('IP: ' + socket.gethostbyname(domain))
    except Exception as e: lines.append('DNS: ' + str(e))
    try:
        req = urllib.request.Request('https://' + domain, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            for k in ('Server','X-Powered-By','Content-Type','X-Frame-Options'):
                v = r.headers.get(k)
                if v: lines.append(k + ': ' + v)
    except Exception as e: lines.append('HTTP: ' + str(e))
    r = subprocess.run(['whois', domain], capture_output=True, timeout=20)
    if r.returncode == 0: lines.append(sep + 'WHOIS:' + sep + _d(r.stdout)[:600])
    text = sep.join(lines)
    out_file = Path(output_dir) / ('domain_' + domain + '.txt')
    out_file.write_text(text, encoding='utf-8')
    return {'ok': True, 'output': text, 'files': [str(out_file)], 'error': ''}