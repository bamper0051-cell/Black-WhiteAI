def run_tool(inputs):
    import ssl, socket, datetime
    from pathlib import Path
    host = inputs.get('host', inputs.get('domain', '')).strip()
    host = host.replace('https://','').replace('http://','').split('/')[0]
    output_dir = inputs.get('output_dir', '/tmp')
    if not host: return {'ok': False, 'output': 'Нужен host', 'files': [], 'error': 'missing'}
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(10); s.connect((host, 443))
            cert = s.getpeercert()
        exp = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        days = (exp - datetime.datetime.utcnow()).days
        lines = [
            'Host: ' + host,
            'Subject: ' + str(cert.get('subject','')),
            'Issuer: ' + str(cert.get('issuer','')),
            'Expires: ' + str(exp) + ' (' + str(days) + ' дней)',
            'Status: ' + ('✅ OK' if days > 0 else '❌ ИСТЁК'),
        ]
        text = chr(10).join(lines)
        f = Path(output_dir) / ('ssl_' + host + '.txt')
        f.write_text(text, encoding='utf-8')
        return {'ok': days > 0, 'output': text, 'files': [str(f)], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}