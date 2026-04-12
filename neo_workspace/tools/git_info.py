def run_tool(inputs: dict) -> dict:
    import subprocess, os
    path    = inputs.get('path', '.')
    command = inputs.get('command', 'log')  # log | status | diff | branch | tags
    limit   = int(inputs.get('limit', 10))
    output_dir = inputs.get('output_dir', '/tmp')
    if not os.path.exists(path):
        return {'ok': False, 'output': '', 'files': [], 'error': f'Path not found: {path}'}
    cmds = {
        'log':    ['git', 'log', f'--max-count={limit}', '--oneline', '--decorate'],
        'status': ['git', 'status', '--short'],
        'diff':   ['git', 'diff', '--stat'],
        'branch': ['git', 'branch', '-a'],
        'tags':   ['git', 'tag', '-l'],
    }
    cmd = cmds.get(command, cmds['log'])
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=15, cwd=path)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        # not a git repo is a soft failure (tool itself works)
        not_git = 'not a git repository' in err.lower()
        ok = r.returncode == 0 or not_git
        out_path = os.path.join(output_dir, f'git_{command}.txt')
        display = out[:2000] if out else (err[:200] if not not_git else 'git_info ready (path is not a git repo)')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(display)
        return {'ok': ok, 'output': display, 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}