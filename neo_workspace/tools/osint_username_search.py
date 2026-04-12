def run_tool(inputs: dict) -> dict:
    import os
    import sys
    import subprocess
    import json
    import time
    from pathlib import Path
    from urllib.parse import quote
    
    output_dir = inputs.get("output_dir", "/tmp")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def _dec(b):
        if not b: 
            return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try: 
                return b.decode(enc)
            except: 
                pass
        return b.decode("utf-8", errors="replace")
    
    def run_command(cmd, timeout=30):
        """Запускает команду и возвращает результат"""
        try:
            print(f"Выполняю команду: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
            return {
                "stdout": _dec(result.stdout),
                "stderr": _dec(result.stderr),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Таймаут команды", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}
    
    def install_package(package):
        """Устанавливает Python пакет"""
        print(f"Устанавливаю пакет: {package}")
        cmd = [sys.executable, "-m", "pip", "install", package, "-q", "--break-system-packages"]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0
    
    try:
        username = inputs.get("username", "").strip()
        if not username:
            return {"ok": False, "output": "Не указан username", "files": [], "error": "Не указан username"}
        
        print(f"Начинаю поиск информации по username: {username}")
        
        # Создаем файл для результатов
        timestamp = int(time.time())
        result_file = Path(output_dir) / f"osint_results_{username}_{timestamp}.txt"
        json_file = Path(output_dir) / f"osint_results_{username}_{timestamp}.json"
        
        results = {
            "username": username,
            "search_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sources": {},
            "summary": ""
        }
        
        output_lines = []
        output_lines.append(f"=== OSINT ПОИСК ПО USERNAME: {username} ===\n")
        output_lines.append(f"Время поиска: {results['search_time']}\n")
        
        # 1. Проверяем наличие sherlock
        print("Проверяю наличие инструмента sherlock...")
        sherlock_check = run_command("which sherlock")
        
        if sherlock_check["returncode"] != 0:
            print("Sherlock не найден, устанавливаю...")
            # Клонируем и устанавливаем sherlock
            clone_cmd = "git clone https://github.com/sherlock-project/sherlock.git /tmp/sherlock_install"
            run_command(clone_cmd, timeout=60)
            
            install_cmd = "cd /tmp/sherlock_install && pip install -q -r requirements.txt --break-system-packages"
            run_command(install_cmd, timeout=120)
            
            # Добавляем sherlock в PATH
            sherlock_path = "/tmp/sherlock_install/sherlock/sherlock.py"
        else:
            sherlock_path = "sherlock"
        
        # 2. Запускаем sherlock для поиска
        print(f"Запускаю sherlock для поиска {username}...")
        sherlock_cmd = f"python3 {sherlock_path} --timeout 10 --print-found {username}"
        sherlock_result = run_command(sherlock_cmd, timeout=120)
        
        if sherlock_result["stdout"]:
            results["sources"]["sherlock"] = sherlock_result["stdout"]
            output_lines.append("=== РЕЗУЛЬТАТЫ SHERLOCK ===")
            output_lines.append(sherlock_result["stdout"])
            output_lines.append("")
        
        # 3. Поиск через whatsmyname (если доступен)
        print("Проверяю наличие whatsmyname...")
        wmn_check = run_command("which whatsmyname")
        
        if wmn_check["returncode"] == 0:
            print(f"Запускаю whatsmyname для поиска {username}...")
            wmn_cmd = f"whatsmyname -u {username} -n"
            wmn_result = run_command(wmn_cmd, timeout=60)
            
            if wmn_result["stdout"]:
                results["sources"]["whatsmyname"] = wmn_result["stdout"]
                output_lines.append("=== РЕЗУЛЬТАТЫ WHATSMYNAME ===")
                output_lines.append(wmn_result["stdout"])
                output_lines.append("")
        
        # 4. Поиск через социальные сети (базовые проверки)
        print("Выполняю базовые проверки социальных сетей...")
        social_checks = []
        
        # GitHub
        print("Проверяю GitHub...")
        github_cmd = f"curl -s -L 'https://api.github.com/users/{username}'"
        github_result = run_command(github_cmd, timeout=15)
        
        if github_result["returncode"] == 0 and "login" in github_result["stdout"]:
            try:
                github_data = json.loads(github_result["stdout"])
                if github_data.get("login", "").lower() == username.lower():
                    social_checks.append(f"GitHub: https://github.com/{username} (найден)")
                    results["sources"]["github"] = f"https://github.com/{username}"
            except:
                pass
        
        # Twitter/X (базовая проверка)
        print("Проверяю Twitter/X...")
        twitter_url = f"https://twitter.com/{username}"
        twitter_cmd = f"curl -s -I -L '{twitter_url}' | head -n 5"
        twitter_result = run_command(twitter_cmd, timeout=15)
        
        if "200" in twitter_result["stdout"] or "301" in twitter_result["stdout"] or "302" in twitter_result["stdout"]:
            social_checks.append(f"Twitter/X: {twitter_url} (возможно существует)")
            results["sources"]["twitter"] = twitter_url
        
        # Instagram (базовая проверка)
        print("Проверяю Instagram...")
        instagram_url = f"https://instagram.com/{username}"
        instagram_cmd = f"curl -s -I -L '{instagram_url}' | head -n 5"
        instagram_result = run_command(instagram_cmd, timeout=15)
        
        if "200" in instagram_result["stdout"] or "301" in instagram_result["stdout"] or "302" in instagram_result["stdout"]:
            social_checks.append(f"Instagram: {instagram_url} (возможно существует)")
            results["sources"]["instagram"] = instagram_url
        
        # LinkedIn
        print("Проверяю LinkedIn...")
        linkedin_url = f"https://linkedin.com/in/{username}"
        linkedin_cmd = f"curl -s -I -L '{linkedin_url}' | head -n 5"
        linkedin_result = run_command(linkedin_cmd, timeout=15)
        
        if "200" in linkedin_result["stdout"] or "301" in linkedin_result["stdout"] or "302" in linkedin_result["stdout"]:
            social_checks.append(f"LinkedIn: {linkedin_url} (возможно существует)")
            results["sources"]["linkedin"] = linkedin_url
        
        if social_checks:
            output_lines.append("=== БАЗОВЫЕ ПРОВЕРКИ СОЦИАЛЬНЫХ СЕТЕЙ ===")
            for check in social_checks:
                output_lines.append(check)
            output_lines.append("")
        
        # 5. Поиск через поисковые системы (базовый)
        print("Выполняю поиск через поисковые системы...")
        search_queries = [
            f"site:github.com {username}",
            f"site:twitter.com {username}",
            f"site:instagram.com {username}",
            f"site:linkedin.com {username}",
            f"site:facebook.com {username}",
            f"site:vk.com {username}",
            f"site:reddit.com {username}",
            f"\"{username}\" social media"
        ]
        
        output_lines.append("=== РЕКОМЕНДУЕМЫЕ ПОИСКОВЫЕ ЗАПРОСЫ ===")
        for query in search_queries:
            encoded_query = quote(query)
            google_url = f"https://www.google.com/search?q={encoded_query}"
            duckduckgo_url = f"https://duckduckgo.com/?q={encoded_query}"
            output_lines.append(f"Запрос: {query}")
            output_lines.append(f"  Google: {google_url}")
            output_lines.append(f"  DuckDuckGo: {duckduckgo_url}")
            output_lines.append("")
        
        # 6. Создаем итоговый отчет
        found_count = 0
        if "sherlock" in results["sources"]:
            # Подсчитываем найденные сайты из вывода sherlock
            lines = results["sources"]["sherlock"].split('\n')
            for line in lines:
                if "[" in line and "]" in line and "http" in line:
                    found_count += 1
        
        summary = f"Поиск завершен. Найдено потенциальных совпадений: {found_count}"
        if social_checks:
            summary += f" + {len(social_checks)} социальных сетей"
        
        results["summary"] = summary
        output_lines.append(f"=== ИТОГ ===")
        output_lines.append(summary)
        output_lines.append(f"\nПодробные результаты сохранены в файлах:")
        output_lines.append(f"  Текстовый отчет: {result_file}")
        output_lines.append(f"  JSON отчет: {json_file}")
        
        # Сохраняем результаты в файлы
        final_output = "\n".join(output_lines)
        
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(final_output)
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Поиск завершен. Результаты сохранены в {result_file}")
        
        return {
            "ok": True,
            "output": final_output,
            "files": [str(result_file), str(json_file)],
            "error": ""
        }
        
    except Exception as e:
        error_msg = f"Ошибка при выполнении поиска: {str(e)}"
        print(error_msg)
        return {
            "ok": False,
            "output": error_msg,
            "files": [],
            "error": error_msg
        }