def run_tool(inputs: dict) -> dict:
    import csv, json, os
    data = inputs.get('data', [])
    filename = inputs.get('filename', 'output.csv')
    output_dir = inputs.get('output_dir', '/tmp')
    if isinstance(data, str):
        try: data = json.loads(data)
        except: return {'ok': False, 'output': '', 'files': [], 'error': 'data must be JSON list'}
    if not data:
        return {'ok': False, 'output': '', 'files': [], 'error': 'empty data'}
    try:
        out_path = os.path.join(output_dir, filename)
        keys = list(data[0].keys())
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
        return {'ok': True, 'output': f'Written {len(data)} rows to {filename}', 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}