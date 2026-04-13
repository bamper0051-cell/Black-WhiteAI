import sys, json, traceback
sys.path.insert(0, '/home/bamper0051/x/matrix_workspace/tools')
sys.path.insert(0, '/home/bamper0051/x')

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

inputs = {'code': "import sys, platform, os\nprint(f'Python: {sys.version}')\nprint(f'Platform: {platform.platform()}')\nprint(f'Current dir: {os.getcwd()}')\nprint(f'Tools available: matrix_list_tools will show them')", 'output_dir': '/home/bamper0051/x/matrix_workspace/artifacts/run_1775722868556'}
try:
    result = run_tool(inputs)
    if not isinstance(result, dict): result = {'ok': True, 'output': str(result), 'files': [], 'error': ''}
    print('__MATRIX_RESULT__:' + json.dumps(result, ensure_ascii=False, default=str))
except Exception as e:
    print('__MATRIX_RESULT__:' + json.dumps({'ok': False, 'output': '', 'files': [], 'error': traceback.format_exc()[-500:]}))
