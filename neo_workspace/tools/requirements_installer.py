def run_tool(inputs: dict) -> dict:
    import subprocess, sys, importlib
    packages   = inputs.get('packages', [])
    check_only = inputs.get('check_only', False)
    if isinstance(packages, str):
        packages = [p.strip() for p in packages.replace(',', '\n').splitlines() if p.strip()]
    results = {}
    for pkg in packages:
        name = pkg.split('==')[0].split('>=')[0].split('<=')[0].strip()
        import_name = name.replace('-', '_').replace('beautifulsoup4', 'bs4')
        try:
            importlib.import_module(import_name)
            results[pkg] = 'already_installed'
        except ImportError:
            if check_only:
                results[pkg] = 'missing'
            else:
                try:
                    r = subprocess.run([sys.executable, '-m', 'pip', 'install',
                                        '--break-system-packages', '--quiet', pkg],
                                       capture_output=True, timeout=60)
                    results[pkg] = 'installed' if r.returncode == 0 else f'failed: {r.stderr.decode()[:100]}'
                except Exception as e:
                    results[pkg] = f'error: {e}'
    ok = all(v in ('already_installed', 'installed') for v in results.values())
    summary = '\n'.join(f'{k}: {v}' for k, v in results.items())
    return {'ok': ok, 'output': summary, 'files': [], 'error': '' if ok else 'Some packages failed'}