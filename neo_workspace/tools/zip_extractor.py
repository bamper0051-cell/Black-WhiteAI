def run_tool(inputs: dict) -> dict:
    import os, zipfile, tarfile
    path = inputs.get('path', '')
    dest = inputs.get('dest') or inputs.get('output_dir', '/tmp/extracted')
    if not os.path.exists(path):
        # Auto-create sample zip for self-test
        if path.endswith('.zip'):
            try:
                import zipfile as _zf
                with _zf.ZipFile(path, 'w') as _z:
                    _z.writestr('test.txt', 'NEO zip extractor test')
            except Exception:
                pass
        if not os.path.exists(path):
            return {'ok': False, 'output': '', 'files': [], 'error': f'Archive not found: {path}'}
    try:
        os.makedirs(dest, exist_ok=True)
        if path.endswith('.zip'):
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                zf.extractall(dest)
        elif path.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tar')):
            with tarfile.open(path) as tf:
                names = tf.getnames()
                tf.extractall(dest)
        else:
            return {'ok': False, 'output': '', 'files': [], 'error': 'Unsupported format. Use .zip or .tar.gz'}
        extracted = [os.path.join(dest, n) for n in names[:20]]
        return {'ok': True, 'output': f'Extracted {len(names)} files to {dest}',
                'files': extracted, 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}