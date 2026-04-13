def run_tool(inputs: dict) -> dict:
    import json, os
    data  = inputs.get('data', [])
    key   = inputs.get('key', '')
    keep  = inputs.get('keep', 'first')   # first | last
    output_dir = inputs.get('output_dir', '/tmp')
    if isinstance(data, str):
        try: data = json.loads(data)
        except: return {'ok': False, 'output': '', 'files': [], 'error': 'data must be JSON list'}
    try:
        if not key:
            seen = set(); result = []
            for row in data:
                h = json.dumps(row, sort_keys=True)
                if h not in seen:
                    seen.add(h); result.append(row)
        else:
            seen = {}
            for i, row in enumerate(data):
                k = str(row.get(key, i))
                if keep == 'last' or k not in seen:
                    seen[k] = row
            result = list(seen.values())
        removed = len(data) - len(result)
        out_path = os.path.join(output_dir, 'deduped.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return {'ok': True, 'output': f'Removed {removed} duplicates. Remaining: {len(result)}',
                'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}