def run_tool(inputs):
    import subprocess, sys
    from pathlib import Path
    req_file = inputs.get('requirements', inputs.get('path', ''))
    output_dir = inputs.get('output_dir', '/tmp')
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    # Попробуем pip-audit
    cmd = [sys.executable, '-m', 'pip_audit']
    if req_file: cmd += ['-r', req_file]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if r.returncode not in (0, 1) or not r.stdout:
        # Установить pip-audit
        subprocess.run([sys.executable,'-m','pip','install','pip-audit','-q','--break-system-packages'],
                       capture_output=True, timeout=120)
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    out = _d(r.stdout) + _d(r.stderr)
    vuln = [l for l in out.splitlines() if 'CVE' in l or 'vuln' in l.lower()]
    ok = len(vuln) == 0
    summary = ('✅ Уязвимостей не найдено' if ok else '❌ Найдено: ' + str(len(vuln))) + chr(10) + out[:2000]
    f = Path(output_dir) / 'deps_audit.txt'
    f.write_text(summary, encoding='utf-8')
    return {'ok': ok, 'output': summary, 'files': [str(f)], 'error': ''}