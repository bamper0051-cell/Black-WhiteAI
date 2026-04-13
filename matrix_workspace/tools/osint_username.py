def run_tool(inputs):
    import urllib.request
    from pathlib import Path
    username = inputs.get('username', inputs.get('name', '')).strip()
    output_dir = inputs.get('output_dir', '/tmp')
    if not username: return {'ok': False, 'output': 'Нужен username', 'files': [], 'error': 'missing'}
    platforms = [
        ('GitHub',   'https://github.com/' + username),
        ('Reddit',   'https://www.reddit.com/user/' + username),
        ('Twitter',  'https://twitter.com/' + username),
        ('TikTok',   'https://www.tiktok.com/@' + username),
        ('YouTube',  'https://www.youtube.com/@' + username),
        ('Telegram', 'https://t.me/' + username),
        ('GitLab',   'https://gitlab.com/' + username),
        ('Medium',   'https://medium.com/@' + username),
    ]
    found = []; miss = []
    for p, url in platforms:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                if r.getcode() == 200: found.append('[+] ' + p + ': ' + url)
        except: miss.append('[-] ' + p)
    sep = chr(10)
    text = 'OSINT @' + username + sep + sep + sep.join(found) + sep + 'Не найдено: ' + str(len(miss))
    out_file = Path(output_dir) / ('osint_' + username + '.txt')
    out_file.write_text(text, encoding='utf-8')
    return {'ok': bool(found), 'output': text, 'files': [str(out_file)], 'error': ''}