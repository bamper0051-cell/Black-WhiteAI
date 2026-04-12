def run_tool(inputs: dict) -> dict:
    import os
    import subprocess
    from pathlib import Path
    
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
        # 1. Определяем путь к репозиторию RED_HAWK
        repo_path = "/app/matrix_workspace/repos/red_hawk"
        
        # Проверяем существование директории
        if not os.path.exists(repo_path):
            return {
                "ok": False,
                "output": f"Директория RED_HAWK не найдена: {repo_path}",
                "files": [],
                "error": f"Directory not found: {repo_path}"
            }
        
        # 2. Получаем аргументы CLI из inputs
        args = inputs.get("args", "")
        
        # 3. Формируем команду для запуска
        cmd = f"python3 . {args}".strip()
        
        print(f"Запускаю RED_HAWK в директории: {repo_path}")
        print(f"Команда: {cmd}")
        
        # 4. Запускаем subprocess в указанной директории
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        # 5. Декодируем вывод с fallback кодировками
        output = _dec(stdout)
        error_output = _dec(stderr)
        
        # 6. Формируем результат
        result = ""
        if output:
            result += f"STDOUT:\n{output}\n"
        if error_output:
            result += f"STDERR:\n{error_output}\n"
        
        return_code = process.returncode
        result += f"\nКод завершения: {return_code}"
        
        if return_code == 0:
            return {
                "ok": True,
                "output": result,
                "files": [],
                "error": ""
            }
        else:
            return {
                "ok": False,
                "output": result,
                "files": [],
                "error": f"RED_HAWK завершился с кодом {return_code}"
            }
            
    except FileNotFoundError as e:
        return {
            "ok": False,
            "output": f"Ошибка: файл или команда не найдены - {str(e)}",
            "files": [],
            "error": f"FileNotFoundError: {str(e)}"
        }
    except PermissionError as e:
        return {
            "ok": False,
            "output": f"Ошибка прав доступа: {str(e)}",
            "files": [],
            "error": f"PermissionError: {str(e)}"
        }
    except Exception as e:
        return {
            "ok": False,
            "output": f"Неожиданная ошибка: {str(e)}",
            "files": [],
            "error": str(e)
        }