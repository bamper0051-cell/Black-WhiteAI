def run_tool(inputs):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    url  = inputs.get('url', inputs.get('github_url', '')).strip()
    name = inputs.get('tool_name', inputs.get('name', '')).strip()
    desc = inputs.get('description', '').strip()
    if not url: return {'ok': False, 'output': 'Нужен url', 'files': [], 'error': 'missing'}
    if not name: name = url.rstrip('/').split('/')[-1].replace('.git','').replace('-','_').lower()
    try:
        from agent_matrix import _install_github
        ok, err = _install_github(name, url, desc or ('GitHub: ' + url), on_status=lambda m: print(m))
        if ok: return {'ok': True, 'output': 'Установлен: ' + name + ' из ' + url, 'files': [], 'error': ''}
        return {'ok': False, 'output': err, 'files': [], 'error': err}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}