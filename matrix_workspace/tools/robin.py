def run_tool(inputs: dict) -> dict:
    import os
    import sys
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
        # Путь к репозиторию
        repo_path = "/app/matrix_workspace/repos/robin"
        
        # Проверяем существование директории
        if not os.path.exists(repo_path):
            return {
                "ok": False,
                "output": f"Директория {repo_path} не найдена",
                "files": [],
                "error": f"Директория {repo_path} не найдена"
            }
        
        # Получаем аргументы CLI
        args = inputs.get("args", "")
        
        # Формируем команду
        cmd = ["python3", "."]
        if args:
            # Разбиваем строку аргументов на отдельные части
            import shlex
            cmd.extend(shlex.split(args))
        
        print(f"Запускаю команду: {' '.join(cmd)}")
        print(f"Рабочая директория: {repo_path}")
        
        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Получаем bytes для ручного декодирования
        )
        
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        # Декодируем вывод
        stdout_decoded = _dec(stdout)
        stderr_decoded = _dec(stderr)
        
        # Формируем полный вывод
        full_output = f"Код возврата: {return_code}\n\n"
        if stdout_decoded:
            full_output += f"STDOUT:\n{stdout_decoded}\n"
        if stderr_decoded:
            full_output += f"STDERR:\n{stderr_decoded}\n"
        
        # Определяем успешность выполнения
        ok_status = return_code == 0
        
        return {
            "ok": ok_status,
            "output": full_output,
            "files": [],
            "error": stderr_decoded if not ok_status else ""
        }
        
    except FileNotFoundError as e:
        return {
            "ok": False,
            "output": f"Файл или команда не найдены: {str(e)}",
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
            "output": f"Непредвиденная ошибка: {str(e)}",
            "files": [],
            "error": str(e)
        }