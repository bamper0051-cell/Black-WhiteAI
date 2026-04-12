def run_tool(inputs):
    import os, sys, sqlite3
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    name = inputs.get('name', inputs.get('tool_name', '')).strip()
    if not name: return {'ok': False, 'output': 'Нужен name', 'files': [], 'error': 'missing'}
    try:
        from agent_matrix import TOOLS_DB, TOOLS_DIR
        db = sqlite3.connect(str(TOOLS_DB))
        row = db.execute('SELECT 1 FROM tools WHERE name=?', (name,)).fetchone()
        if not row:
            db.close()
            return {'ok': False, 'output': 'Инструмент не найден: ' + name, 'files': [], 'error': 'not_found'}
        db.execute('DELETE FROM tools WHERE name=?', (name,))
        db.commit(); db.close()
        f = TOOLS_DIR / (name + '.py')
        if f.exists(): f.unlink()
        return {'ok': True, 'output': 'Удалён: ' + name, 'files': [], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': str(e), 'files': [], 'error': str(e)}