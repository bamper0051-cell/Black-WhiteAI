def run_tool(inputs):
    import subprocess, sys, tempfile, os
    code = inputs.get('code', inputs.get('script', '')).strip()
    output_dir = inputs.get('output_dir', '/tmp')
    if not code: return {'ok': False, 'output': 'Нужен code', 'files': [], 'error': 'missing'}
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code); tmp = f.name
    try:
        r = subprocess.run([sys.executable, tmp], capture_output=True, timeout=30, cwd=output_dir)
        out = _d(r.stdout) + _d(r.stderr)
        return {'ok': r.returncode==0, 'output': out.strip()[:3000], 'files': [], 'error': _d(r.stderr) if r.returncode else ''}
    finally:
        try: os.unlink(tmp)
        except: pass