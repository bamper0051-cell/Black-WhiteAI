def run_tool(inputs):
    import zipfile, os, time
    from pathlib import Path
    files = inputs.get('files', inputs.get('paths', []))
    output_dir = inputs.get('output_dir', '/tmp')
    name = inputs.get('name', 'archive_' + str(int(time.time())) + '.zip')
    if not files: return {'ok': False, 'output': 'Нужен files', 'files': [], 'error': 'missing'}
    if isinstance(files, str): files = [files]
    out = os.path.join(output_dir, name)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if os.path.isfile(f): zf.write(f, os.path.basename(f))
            elif os.path.isdir(f):
                for fp in Path(f).rglob('*'):
                    if fp.is_file(): zf.write(str(fp), str(fp.relative_to(f)))
    return {'ok': True, 'output': 'ZIP: ' + out, 'files': [out], 'error': ''}