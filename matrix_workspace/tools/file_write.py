def run_tool(inputs):
    import os, time
    from pathlib import Path
    path = inputs.get('path', '').strip()
    content = inputs.get('content', '')
    output_dir = inputs.get('output_dir', '/tmp')
    if not path: path = str(Path(output_dir) / ('out_' + str(int(time.time())) + '.txt'))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Path(path).write_text(str(content), encoding='utf-8')
    return {'ok': True, 'output': 'Записано: ' + path, 'files': [path], 'error': ''}