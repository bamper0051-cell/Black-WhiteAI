def run_tool(inputs: dict) -> dict:
    import os
    import sys
    import subprocess
    import json
    import time
    from pathlib import Path
    from urllib.parse import urlparse
    
    output_dir = inputs.get("output_dir", "/tmp")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def _dec(b):
        if not b:
            return ""
        if isinstance(b, str):
            return b
        for enc in ("utf-8", "cp1251", "latin-1", "cp866"):
            try:
                return b.decode(enc)
            except:
                pass
        return b.decode("utf-8", errors="replace")
    
    def run_cmd(cmd, timeout=60, shell=True):
        """Запуск команды с обработкой ошибок"""
        try:
            print(f"Выполняю команду: {cmd}")
            result = subprocess.run(cmd, shell=shell, capture_output=True, timeout=timeout)
            return {
                "ok": result.returncode == 0,
                "stdout": _dec(result.stdout),
                "stderr": _dec(result.stderr),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "Таймаут", "returncode": -1}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}
    
    def install_package(package_name):
        """Установка пакета через pip"""
        print(f"Устанавливаю пакет: {package_name}")
        cmd = [sys.executable, "-m", "pip", "install", package_name, "-q", "--break-system-packages"]
        result = run_cmd(cmd, timeout=120, shell=False)
        return result["ok"]
    
    def safe_split(text, delimiter, maxsplit=1):
        """Безопасное разделение строки"""
        if delimiter not in text:
            return ["", ""]
        parts = text.split(delimiter, maxsplit)
        if len(parts) < 2:
            parts.append("")
        return parts
    
    try:
        site = inputs.get("site", "").strip()
        if not site:
            return {"ok": False, "output": "Не указан домен", "files": [], "error": "Не указан домен"}
        
        # Убираем протокол если есть
        if site.startswith(("http://", "https://")):
            site = urlparse(site).netloc
        
        print(f"Начинаю OSINT сбор информации для домена: {site}")
        
        # Подготовка имени файла для результатов
        timestamp = int(time.time())
        results_file = Path(output_dir) / f"osint_{site}_{timestamp}.json"
        report_file = Path(output_dir) / f"osint_report_{site}_{timestamp}.txt"
        
        results = {
            "domain": site,
            "timestamp": timestamp,
            "whois": {},
            "dns_records": {},
            "subdomains": [],
            "technologies": [],
            "security_headers": {},
            "ssl_certificate": {}
        }
        
        # 1. WHOIS информация
        print("Получаю WHOIS информацию...")
        whois_cmd = f"whois {site}"
        whois_result = run_cmd(whois_cmd, timeout=30)
        
        if whois_result["ok"] and whois_result["stdout"]:
            results["whois"]["raw"] = whois_result["stdout"]
            # Парсим основные поля
            whois_text = whois_result["stdout"].lower()
            
            # Безопасное извлечение данных
            if "registrar:" in whois_text:
                try:
                    registrar_line = whois_result["stdout"].split("Registrar:")[1].split("\n")[0].strip()
                    results["whois"]["registrar"] = registrar_line
                except:
                    results["whois"]["registrar"] = "Не удалось извлечь"
            
            if "creation date:" in whois_text:
                try:
                    creation_line = whois_result["stdout"].split("Creation Date:")[1].split("\n")[0].strip()
                    results["whois"]["creation_date"] = creation_line
                except:
                    results["whois"]["creation_date"] = "Не удалось извлечь"
            
            if "expiry date:" in whois_text:
                try:
                    expiry_line = whois_result["stdout"].split("Expiry Date:")[1].split("\n")[0].strip()
                    results["whois"]["expiry_date"] = expiry_line
                except:
                    results["whois"]["expiry_date"] = "Не удалось извлечь"
        else:
            results["whois"]["error"] = whois_result.get("stderr", "Не удалось получить WHOIS информацию")
        
        # 2. DNS записи
        print("Получаю DNS записи...")
        dns_commands = [
            f"dig A {site} +short",
            f"dig MX {site} +short",
            f"dig TXT {site} +short",
            f"dig NS {site} +short"
        ]
        
        for cmd in dns_commands:
            dns_result = run_cmd(cmd, timeout=20)
            if dns_result["ok"] and dns_result["stdout"].strip():
                record_type = cmd.split()[1]
                results["dns_records"][record_type] = dns_result["stdout"].strip()
        
        # 3. Поиск поддоменов
        print("Ищу поддомены...")
        
        # Проверяем наличие subfinder
        subfinder_check = run_cmd("which subfinder", timeout=10)
        if subfinder_check["ok"] and "subfinder" in subfinder_check["stdout"]:
            subfinder_cmd = f"subfinder -d {site} -silent"
            subfinder_result = run_cmd(subfinder_cmd, timeout=120)
            if subfinder_result["ok"] and subfinder_result["stdout"]:
                subdomains = [s.strip() for s in subfinder_result["stdout"].split("\n") if s.strip()]
                results["subdomains"] = subdomains
        else:
            # Альтернативный метод через curl и crt.sh
            print("Subfinder не найден, использую альтернативные методы...")
            crt_cmd = f"curl -s 'https://crt.sh/?q=%25.{site}&output=json'"
            crt_result = run_cmd(crt_cmd, timeout=30)
            if crt_result["ok"] and crt_result["stdout"]:
                try:
                    crt_data = json.loads(crt_result["stdout"])
                    subdomains_set = set()
                    for entry in crt_data:
                        if isinstance(entry, dict) and "name_value" in entry:
                            name_value = entry["name_value"]
                            if isinstance(name_value, str):
                                domains = name_value.split("\n")
                                for domain in domains:
                                    domain = domain.strip().lower()
                                    if domain.endswith(f".{site}") or domain == site:
                                        subdomains_set.add(domain)
                    results["subdomains"] = list(subdomains_set)
                except Exception as e:
                    print(f"Ошибка при парсинге crt.sh: {e}")
        
        # 4. Проверка SSL сертификата
        print("Проверяю SSL сертификат...")
        ssl_cmd = f"echo | timeout 10 openssl s_client -connect {site}:443 -servername {site} 2>/dev/null | openssl x509 -noout -text 2>/dev/null || true"
        ssl_result = run_cmd(ssl_cmd, timeout=30)
        if ssl_result["ok"] and ssl_result["stdout"]:
            results["ssl_certificate"]["raw"] = ssl_result["stdout"]
            # Извлекаем даты
            ssl_text = ssl_result["stdout"]
            if "Not Before" in ssl_text:
                try:
                    valid_from = ssl_text.split("Not Before:")[1].split("\n")[0].strip()
                    results["ssl_certificate"]["valid_from"] = valid_from
                except:
                    results["ssl_certificate"]["valid_from"] = "Не удалось извлечь"
            
            if "Not After" in ssl_text:
                try:
                    valid_until = ssl_text.split("Not After:")[1].split("\n")[0].strip()
                    results["ssl_certificate"]["valid_until"] = valid_until
                except:
                    results["ssl_certificate"]["valid_until"] = "Не удалось извлечь"
        
        # 5. Проверка HTTP заголовков
        print("Проверяю HTTP заголовки...")
        headers_cmd = f"curl -I -s -L --max-time 10 https://{site} 2>/dev/null || curl -I -s -L --max-time 10 http://{site} 2>/dev/null"
        headers_result = run_cmd(headers_cmd, timeout=30)
        
        if headers_result["ok"] and headers_result["stdout"]:
            security_headers = ["strict-transport-security", "content-security-policy", 
                              "x-frame-options", "x-content-type-options", "x-xss-protection"]
            
            for line in headers_result["stdout"].split("\n"):
                if ":" in line:
                    try:
                        header, value = safe_split(line, ":", 1)
                        header = header.strip().lower()
                        value = value.strip()
                        
                        if header in security_headers:
                            results["security_headers"][header] = value
                    except:
                        continue
        
        # 6. Определение технологий
        print("Определяю используемые технологии...")
        
        # Сначала проверяем whatweb
        whatweb_check = run_cmd("which whatweb", timeout=10)
        if whatweb_check["ok"] and "whatweb" in whatweb_check["stdout"]:
            whatweb_cmd = f"whatweb -a 3 {site} --color=never --no-errors"
            whatweb_result = run_cmd(whatweb_cmd, timeout=60)
            if whatweb_result["ok"] and whatweb_result["stdout"]:
                results["technologies"] = [line.strip() for line in whatweb_result["stdout"].split("\n") if line.strip()]
        else:
            # Альтернатива: используем curl для базового определения
            print("WhatWeb не найден, использую базовый анализ...")
            tech_cmd = f"curl -s -L --max-time 10 https://{site} 2>/dev/null | grep -i 'powered\\|framework\\|wordpress\\|drupal\\|joomla\\|react\\|angular\\|vue' | head -10"
            tech_result = run_cmd(tech_cmd, timeout=30)
            if tech_result["ok"] and tech_result["stdout"]:
                results["technologies"] = [line.strip() for line in tech_result["stdout"].split("\n") if line.strip()]
        
        # Сохраняем результаты в JSON
        print("Сохраняю результаты в JSON...")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Создаем текстовый отчет
        print("Формирую отчет...")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"OSINT ОТЧЕТ ДЛЯ: {site}\n")
            f.write(f"Дата сбора: {time.ctime(timestamp)}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("1. WHOIS ИНФОРМАЦИЯ:\n")
            f.write("-" * 40 + "\n")
            if results["whois"]:
                for key, value in results["whois"].items():
                    if key != "raw":
                        f.write(f"{key}: {value}\n")
            else:
                f.write("WHOIS информация не получена\n")
            f.write("\n")
            
            f.write("2. DNS ЗАПИСИ:\n")
            f.write("-" * 40 + "\n")
            if results["dns_records"]:
                for record_type, value in results["dns_records"].items():
                    f.write(f"{record_type} записи:\n{value}\n\n")
            else:
                f.write("DNS записи не получены\n")
            f.write("\n")
            
            f.write("3. ПОДДОМЕНЫ:\n")
            f.write("-" * 40 + "\n")
            if results["subdomains"]:
                for subdomain in sorted(results["subdomains"]):
                    f.write(f"  • {subdomain}\n")
            else:
                f.write("Поддомены не найдены\n")
            f.write("\n")
            
            f.write("4. SSL СЕРТИФИКАТ:\n")
            f.write("-" * 40 + "\n")
            if results["ssl_certificate"]:
                for key, value in results["ssl_certificate"].items():
                    if key != "raw":
                        f.write(f"{key}: {value}\n")
            else:
                f.write("SSL сертификат не проверен\n")
            f.write("\n")
            
            f.write("5. БЕЗОПАСНЫЕ ЗАГОЛОВКИ:\n")
            f.write("-" * 40 + "\n")
            if results["security_headers"]:
                for header, value in results["security_headers"].items():
                    f.write(f"{header}: {value}\n")
            else:
                f.write("Безопасные заголовки не обнаружены\n")
            f.write("\n")
            
            f.write("6. ОБНАРУЖЕННЫЕ ТЕХНОЛОГИИ:\n")
            f.write("-" * 40 + "\n")
            if results["technologies"]:
                for tech in results["technologies"][:20]:
                    f.write(f"  • {tech}\n")
            else:
                f.write("Технологии не определены\n")
        
        # Формируем краткий вывод
        summary = f"""
OSINT сбор завершен для: {site}

Найдено:
• Поддомены: {len(results['subdomains'])}
• DNS записей: {len(results['dns_records'])}
• Безопасных заголовков: {len(results['security_headers'])}
• SSL сертификат: {'Да' if results['ssl_certificate'].get('raw') else 'Нет'}

Файлы сохранены:
• JSON: {results_file}
• Отчет: {report_file}
"""
        
        print("OSINT сбор завершен успешно!")
        
        return {
            "ok": True,
            "output": summary.strip(),
            "files": [str(results_file), str(report_file)],
            "error": ""
        }
        
    except Exception as e:
        error_msg = f"Ошибка при выполнении OSINT сбора: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        return {
            "ok": False,
            "output": error_msg,
            "files": [],
            "error": error_msg
        }