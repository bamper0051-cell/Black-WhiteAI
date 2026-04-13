def run_tool(inputs: dict) -> dict:
    import os, fnmatch, re
    directory = inputs.get('directory', '.')
    name_pat   = inputs.get('name_pattern', '*')
    content_pat = inputs.get('content_pattern', '')
    max_results = int(inputs.get('max_results', 50))
    if not os.path.exists(directory):
        return {'ok': False, 'output': '', 'files': [], 'error': f'Directory not found: {directory}'}
    try:
        matches = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                if fnmatch.fnmatch(fname, name_pat):
                    fpath = os.path.join(root, fname)
                    if content_pat:
                        try:
                            with open(fpath, encoding='utf-8', errors='ignore') as f:
                                if re.search(content_pat, f.read(), re.IGNORECASE):
                                    matches.append(fpath)
                        except Exception:
                            pass
                    else:
                        matches.append(fpath)
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break
        summary = f'Found {len(matches)} files'
        if matches:
            summary += ':\n' + '\n'.join(matches[:10])
            if len(matches) > 10:
                summary += f'\n... and {len(matches)-10} more'
        return {'ok': True, 'output': summary, 'files': matches, 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}