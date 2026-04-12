def run_tool(inputs: dict) -> dict:
    import os
    import sys
    import subprocess
    from pathlib import Path
    import shutil
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    def _dec(b):
        if not b:
            return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try:
                return b.decode(enc)
            except:
                pass
        return b.decode("utf-8", errors="replace")
    
    try:
        # Получаем URL репозитория
        repo_url = inputs.get("url", "https://github.com/sherlock-project/sherlock")
        tool_name = inputs.get("tool_name", "sherlock")
        args = inputs.get("args", "")
        
        print(f"🔄 Начинаю установку {tool_name} из {repo_url}")
        
        # Создаем директорию для инструмента
        tool_dir = Path(output_dir) / tool_name
        if tool_dir.exists():
            print(f"⚠️ Директория {tool_dir} уже существует, удаляю...")
            shutil.rmtree(tool_dir)
        
        # 1. Клонируем репозиторий
        print(f"📥 Клонирую репозиторий {repo_url}...")
        clone_cmd = ["git", "clone", "--depth=1", repo_url, str(tool_dir)]
        result = subprocess.run(clone_cmd, capture_output=True, timeout=300)
        
        if result.returncode != 0:
            return {
                "ok": False,
                "output": f"Ошибка клонирования: {_dec(result.stderr)}",
                "files": [],
                "error": f"Git clone failed with code {result.returncode}"
            }
        
        print("✅ Репозиторий успешно клонирован")
        
        # 2. Проверяем наличие requirements.txt и устанавливаем зависимости
        requirements_file = tool_dir / "requirements.txt"
        if requirements_file.exists():
            print("📦 Найден requirements.txt, устанавливаю зависимости...")
            install_cmd = [
                sys.executable, "-m", "pip", "install", "-r",
                str(requirements_file), "-q", "--break-system-packages"
            ]
            result = subprocess.run(install_cmd, capture_output=True, timeout=300)
            
            if result.returncode != 0:
                print(f"⚠️ Предупреждение при установке зависимостей: {_dec(result.stderr)}")
            else:
                print("✅ Зависимости успешно установлены")
        
        # 3. Ищем точку входа - УЛУЧШЕННЫЙ ПОИСК
        print("🔍 Ищу точку входа...")
        
        # Сначала ищем setup.py или pyproject.toml для определения точки входа
        entry_file = None
        setup_file = tool_dir / "setup.py"
        pyproject_file = tool_dir / "pyproject.toml"
        
        # Проверяем, есть ли специальные файлы для sherlock
        sherlock_files = ["sherlock.py", "sherlock/sherlock.py"]
        for sf in sherlock_files:
            sf_path = tool_dir / sf
            if sf_path.exists():
                entry_file = sf_path
                print(f"✅ Найден специальный файл: {sf}")
                break
        
        # Если не нашли специальные файлы, ищем стандартные точки входа
        if entry_file is None:
            entry_points = ["main.py", "app.py", "cli.py", "tool.py", "__main__.py", "run.py"]
            for ep in entry_points:
                ep_path = tool_dir / ep
                if ep_path.exists():
                    entry_file = ep_path
                    print(f"✅ Найден стандартный файл: {ep}")
                    break
        
        # Если все еще не нашли, ищем любые .py файлы в корне
        if entry_file is None:
            py_files = list(tool_dir.glob("*.py"))
            if py_files:
                # Сортируем по приоритету: main, run, cli в названии
                priority_files = []
                other_files = []
                
                for py_file in py_files:
                    name_lower = py_file.name.lower()
                    if "main" in name_lower or "run" in name_lower or "cli" in name_lower:
                        priority_files.append(py_file)
                    else:
                        other_files.append(py_file)
                
                if priority_files:
                    entry_file = priority_files[0]
                    print(f"✅ Найден файл с ключевым словом: {entry_file.name}")
                else:
                    entry_file = other_files[0]
                    print(f"✅ Найден первый .py файл: {entry_file.name}")
        
        # Если все еще не нашли, ищем в поддиректориях
        if entry_file is None:
            all_py_files = list(tool_dir.rglob("*.py"))
            if all_py_files:
                # Ищем файлы с main или run в названии
                for py_file in all_py_files:
                    name_lower = py_file.name.lower()
                    if "main" in name_lower or "run" in name_lower or "cli" in name_lower:
                        entry_file = py_file
                        print(f"✅ Найден файл в поддиректории: {py_file.relative_to(tool_dir)}")
                        break
                
                if entry_file is None:
                    entry_file = all_py_files[0]
                    print(f"✅ Найден первый .py файл в поддиректориях: {entry_file.relative_to(tool_dir)}")
        
        if entry_file is None:
            # Покажем содержимое директории для отладки
            print("📁 Содержимое директории:")
            for item in tool_dir.rglob("*"):
                print(f"  {item.relative_to(tool_dir)}")
            
            return {
                "ok": False,
                "output": "Не найден файл для запуска (.py файл). Проверьте содержимое репозитория выше.",
                "files": [],
                "error": "No Python entry point found"
            }
        
        print(f"🎯 Точка входа найдена: {entry_file}")
        
        # 4. Устанавливаем зависимости из setup.py если есть
        if setup_file.exists():
            print("📦 Найден setup.py, устанавливаю пакет...")
            try:
                install_cmd = [
                    sys.executable, "-m", "pip", "install", "-e",
                    str(tool_dir), "-q", "--break-system-packages"
                ]
                result = subprocess.run(install_cmd, capture_output=True, timeout=300)
                if result.returncode == 0:
                    print("✅ Пакет успешно установлен")
                else:
                    print(f"⚠️ Предупреждение при установке пакета: {_dec(result.stderr)}")
            except Exception as e:
                print(f"⚠️ Ошибка при установке пакета: {e}")
        
        # 5. Запускаем инструмент с аргументами
        print(f"🚀 Запускаю {entry_file.name} с аргументами: {args}")
        
        # Разбиваем аргументы на список
        if args:
            arg_list = args.split()
        else:
            arg_list = []
        
        # Для sherlock обычно нужен username, если аргументов нет - покажем help
        if not arg_list:
            arg_list = ["--help"]
            print("ℹ️ Аргументы не указаны, показываю справку...")
        
        # Определяем рабочую директорию (там где находится entry_file)
        cwd_dir = entry_file.parent
        
        run_cmd = [sys.executable, str(entry_file)] + arg_list
        print(f"💻 Команда: {' '.join(run_cmd)}")
        print(f"📂 Рабочая директория: {cwd_dir}")
        
        result = subprocess.run(run_cmd, capture_output=True, timeout=600, cwd=cwd_dir)
        
        output_text = ""
        if result.stdout:
            stdout_text = _dec(result.stdout)
            output_text += stdout_text
            print(f"📤 STDOUT (первые 500 символов): {stdout_text[:500]}...")
        
        if result.stderr:
            stderr_text = _dec(result.stderr)
            output_text += "\n\nSTDERR:\n" + stderr_text
            print(f"📥 STDERR (первые 500 символов): {stderr_text[:500]}...")
        
        # 6. Проверяем на ошибку импорта модуля
        if "ModuleNotFoundError" in output_text or "ImportError" in output_text:
            print("⚠️ Обнаружена ошибка импорта, пытаюсь установить недостающие модули...")
            # Пытаемся извлечь имя модуля из ошибки
            import re
            module_match = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", output_text)
            if module_match:
                missing_module = module_match.group(1)
                print(f"📦 Устанавливаю недостающий модуль: {missing_module}")
                install_cmd = [
                    sys.executable, "-m", "pip", "install", missing_module,
                    "-q", "--break-system-packages"
                ]
                result_install = subprocess.run(install_cmd, capture_output=True, timeout=300)
                if result_install.returncode == 0:
                    print(f"✅ Модуль {missing_module} успешно установлен")
                    # Пробуем запустить снова
                    print("🔄 Повторный запуск после установки модуля...")
                    result = subprocess.run(run_cmd, capture_output=True, timeout=600, cwd=cwd_dir)
                    output_text = _dec(result.stdout) + "\n\nSTDERR:\n" + _dec(result.stderr)
        
        # 7. Создаем файл с результатами
        result_file = Path(output_dir) / f"{tool_name}_results.txt"
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(f"Команда: {' '.join(run_cmd)}\n")
            f.write(f"Рабочая директория: {cwd_dir}\n")
            f.write(f"Код возврата: {result.returncode}\n")
            f.write("=" * 50 + "\n")
            f.write(output_text)
        
        print(f"✅ Выполнение завершено с кодом {result.returncode}")
        
        return {
            "ok": result.returncode == 0 or "--help" in arg_list,
            "output": output_text,
            "files": [str(result_file)],
            "error": "" if result.returncode == 0 else f"Exit code: {result.returncode}"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "output": "Таймаут выполнения операции (увеличьте timeout если нужно)",
            "files": [],
            "error": "Operation timeout"
        }
    except Exception as e:
        return {
            "ok": False,
            "output": f"Ошибка: {str(e)}",
            "files": [],
            "error": str(e)
        }