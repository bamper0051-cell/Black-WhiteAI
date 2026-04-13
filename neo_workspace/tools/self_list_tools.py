def run_tool(inputs: dict) -> dict:
    import os, sys, subprocess, json, importlib, inspect, pkgutil
    from pathlib import Path
    from types import ModuleType
    output_dir = inputs.get("output_dir", "/tmp")
    
    def _dec(b):
        if not b: return ""
        for enc in ("utf-8", "cp1251", "latin-1"):
            try: return b.decode(enc)
            except: pass
        return b.decode("utf-8", errors="replace")
    
    def get_tool_info(func):
        """Извлечь информацию о функции инструмента"""
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            doc = inspect.getdoc(func) or ""
            return {
                "name": func.__name__,
                "params": params,
                "doc": doc[:200] + "..." if len(doc) > 200 else doc
            }
        except:
            return {"name": func.__name__, "params": [], "doc": ""}
    
    def safe_import_module(module_name):
        """Безопасный импорт модуля с установкой зависимостей при необходимости"""
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            # Пробуем установить модуль через pip
            print(f"⚠️  Модуль {module_name} не найден, пробую установить...")
            try:
                cmd = [sys.executable, "-m", "pip", "install", module_name, "-q", "--break-system-packages"]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0:
                    print(f"✅ Модуль {module_name} успешно установлен")
                    return importlib.import_module(module_name)
                else:
                    print(f"❌ Не удалось установить {module_name}: {_dec(result.stderr)}")
                    return None
            except Exception as install_error:
                print(f"❌ Ошибка при установке {module_name}: {str(install_error)}")
                return None
        except Exception as e:
            print(f"⚠️  Ошибка импорта {module_name}: {str(e)}")
            return None
    
    try:
        print("🔍 Начинаю поиск доступных инструментов...")
        
        # 1. Поиск встроенных инструментов (функции run_tool в текущем пространстве)
        builtin_tools = []
        
        # Проверяем глобальное пространство имен
        for name, obj in globals().items():
            if (callable(obj) and 
                hasattr(obj, '__name__') and 
                obj.__name__ == 'run_tool' and
                name != 'run_tool'):  # исключаем саму себя
                info = get_tool_info(obj)
                info["type"] = "builtin"
                builtin_tools.append(info)
                print(f"✅ Найден встроенный инструмент: {info['name']}")
        
        # 2. Поиск в установленных пакетах - ОГРАНИЧЕННЫЙ СПИСОК
        dynamic_tools = []
        scanned_modules = set()
        
        # Используем ограниченный список известных модулей для избежания timeout
        known_tool_modules = [
            "os", "sys", "json", "pathlib", "subprocess",
            "inspect", "importlib", "pkgutil", "types",
            "datetime", "re", "math", "random", "statistics"
        ]
        
        print(f"📦 Сканирую ограниченный список модулей ({len(known_tool_modules)} модулей)")
        
        for i, module_name in enumerate(known_tool_modules):
            try:
                if i % 10 == 0:  # Прогресс
                    print(f"📊 Прогресс: {i}/{len(known_tool_modules)} модулей")
                
                module = safe_import_module(module_name)
                if module is None:
                    continue
                    
                scanned_modules.add(module_name)
                
                # Ищем функции run_tool в модуле с таймаутом
                try:
                    for name in dir(module):
                        if name.startswith('_'): 
                            continue
                        
                        try:
                            obj = getattr(module, name)
                            if (callable(obj) and 
                                hasattr(obj, '__name__') and 
                                obj.__name__ == 'run_tool'):
                                
                                info = get_tool_info(obj)
                                info["type"] = "dynamic"
                                info["module"] = module_name
                                dynamic_tools.append(info)
                                print(f"✅ Найден динамический инструмент: {info['name']} из {module_name}")
                        except:
                            continue
                except Exception as scan_error:
                    print(f"⚠️  Ошибка сканирования {module_name}: {str(scan_error)}")
                    continue
                    
            except Exception as e:
                print(f"⚠️  Пропускаю модуль {module_name}: {str(e)}")
                continue
        
        # 3. Формируем результат
        result_lines = []
        result_lines.append("=" * 60)
        result_lines.append("📋 ДОСТУПНЫЕ ИНСТРУМЕНТЫ")
        result_lines.append("=" * 60)
        
        if builtin_tools:
            result_lines.append("\n🔧 ВСТРОЕННЫЕ ИНСТРУМЕНТЫ:")
            result_lines.append("-" * 40)
            for tool in builtin_tools:
                result_lines.append(f"• {tool['name']}")
                if tool['params']:
                    result_lines.append(f"  Параметры: {', '.join(tool['params'])}")
                if tool['doc']:
                    result_lines.append(f"  Описание: {tool['doc']}")
                result_lines.append("")
        
        if dynamic_tools:
            result_lines.append("\n⚡ ДИНАМИЧЕСКИЕ ИНСТРУМЕНТЫ:")
            result_lines.append("-" * 40)
            for tool in dynamic_tools:
                result_lines.append(f"• {tool['name']}")
                result_lines.append(f"  Модуль: {tool.get('module', 'unknown')}")
                if tool['params']:
                    result_lines.append(f"  Параметры: {', '.join(tool['params'])}")
                if tool['doc']:
                    result_lines.append(f"  Описание: {tool['doc']}")
                result_lines.append("")
        
        # Статистика
        result_lines.append("=" * 60)
        result_lines.append(f"📊 СТАТИСТИКА:")
        result_lines.append(f"• Встроенных инструментов: {len(builtin_tools)}")
        result_lines.append(f"• Динамических инструментов: {len(dynamic_tools)}")
        result_lines.append(f"• Всего: {len(builtin_tools) + len(dynamic_tools)}")
        result_lines.append(f"• Просканировано модулей: {len(scanned_modules)}")
        result_lines.append("=" * 60)
        
        result = "\n".join(result_lines)
        
        # 4. Сохраняем в файл
        output_file = Path(output_dir) / "available_tools.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"✅ Поиск завершен. Найдено {len(builtin_tools)} встроенных и {len(dynamic_tools)} динамических инструментов")
        print(f"📄 Результат сохранен в: {output_file}")
        
        return {
            "ok": True, 
            "output": result, 
            "files": [str(output_file)], 
            "error": ""
        }
        
    except Exception as e:
        error_msg = f"❌ Ошибка при поиске инструментов: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "ok": False, 
            "output": error_msg, 
            "files": [], 
            "error": str(e)
        }