def run_tool(inputs: dict) -> dict:
    import urllib.request, re, json, os
    url = inputs.get('url', '')
    selector = inputs.get('selector', 'a')
    attribute = inputs.get('attribute', 'text')  # text | href | src | any attr name
    limit = int(inputs.get('limit', 50))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 NEO/1.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='replace')
        # Simple regex extraction by tag name
        tag = re.escape(selector.strip('.#').split('[')[0])
        if attribute == 'text':
            matches = re.findall(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.IGNORECASE)
            results = [re.sub(r'<[^>]+>', '', m).strip() for m in matches[:limit]]
        else:
            attr = re.escape(attribute)
            matches = re.findall(rf'<{tag}[^>]*\s{attr}=["\']([^"\']*)["\']', html, re.IGNORECASE)
            results = matches[:limit]
        out_path = os.path.join(output_dir, 'scraped.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return {'ok': True,
                'output': f'Extracted {len(results)} <{selector}> items\n' + '\n'.join(str(r)[:80] for r in results[:5]),
                'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}