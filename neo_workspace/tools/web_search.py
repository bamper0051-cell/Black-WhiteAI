def run_tool(inputs: dict) -> dict:
    import os
    import json
    import requests
    from urllib.parse import quote_plus, urlparse
    import time
    import re
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    try:
        # Extract inputs
        query = inputs.get("query", "")
        language = inputs.get("language", "ru")
        chat_id = inputs.get("chat_id", "")
        task = inputs.get("task", "")
        
        print(f"Starting web search for query: '{query}'")
        print(f"Language: {language}")
        print(f"Chat ID: {chat_id}")
        
        if not query:
            return {"ok": False, "output": "", "files": [], "error": "Query parameter is required"}
        
        # Prepare search parameters
        search_terms = query
        if task and "отвечай по русски" in task.lower():
            language = "ru"
        
        # Try multiple search approaches
        results = []
        
        # Approach 1: DuckDuckGo HTML scraping (fallback)
        print("Attempting DuckDuckGo search...")
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_terms)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': language
            }
            
            response = requests.get(ddg_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse HTML for results
                from html.parser import HTMLParser
                
                class DDGParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.in_result = False
                        self.in_title = False
                        self.in_snippet = False
                        self.current_result = {}
                        self.results = []
                        self.data_buffer = ""
                        
                    def handle_starttag(self, tag, attrs):
                        attrs_dict = dict(attrs)
                        if tag == 'a' and 'class' in attrs_dict and 'result__url' in attrs_dict['class']:
                            self.in_result = True
                            self.current_result = {'url': attrs_dict.get('href', '')}
                        elif self.in_result and tag == 'a' and 'class' in attrs_dict and 'result__a' in attrs_dict['class']:
                            self.in_title = True
                        elif self.in_result and tag == 'a' and 'class' in attrs_dict and 'result__snippet' in attrs_dict['class']:
                            self.in_snippet = True
                            
                    def handle_endtag(self, tag):
                        if tag == 'a' and self.in_title:
                            self.in_title = False
                            if self.data_buffer:
                                self.current_result['title'] = self.data_buffer.strip()
                                self.data_buffer = ""
                        elif tag == 'a' and self.in_snippet:
                            self.in_snippet = False
                            if self.data_buffer:
                                self.current_result['snippet'] = self.data_buffer.strip()
                                self.data_buffer = ""
                                # Save completed result
                                if 'title' in self.current_result and 'url' in self.current_result:
                                    self.results.append(self.current_result.copy())
                                self.current_result = {}
                                self.in_result = False
                                
                    def handle_data(self, data):
                        if self.in_title or self.in_snippet:
                            self.data_buffer += data
                
                parser = DDGParser()
                parser.feed(response.text)
                
                for result in parser.results[:5]:  # Limit to 5 results
                    if result.get('url') and not result['url'].startswith('//'):
                        results.append({
                            'title': result.get('title', 'No title'),
                            'url': result['url'],
                            'snippet': result.get('snippet', 'No description'),
                            'source': 'DuckDuckGo'
                        })
                
                print(f"Found {len(results)} results from DuckDuckGo")
                
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
        
        # Approach 2: Use a public search API as fallback
        if len(results) < 3:
            print("Trying alternative search method...")
            try:
                # Use a simple Wikipedia search as fallback
                wiki_url = f"https://{language}.wikipedia.org/w/api.php"
                params = {
                    'action': 'query',
                    'list': 'search',
                    'srsearch': search_terms,
                    'format': 'json',
                    'srlimit': 5
                }
                
                wiki_response = requests.get(wiki_url, params=params, timeout=10)
                
                if wiki_response.status_code == 200:
                    wiki_data = wiki_response.json()
                    for item in wiki_data.get('query', {}).get('search', [])[:3]:
                        page_url = f"https://{language}.wikipedia.org/wiki/{quote_plus(item['title'])}"
                        results.append({
                            'title': item['title'],
                            'url': page_url,
                            'snippet': item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', ''),
                            'source': 'Wikipedia'
                        })
                    
                    print(f"Added {len(wiki_data.get('query', {}).get('search', []))} Wikipedia results")
                    
            except Exception as e:
                print(f"Wikipedia search failed: {e}")
        
        # Format results
        if results:
            output_lines = []
            output_lines.append(f"🔍 **Результаты поиска для: '{query}'**")
            output_lines.append(f"🌐 **Язык: {language}**")
            output_lines.append("")
            
            for i, result in enumerate(results[:5], 1):
                output_lines.append(f"{i}. **{result['title']}**")
                output_lines.append(f"   📎 {result['url']}")
                output_lines.append(f"   📝 {result['snippet'][:150]}...")
                output_lines.append(f"   🔗 Источник: {result['source']}")
                output_lines.append("")
            
            output_lines.append(f"Всего найдено результатов: {len(results)}")
            
            if len(results) < 2:
                output_lines.append("\n⚠️ Найдено мало результатов. Попробуйте уточнить запрос.")
            
            result_text = "\n".join(output_lines)
            
        else:
            result_text = f"❌ По запросу '{query}' ничего не найдено.\n\nСоветы:\n1. Проверьте правильность написания\n2. Попробуйте другие ключевые слова\n3. Уточните язык поиска"
        
        # Save results to file
        timestamp = int(time.time())
        filename = f"search_results_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'query': query,
                'language': language,
                'timestamp': timestamp,
                'results': results,
                'summary': result_text
            }, f, ensure_ascii=False, indent=2)
        
        print(f"Search completed. Found {len(results)} results.")
        print(f"Results saved to: {filepath}")
        
        return {
            "ok": True, 
            "output": result_text, 
            "files": [filename], 
            "error": ""
        }
        
    except Exception as e:
        error_msg = f"Ошибка при выполнении поиска: {str(e)}"
        print(f"Error: {error_msg}")
        return {"ok": False, "output": "", "files": [], "error": error_msg}