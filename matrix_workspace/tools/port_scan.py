def run_tool(inputs):
    import socket, subprocess, sys
    from pathlib import Path
    host    = inputs.get('host', inputs.get('target', '127.0.0.1')).strip()
    ports   = inputs.get('ports', '22,80,443,8080,8443').strip()
    output_dir = inputs.get('output_dir', '/tmp')
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    results = []
    # Пробуем nmap
    r = subprocess.run(['nmap', '-p', ports, '--open', '-T4', host],
                       capture_output=True, timeout=60)
    if r.returncode == 0:
        out = _d(r.stdout)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        f = Path(output_dir) / ('portscan_' + host.replace('.','_') + '.txt')
        f.write_text(out, encoding='utf-8')
        return {'ok': True, 'output': out[:2000], 'files': [str(f)], 'error': ''}
    # Fallback: socket
    for p in ports.split(','):
        try:
            port = int(p.strip())
            with socket.create_connection((host, port), timeout=2):
                results.append('[+] ' + str(port) + '/tcp open')
        except: results.append('[-] ' + p.strip() + '/tcp closed')
    text = 'Скан ' + host + ':' + chr(10) + chr(10).join(results)
    f = Path(output_dir) / ('portscan_' + host.replace('.','_') + '.txt')
    f.write_text(text, encoding='utf-8')
    return {'ok': True, 'output': text, 'files': [str(f)], 'error': ''}