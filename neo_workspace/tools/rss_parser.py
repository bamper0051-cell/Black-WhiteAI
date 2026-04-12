def run_tool(inputs: dict) -> dict:
    import urllib.request, re, json, os
    url = inputs.get('url', '')
    limit = int(inputs.get('limit', 20))
    output_dir = inputs.get('output_dir', '/tmp')
    if not url:
        return {'ok': False, 'output': '', 'files': [], 'error': 'url required'}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NEO/1.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode('utf-8', errors='replace')
        # Parse items with regex (no xml lib needed for simple feeds)
        def _tag(text, tag):
            m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', text, re.DOTALL)
            return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''
        item_blocks = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        if not item_blocks:
            item_blocks = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
        items = []
        for block in item_blocks[:limit]:
            items.append({
                'title':       _tag(block, 'title'),
                'link':        _tag(block, 'link') or _tag(block, 'id'),
                'description': _tag(block, 'description') or _tag(block, 'summary'),
                'pubDate':     _tag(block, 'pubDate') or _tag(block, 'updated'),
            })
        out_path = os.path.join(output_dir, 'feed.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return {'ok': True, 'output': f'Parsed {len(items)} items\n' +
                '\n'.join(f"- {i['title'][:70]}" for i in items[:5]),
                'files': [out_path], 'error': ''}
    except Exception as e:
        return {'ok': False, 'output': '', 'files': [], 'error': str(e)}