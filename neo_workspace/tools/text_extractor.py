def run_tool(inputs: dict) -> dict:
    import re, json, os
    text    = inputs.get('text', '')
    extract = inputs.get('extract', ['emails', 'phones', 'urls', 'dates', 'ips'])
    output_dir = inputs.get('output_dir', '/tmp')
    if isinstance(text, list):
        text = '\n'.join(str(t) for t in text)
    PATTERNS = {
        'emails':  r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b',
        'phones':  r'(?:\+7|8|7)?[\s\-]?\(?[\d]{3}\)?[\s\-]?[\d]{3}[\s\-]?[\d]{2}[\s\-]?[\d]{2}',
        'urls':    r'https?://[^\s<>"{}|\\^`\[\]]+',
        'dates':   r'\b\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\b|\b\d{4}[./\-]\d{2}[./\-]\d{2}\b',
        'ips':     r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'hashtags':r'#\w+',
        'mentions':r'@\w+',
    }
    results = {}
    total = 0
    for key in (extract if isinstance(extract, list) else [extract]):
        if key in PATTERNS:
            found = list(dict.fromkeys(re.findall(PATTERNS[key], text)))  # dedupe, preserve order
            results[key] = found
            total += len(found)
    out_path = os.path.join(output_dir, 'extracted.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    summary_lines = [f'{k}: {len(v)} found' for k, v in results.items() if v]
    return {'ok': True, 'output': f'Total: {total} entities\n' + '\n'.join(summary_lines),
            'files': [out_path], 'error': ''}