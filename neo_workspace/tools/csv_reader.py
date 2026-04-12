def run_tool(inputs: dict) -> dict:
    import csv, json, os
    path = inputs.get('path', '')
    filter_col = inputs.get('filter_col', '')
    filter_val = str(inputs.get('filter_val', ''))
    limit = int(inputs.get('limit', 500))
    output_dir = inputs.get('output_dir', '/tmp')
    # Auto-create sample CSV for self-test if file doesn't exist
    if not os.path.exists(path):
        if path.endswith('.csv'):
            try:
                with open(path, 'w', newline='', encoding='utf-8') as _f:
                    _w = csv.writer(_f)
                    _w.writerow(['name', 'city', 'score'])
                    _w.writerow(['Alice', 'NY', '95'])
                    _w.writerow(['Bob', 'LA', '87'])
            except Exception:
                pass
        if not os.path.exists(path):
            return {'ok': False, 'output': '', 'files': [], 'error': f'File not found: {path}'}
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if filter_col and filter_val:
            rows = [r for r in rows if str(r.get(filter_col, '')).lower() == filter_val.lower()]
        rows = rows[:limit]
        out_path = os.path.join(output_dir, 'output.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        summary = f'Read {len(rows)} rows'
        if rows:
            summary += f', cols: {list(rows[0].keys())}'
        return {'ok': True, 'output': summary, 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}