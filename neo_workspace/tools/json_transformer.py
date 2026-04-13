def run_tool(inputs: dict) -> dict:
    import json, os
    data = inputs.get('data', [])
    operation = inputs.get('operation', 'passthrough')  # filter|pluck|flatten|sort|count
    key = inputs.get('key', '')
    value = inputs.get('value', '')
    output_dir = inputs.get('output_dir', '/tmp')
    if isinstance(data, str):
        try: data = json.loads(data)
        except: return {'ok': False, 'output': '', 'files': [], 'error': 'data must be JSON'}
    try:
        if operation == 'filter' and key:
            result = [r for r in data if str(r.get(key, '')) == str(value)]
        elif operation == 'pluck' and key:
            result = [r.get(key) for r in data]
        elif operation == 'flatten':
            flat = []
            def _flatten(obj, prefix=''):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        _flatten(v, f'{prefix}{k}.')
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        _flatten(v, f'{prefix}{i}.')
                else:
                    flat.append({'key': prefix.rstrip('.'), 'value': obj})
            for item in (data if isinstance(data, list) else [data]):
                _flatten(item)
            result = flat
        elif operation == 'sort' and key:
            result = sorted(data, key=lambda x: x.get(key, ''))
        elif operation == 'count':
            from collections import Counter
            result = dict(Counter(str(r.get(key, '')) for r in data))
        else:
            result = data
        out_path = os.path.join(output_dir, 'transformed.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        n = len(result) if isinstance(result, (list, dict)) else 1
        return {'ok': True, 'output': f'{operation}: {n} items', 'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}