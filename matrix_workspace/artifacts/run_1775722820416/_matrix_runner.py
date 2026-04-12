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

inputs = {'code': "import os, sys, platform, json\ninfo = {\n    'agent_name': 'AGENT MATRIX v2.0',\n    'python_version': sys.version,\n    'platform': platform.platform(),\n    'user': os.getenv('USER') or os.getenv('USERNAME'),\n    'tools_available': ['python_eval', 'shell_cmd', 'file_read', 'file_write', 'zip_files', 'run_tests', 'analyze_code', 'osint_username', 'osint_domain', 'web_scrape', 'http_get', 'port_scan', 'ssl_check', 'deps_audit', 'github_clone', 'github_install', 'pip_install', 'matrix_create_tool', 'matrix_list_tools'],\n    'role': 'планировщик задач с возможностью выполнения кода и использования инструментов OSINT/безопасности'\n}\nprint(json.dumps(info, indent=2, ensure_ascii=False))", 'output_dir': '/home/bamper0051/x/matrix_workspace/artifacts/run_1775722820416'}
try:
    result = run_tool(inputs)
    if not isinstance(result, dict): result = {'ok': True, 'output': str(result), 'files': [], 'error': ''}
    print('__MATRIX_RESULT__:' + json.dumps(result, ensure_ascii=False, default=str))
except Exception as e:
    print('__MATRIX_RESULT__:' + json.dumps({'ok': False, 'output': '', 'files': [], 'error': traceback.format_exc()[-500:]}))
