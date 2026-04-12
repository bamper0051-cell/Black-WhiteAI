def run_tool(inputs: dict) -> dict:
    import difflib, os
    mode   = inputs.get('mode', 'text')   # text | files
    output_dir = inputs.get('output_dir', '/tmp')
    try:
        if mode == 'files':
            path_a = inputs.get('path_a', '')
            path_b = inputs.get('path_b', '')
            with open(path_a, encoding='utf-8', errors='ignore') as f: a = f.readlines()
            with open(path_b, encoding='utf-8', errors='ignore') as f: b = f.readlines()
            label_a, label_b = path_a, path_b
        else:
            a = [l + '\n' for l in inputs.get('text_a', '').splitlines()]
            b = [l + '\n' for l in inputs.get('text_b', '').splitlines()]
            label_a, label_b = 'a', 'b'
        diff = list(difflib.unified_diff(a, b, fromfile=label_a, tofile=label_b, lineterm=''))
        diff_text = ''.join(diff)
        added   = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
        removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
        out_path = os.path.join(output_dir, 'diff.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(diff_text)
        return {'ok': True, 'output': f'+{added} lines / -{removed} lines\n{diff_text[:1000]}',
                'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}