def run_tool(inputs):
    import ast, os, subprocess, sys
    from pathlib import Path
    code = inputs.get('code', '')
    path = inputs.get('path', '')
    output_dir = inputs.get('output_dir', '/tmp')
    if path and os.path.exists(path):
        code = open(path, encoding='utf-8', errors='replace').read()
    if not code: return {'ok': False, 'output': 'Нужен code или path', 'files': [], 'error': 'missing'}
    issues = []
    try:
        ast.parse(code); issues.append('✅ Синтаксис OK')
    except SyntaxError as e:
        issues.append('❌ SyntaxError строка ' + str(e.lineno) + ': ' + str(e.msg))
    lines = code.split(chr(10))
    for i, l in enumerate(lines, 1):
        if 'except:' in l: issues.append('⚠️ Строка ' + str(i) + ': голый except')
        if len(l) > 120: issues.append('📏 Строка ' + str(i) + ': длинная (' + str(len(l)) + ' символов)')
    report = chr(10).join(issues) + chr(10) + chr(10) + 'Строк: ' + str(len(lines))
    out = Path(output_dir) / 'analysis.txt'
    out.write_text(report, encoding='utf-8')
    return {'ok': True, 'output': report, 'files': [str(out)], 'error': ''}