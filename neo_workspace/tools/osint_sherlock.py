def run_tool(inputs: dict) -> dict:
    import os, sys, subprocess, json, time, tempfile, shutil
    from pathlib import Path
    from datetime import datetime
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    def _dec(b):
        if not b: return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try: return b.decode(enc)
            except: pass
        return b.decode("utf-8", errors="replace")
    
    try:
        username = inputs.get("username", "").strip()
        if not username:
            return {"ok": False, "output": "Не указан username для поиска", "files": [], "error": "Не указан username для поиска"}
        
        print(f"Начинаем OSINT поиск по username: {username}")
        print("Проверяем наличие sherlock...")
        
        # Проверяем наличие sherlock
        sherlock_path = Path("/tmp/sherlock")
        
        if not sherlock_path.exists():
            print("Sherlock не найден, клонируем репозиторий...")
            r = subprocess.run(["git", "clone", "https://github.com/sherlock-project/sherlock.git", str(sherlock_path)],
                             capture_output=True, timeout=300)
            if r.returncode != 0:
                return {"ok": False, "output": f"Ошибка клонирования sherlock: {_dec(r.stderr)}", "files": [], "error": f"Ошибка клонирования sherlock: {_dec(r.stderr)}"}
            print("Sherlock успешно клонирован")
        
        # Проверяем зависимости
        requirements_file = sherlock_path / "requirements.txt"
        if requirements_file.exists():
            print("Устанавливаем зависимости sherlock...")
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q", "--break-system-packages"],
                             capture_output=True, timeout=180)
            if r.returncode != 0:
                print(f"Предупреждение при установке зависимостей: {_dec(r.stderr)}")
        
        # Создаем временный файл для результатов
        timestamp = int(time.time())
        results_file = Path(output_dir) / f"sherlock_results_{username}_{timestamp}.json"
        txt_file = Path(output_dir) / f"sherlock_results_{username}_{timestamp}.txt"
        
        print(f"Запускаем sherlock для username: {username}")
        print("Это может занять несколько минут...")
        
        # Запускаем sherlock
        cmd = [
            sys.executable, str(sherlock_path / "sherlock" / "sherlock.py"),
            "--timeout", "10",
            "--print-found",
            "--no-color",
            "--json", str(results_file),
            username
        ]
        
        r = subprocess.run(cmd, capture_output=True, timeout=600)
        
        output_lines = []
        output_lines.append(f"=== РАСШИРЕННЫЙ OSINT ПОИСК С SHERLOCK ===")
        output_lines.append(f"Цель: {username}")
        output_lines.append(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("")
        
        # Добавляем вывод sherlock
        if r.stdout:
            sherlock_output = _dec(r.stdout)
            output_lines.append("=== ВЫВОД SHERLOCK ===")
            output_lines.append(sherlock_output)
        
        # Читаем JSON результаты
        found_sites = []
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                if isinstance(results, dict) and username in results:
                    user_results = results[username]
                else:
                    user_results = results
                
                output_lines.append("")
                output_lines.append("=== НАЙДЕННЫЕ АККАУНТЫ ===")
                
                if isinstance(user_results, list) and len(user_results) > 0:
                    for site in user_results:
                        if isinstance(site, dict):
                            site_name = site.get("name", "Неизвестно")
                            url = site.get("url", "")
                            status = site.get("status", "")
                            
                            if status == "found":
                                found_sites.append({"name": site_name, "url": url})
                                output_lines.append(f"✓ {site_name}: {url}")
                            elif status == "error":
                                output_lines.append(f"✗ {site_name}: Ошибка проверки")
                            else:
                                output_lines.append(f"○ {site_name}: Не найден")
                else:
                    output_lines.append("Аккаунты не найдены")
                    
            except Exception as e:
                output_lines.append(f"Ошибка чтения результатов: {str(e)}")
        
        # Создаем текстовый отчет
        output_lines.append("")
        output_lines.append("=== СТАТИСТИКА ===")
        output_lines.append(f"Найдено аккаунтов: {len(found_sites)}")
        output_lines.append(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("")
        output_lines.append("=== РЕКОМЕНДАЦИИ ===")
        output_lines.append("1. Проверьте найденные аккаунты вручную")
        output_lines.append("2. Используйте дополнительные инструменты для анализа")
        output_lines.append("3. Сохраните результаты для дальнейшего исследования")
        
        # Сохраняем текстовый отчет
        txt_content = "\n".join(output_lines)
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        
        # Создаем сводный отчет в формате JSON
        summary_file = Path(output_dir) / f"sherlock_summary_{username}_{timestamp}.json"
        summary = {
            "username": username,
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "found_accounts": found_sites,
            "total_found": len(found_sites),
            "sherlock_output": _dec(r.stdout) if r.stdout else "",
            "sherlock_error": _dec(r.stderr) if r.stderr else ""
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Формируем итоговый вывод
        final_output = f"=== РАСШИРЕННЫЙ OSINT ПОИСК ЗАВЕРШЕН ===\n\n"
        final_output += f"Цель: {username}\n"
        final_output += f"Найдено аккаунтов: {len(found_sites)}\n\n"
        
        if found_sites:
            final_output += "НАЙДЕННЫЕ АККАУНТЫ:\n"
            for i, site in enumerate(found_sites, 1):
                final_output += f"{i}. {site['name']}: {site['url']}\n"
        else:
            final_output += "Аккаунты не найдены\n"
        
        final_output += f"\nПодробные результаты сохранены в файлах:\n"
        final_output += f"  Полный отчет: {txt_file}\n"
        final_output += f"  JSON результаты: {results_file}\n"
        final_output += f"  Сводный отчет: {summary_file}\n"
        
        print("Поиск завершен успешно")
        
        return {
            "ok": True,
            "output": final_output,
            "files": [str(txt_file), str(results_file), str(summary_file)],
            "error": ""
        }
        
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Таймаут выполнения поиска (слишком долго)", "files": [], "error": "Таймаут выполнения поиска"}
    except Exception as e:
        return {"ok": False, "output": f"Ошибка при выполнении поиска: {str(e)}", "files": [], "error": str(e)}