def run_tool(inputs):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    name    = inputs.get('tool_name', inputs.get('name', '')).strip()
    desc    = inputs.get('description', '').strip()
    example = inputs.get('example_inputs', {})
    url     = inputs.get('url', inputs.get('github_url', '')).strip()
    if not name: return {'ok': False, 'output': 'Нужен tool_name', 'files': [], 'error': 'missing'}
    try:
        from agent_matrix import generate_tool
        ok, err = generate_tool(name, desc, example, github_url=url, on_status=lambda m: print(m))
        if ok: return {'ok': True, 'output': 'Инструмент ' + repr(name) + ' создан!', 'files': [], 'error': ''}
        return {'ok': False, 'output': err, 'files': [], 'error': err}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}