def run_tool(inputs):
    import subprocess, os, shutil
    from pathlib import Path
    url = inputs.get('url', inputs.get('repo', '')).strip()
    output_dir = inputs.get('output_dir', '/tmp')
    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}
    name = url.rstrip('/').split('/')[-1].replace('.git','')
    dest = str(Path(output_dir) / name)
    if os.path.exists(dest): shutil.rmtree(dest)
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    r = subprocess.run(['git','clone','--depth=1',url,dest], capture_output=True, timeout=120)
    out = _d(r.stdout) + _d(r.stderr)
    if r.returncode == 0:
        cnt = sum(1 for p in Path(dest).rglob('*') if p.is_file())
        return {'ok': True, 'output': 'Клонировано: ' + dest + ' (' + str(cnt) + ' файлов)', 'files': [dest], 'error': ''}
    return {'ok': False, 'output': out, 'files': [], 'error': out}