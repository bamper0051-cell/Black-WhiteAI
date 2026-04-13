def run_tool(inputs):
    import urllib.request, urllib.parse, re, os, zipfile, time
    url        = inputs.get('url', '')
    max_res    = int(inputs.get('max_resources', 30))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        site_dir = os.path.join(output_dir, 'site')
        os.makedirs(site_dir, exist_ok=True)
        hdrs = {'User-Agent': 'Mozilla/5.0 NEO/1.0'}
        def _fetch(u):
            try:
                req = urllib.request.Request(u, headers=hdrs)
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.read(), r.headers.get('Content-Type', '')
            except Exception:
                return None, ''
        html_bytes, _ = _fetch(url)
        if not html_bytes:
            return {'ok': False, 'output': '', 'files': [], 'error': 'Failed to fetch ' + url}
        html = html_bytes.decode('utf-8', errors='replace')
        with open(os.path.join(site_dir, 'index.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        parsed_url = urllib.parse.urlparse(url)
        base_domain = parsed_url.scheme + '://' + parsed_url.netloc
        # Extract resource URLs using simple string search
        res_urls = []
        for tag_attr in ['href=', 'src=']:
            pos = 0
            while True:
                p = html.find(tag_attr, pos)
                if p < 0: break
                pos = p + 1
                q = html[p+len(tag_attr)]
                if q not in ('"', "'"):
                    continue
                end = html.find(q, p+len(tag_attr)+1)
                if end < 0: continue
                val = html[p+len(tag_attr)+1:end]
                ext = val.split('?')[0].lower()
                if any(ext.endswith(e) for e in ('.css','.js','.png','.jpg','.jpeg','.gif','.svg','.ico','.webp','.woff2','.woff')):
                    res_urls.append(val)
        # Resolve + download resources
        downloaded = ['index.html']
        for i, res_url in enumerate(res_urls[:max_res]):
            try:
                if res_url.startswith('//'):
                    res_url = parsed_url.scheme + ':' + res_url
                elif res_url.startswith('/'):
                    res_url = base_domain + res_url
                elif not res_url.startswith('http'):
                    res_url = url.rstrip('/') + '/' + res_url.lstrip('./')
                raw_name = res_url.split('/')[-1].split('?')[0]
                fname = re.sub(r'[^a-zA-Z0-9._-]', '_', raw_name)[:60] or ('res_' + str(i))
                data, _ = _fetch(res_url)
                if data:
                    with open(os.path.join(site_dir, fname), 'wb') as fh:
                        fh.write(data)
                    downloaded.append(fname)
                time.sleep(0.03)
            except Exception:
                pass
        zip_path = os.path.join(output_dir, 'site.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in downloaded:
                fp = os.path.join(site_dir, fname)
                if os.path.exists(fp):
                    zf.write(fp, fname)
        size_kb = os.path.getsize(zip_path) // 1024
        return {
            'ok': True,
            'output': 'Downloaded ' + str(len(downloaded)) + ' files (' + str(size_kb) + ' KB) -> site.zip',
            'files': [zip_path],
            'error': ''
        }
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}
