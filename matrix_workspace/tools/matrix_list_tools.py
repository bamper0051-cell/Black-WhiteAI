def run_tool(inputs):
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from agent_matrix import list_tools
        tools = list_tools()
        if not tools: return {'ok': True, 'output': 'Инструментов нет', 'files': [], 'error': ''}
        sep = chr(10)
        lines = ['MATRIX Tools (' + str(len(tools)) + '):']
        for t in tools:
            tag = '📦' if t.get('builtin') else '🔧'
            lines.append('  ' + tag + ' ' + t['name'] + ' — ' + t.get('description','')[:50])
        return {'ok': True, 'output': sep.join(lines), 'files': [], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}