def run_tool(inputs):
    import subprocess
    cmd = inputs.get('cmd', inputs.get('command', '')).strip()
    cwd = inputs.get('cwd', '') or None
    timeout = int(inputs.get('timeout', 30))
    if not cmd: return {'ok': False, 'output': 'Нужен cmd', 'files': [], 'error': 'missing'}
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout, cwd=cwd)
    out = (_d(r.stdout) + _d(r.stderr)).strip()
    return {'ok': r.returncode==0, 'output': out[:3000], 'files': [], 'error': out[:500] if r.returncode else ''}