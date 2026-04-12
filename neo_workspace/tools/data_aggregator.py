def run_tool(inputs: dict) -> dict:
    import json, os
    from collections import defaultdict
    data     = inputs.get('data', [])
    group_by = inputs.get('group_by', '')
    agg_col  = inputs.get('agg_col', '')
    agg_fn   = inputs.get('agg_fn', 'count')  # count|sum|avg|min|max
    output_dir = inputs.get('output_dir', '/tmp')
    if isinstance(data, str):
        try: data = json.loads(data)
        except: return {'ok': False, 'output': '', 'files': [], 'error': 'data must be JSON list'}
    try:
        groups: dict = defaultdict(list)
        for row in data:
            key = str(row.get(group_by, '_all_')) if group_by else '_all_'
            val = row.get(agg_col)
            groups[key].append(val)
        result = {}
        for key, vals in groups.items():
            nums = [v for v in vals if v is not None]
            try: nums = [float(v) for v in nums]
            except: nums = []
            if agg_fn == 'count':   result[key] = len(vals)
            elif agg_fn == 'sum':   result[key] = sum(nums)
            elif agg_fn == 'avg':   result[key] = sum(nums)/len(nums) if nums else 0
            elif agg_fn == 'min':   result[key] = min(nums) if nums else None
            elif agg_fn == 'max':   result[key] = max(nums) if nums else None
            else:                   result[key] = len(vals)
        # Sort by value descending
        result = dict(sorted(result.items(), key=lambda x: (x[1] or 0), reverse=True))
        out_path = os.path.join(output_dir, 'aggregated.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        top = list(result.items())[:5]
        return {'ok': True, 'output': f'{agg_fn} by {group_by}:\n' + '\n'.join(f'  {k}: {v}' for k,v in top),
                'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}