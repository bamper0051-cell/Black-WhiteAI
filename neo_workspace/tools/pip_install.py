def run_tool(inputs: dict) -> dict:
    import os, sys, subprocess
    from pathlib import Path
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    def _dec(b):
        if not b: return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try: return b.decode(enc)
            except: pass
        return b.decode("utf-8", errors="replace")
    
    try:
        # Получаем список пакетов для установки
        packages = inputs.get("packages", [])
        if not packages:
            return {"ok": False, "output": "Не указаны пакеты для установки", "files": [], "error": "No packages specified"}
        
        print(f"Начинаю установку {len(packages)} пакетов...")
        
        # Создаем список для хранения результатов установки
        results = []
        installed_packages = []
        failed_packages = []
        
        # Устанавливаем каждый пакет по отдельности для лучшего контроля
        for i, package in enumerate(packages):
            print(f"Устанавливаю пакет {i+1}/{len(packages)}: {package}")
            
            # Формируем команду pip install
            cmd = [sys.executable, "-m", "pip", "install", package, "-q", "--break-system-packages"]
            
            try:
                # Выполняем установку с таймаутом 120 секунд
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=120,
                    text=False  # Обрабатываем байты для декодирования
                )
                
                stdout = _dec(result.stdout)
                stderr = _dec(result.stderr)
                
                if result.returncode == 0:
                    results.append(f"✅ {package}: успешно установлен")
                    installed_packages.append(package)
                    
                    # Пытаемся получить версию установленного пакета
                    try:
                        version_cmd = [sys.executable, "-c", f"import {package.split('==')[0].split('>=')[0].split('<=')[0]}; print(getattr({package.split('==')[0].split('>=')[0].split('<=')[0]}, '__version__', 'версия не определена'))"]
                        version_result = subprocess.run(
                            version_cmd,
                            capture_output=True,
                            timeout=10,
                            text=False
                        )
                        version = _dec(version_result.stdout).strip()
                        if version:
                            results[-1] += f" (версия: {version})"
                    except:
                        pass
                else:
                    error_msg = stderr if stderr else stdout
                    results.append(f"❌ {package}: ошибка установки - {error_msg[:200]}")
                    failed_packages.append(package)
                    
            except subprocess.TimeoutExpired:
                results.append(f"❌ {package}: таймаут при установке (120 секунд)")
                failed_packages.append(package)
            except Exception as e:
                results.append(f"❌ {package}: исключение - {str(e)[:200]}")
                failed_packages.append(package)
        
        # Создаем сводный отчет
        summary = []
        summary.append(f"=== ОТЧЕТ ОБ УСТАНОВКЕ ===")
        summary.append(f"Всего пакетов: {len(packages)}")
        summary.append(f"Успешно установлено: {len(installed_packages)}")
        summary.append(f"Не удалось установить: {len(failed_packages)}")
        summary.append("")
        summary.append("Детали установки:")
        summary.extend(results)
        
        # Сохраняем отчет в файл
        report_file = Path(output_dir) / "pip_install_report.txt"
        report_content = "\n".join(summary)
        report_file.write_text(report_content, encoding="utf-8")
        
        # Формируем итоговый вывод
        output_lines = []
        output_lines.append(f"Установка завершена. Отчет сохранен в: {report_file}")
        output_lines.append(f"Успешно: {len(installed_packages)}/{len(packages)}")
        
        if failed_packages:
            output_lines.append(f"Не установлены: {', '.join(failed_packages)}")
        
        final_output = "\n".join(output_lines)
        
        # Проверяем общий результат
        ok = len(failed_packages) == 0
        
        return {
            "ok": ok,
            "output": final_output,
            "files": [str(report_file)],
            "error": "" if ok else f"Не удалось установить {len(failed_packages)} пакетов"
        }
        
    except Exception as e:
        error_msg = f"Критическая ошибка: {str(e)}"
        print(error_msg)
        return {"ok": False, "output": error_msg, "files": [], "error": error_msg}