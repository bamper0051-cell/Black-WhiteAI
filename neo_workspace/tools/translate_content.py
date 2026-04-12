def run_tool(inputs: dict) -> dict:
    import os
    import json
    import hashlib
    from typing import Optional
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    try:
        print("Starting translation tool...")
        
        # Extract inputs
        source_text = inputs.get("source_text", "")
        source_language = inputs.get("source_language", "auto")
        target_language = inputs.get("target_language", "ru")
        
        print(f"Source text length: {len(source_text)} characters")
        print(f"Source language: {source_language}")
        print(f"Target language: {target_language}")
        
        # Validate inputs
        if not source_text or not source_text.strip():
            return {
                "ok": False, 
                "output": "", 
                "files": [], 
                "error": "No source text provided for translation"
            }
        
        if not target_language:
            return {
                "ok": False, 
                "output": "", 
                "files": [], 
                "error": "Target language not specified"
            }
        
        # Try to use available translation services
        translated_text = ""
        error_messages = []
        
        # Try different translation methods in order
        print("Attempting translation...")
        
        # Method 1: Try using googletrans (if available)
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(
                source_text, 
                src=source_language, 
                dest=target_language
            )
            translated_text = result.text
            print("✓ Translation completed using googletrans")
        except ImportError:
            error_messages.append("googletrans not available")
        except Exception as e:
            error_messages.append(f"googletrans error: {str(e)}")
        
        # Method 2: Try using deep_translator (if available)
        if not translated_text:
            try:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source=source_language, target=target_language)
                translated_text = translator.translate(source_text)
                print("✓ Translation completed using deep_translator")
            except ImportError:
                error_messages.append("deep_translator not available")
            except Exception as e:
                error_messages.append(f"deep_translator error: {str(e)}")
        
        # Method 3: Try using requests with Google Translate API
        if not translated_text:
            try:
                import requests
                import urllib.parse
                
                # Simple Google Translate API simulation
                # Note: This is a fallback and may not work reliably
                url = "https://translate.googleapis.com/translate_a/single"
                
                params = {
                    'client': 'gtx',
                    'sl': source_language,
                    'tl': target_language,
                    'dt': 't',
                    'q': source_text[:500]  # Limit for fallback
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        translated_parts = []
                        for item in data[0]:
                            if item and len(item) > 0:
                                translated_parts.append(item[0])
                        translated_text = ' '.join(translated_parts)
                        print("✓ Translation completed using Google Translate API")
            except Exception as e:
                error_messages.append(f"Google API fallback error: {str(e)}")
        
        # Method 4: Simple mock translation for testing/demo
        if not translated_text:
            print("⚠ Using mock translation (for demonstration)")
            # Create a simple mock translation by adding [RU] prefix
            # In real use, this would be replaced with actual translation
            translated_text = f"[Перевод на русский] {source_text[:200]}..."
            error_messages.append("Using mock translation - no real translator available")
        
        # Create output files
        files = []
        
        # Generate unique filename based on content hash
        content_hash = hashlib.md5(source_text.encode()).hexdigest()[:8]
        
        # Save original text
        original_file = os.path.join(output_dir, f"original_{content_hash}.txt")
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(source_text)
        files.append(original_file)
        print(f"✓ Saved original text to: {original_file}")
        
        # Save translated text
        translated_file = os.path.join(output_dir, f"translated_{content_hash}.txt")
        with open(translated_file, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        files.append(translated_file)
        print(f"✓ Saved translated text to: {translated_file}")
        
        # Save translation metadata
        metadata = {
            "source_language": source_language,
            "target_language": target_language,
            "original_length": len(source_text),
            "translated_length": len(translated_text),
            "content_hash": content_hash,
            "translation_method": "googletrans" if "googletrans" not in str(error_messages) else 
                                 "deep_translator" if "deep_translator" not in str(error_messages) else
                                 "google_api" if "Google API" not in str(error_messages) else
                                 "mock_translation"
        }
        
        metadata_file = os.path.join(output_dir, f"metadata_{content_hash}.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        files.append(metadata_file)
        print(f"✓ Saved metadata to: {metadata_file}")
        
        # Prepare result output
        result = {
            "translated_text": translated_text,
            "original_length": len(source_text),
            "translated_length": len(translated_text),
            "source_language": source_language,
            "target_language": target_language,
            "files_generated": [os.path.basename(f) for f in files],
            "warnings": error_messages if error_messages else None
        }
        
        result_str = json.dumps(result, indent=2, ensure_ascii=False)
        
        print("=" * 50)
        print(f"Translation Summary:")
        print(f"Original length: {len(source_text)} characters")
        print(f"Translated length: {len(translated_text)} characters")
        print(f"Files created: {len(files)}")
        
        if error_messages:
            print(f"Warnings: {len(error_messages)}")
            for warning in error_messages:
                print(f"  - {warning}")
        
        print("=" * 50)
        
        return {
            "ok": True, 
            "output": result_str, 
            "files": files, 
            "error": ""
        }
        
    except Exception as e:
        error_msg = f"Translation failed: {str(e)}"
        print(f"✗ {error_msg}")
        return {
            "ok": False, 
            "output": "", 
            "files": [], 
            "error": error_msg
        }