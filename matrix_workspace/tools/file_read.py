def run_tool(inputs):
    import os
    path = inputs.get('path', '').strip()
    if not path or not os.path.exists(path):
        return {'ok': False, 'output': 'Не найден: ' + path, 'files': [], 'error': 'not_found'}
    if os.path.isdir(path):
        return {'ok': True, 'output': 'Dir: ' + ', '.join(os.listdir(path)[:30]), 'files': [], 'error': ''}
    for enc in ('utf-8','cp1251','latin-1'):
        try:
            content = open(path, encoding=enc).read()
            return {'ok': True, 'output': content[:5000], 'files': [path], 'error': ''}
        except UnicodeDecodeError: continue
    return {'ok': False, 'output': 'Не удалось декодировать', 'files': [], 'error': 'decode'}