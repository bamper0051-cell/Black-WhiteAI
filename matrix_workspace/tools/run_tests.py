def run_tool(inputs):
    import subprocess, sys, os
    from pathlib import Path
    path = inputs.get('path', inputs.get('test_file', '.')).strip()
    args = inputs.get('args', '-v').strip()
    output_dir = inputs.get('output_dir', '/tmp')
    def _d(b):
        if not b: return ''
        for e in ('utf-8','cp1251','latin-1'):
            try: return b.decode(e)
            except: pass
        return b.decode('utf-8', errors='replace')
    r = subprocess.run([sys.executable, '-m', 'pytest', path] + args.split() + ['--tb=short'],
                       capture_output=True, timeout=60, cwd=os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) else path)
    out = _d(r.stdout) + _d(r.stderr)
    return {'ok': r.returncode==0, 'output': out[:3000], 'files': [], 'error': '' if r.returncode==0 else out[:500]}