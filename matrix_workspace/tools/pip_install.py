def run_tool(inputs):
    import subprocess, sys
    pkgs = inputs.get('packages', inputs.get('package', ''))
    if isinstance(pkgs, list): pkgs = ' '.join(pkgs)
    pkgs = str(pkgs).strip()
    if not pkgs: return {'ok': False, 'output': 'Нужен packages', 'files': [], 'error': 'missing'}
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    r = subprocess.run([sys.executable,'-m','pip','install','--break-system-packages','-q']+pkgs.split(),
                       capture_output=True, timeout=300)
    out = _d(r.stdout)+_d(r.stderr)
    ok = r.returncode == 0
    return {'ok': ok, 'output': ('OK: ' if ok else 'FAIL: ') + pkgs + chr(10) + out[:500], 'files': [], 'error': '' if ok else out[:300]}