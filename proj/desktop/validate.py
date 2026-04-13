#!/usr/bin/env python3
"""
BlackBugsAI Installation & Setup Validator
Checks all dependencies and configurations before first run.
"""

import sys
import subprocess
from pathlib import Path
import importlib.util

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def check_python_version():
    print("? Checking Python version...")
    if sys.version_info >= (3, 10):
        print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} ?")
        return True
    else:
        print(f"  ? Python {sys.version_info.major}.{sys.version_info.minor} is too old")
        print("  ? Required: Python 3.10 or newer")
        return False

def check_module(module_name, display_name=None):
    display_name = display_name or module_name
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            print(f"  ? {display_name}")
            return True
        else:
            print(f"  ? {display_name} not found")
            return False
    except (ImportError, ModuleNotFoundError, ValueError):
        print(f"  ? {display_name} not installed")
        return False

def check_dependencies():
    print("? Checking dependencies...")
    
    dependencies = [
        # Core
        ("PySide6", "PySide6 (GUI Framework)"),
        ("pydantic", "Pydantic (Config)"),
        ("sqlalchemy", "SQLAlchemy (Database)"),
        
        # AI
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("llama_cpp", "llama-cpp-python"),
        
        # Web/API
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("httpx", "HTTPX"),
        
        # Utilities
        ("psutil", "PSUtil"),
        ("markdown", "Markdown"),
        ("pygments", "Pygments"),
        
        # File processing
        ("PIL", "Pillow (Images)"),
        ("docx", "python-docx (Word)"),
        ("PyPDF2", "PyPDF (PDF)"),
    ]
    
    installed = 0
    failed = []
    
    for module, display in dependencies:
        if check_module(module, display):
            installed += 1
        else:
            failed.append(display)
    
    print(f"\n  Summary: {installed}/{len(dependencies)} packages installed")
    
    if failed:
        print(f"\n  ? Missing packages:")
        for pkg in failed:
            print(f"    - {pkg}")
        print(f"\n  To install all dependencies:")
        print(f"    pip install -r requirements.txt")
        return False
    
    return True

def check_external_tools():
    print("? Checking external tools...")
    
    tools = [
        ("python", "Python"),
        ("node", "Node.js"),
        ("bash", "Bash/Shell"),
    ]
    
    found = 0
    for cmd, display in tools:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ? {display}")
                found += 1
            else:
                print(f"  ? {display} found but may not work correctly")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"  ? {display} not found (optional for sandboxing)")
    
    return found >= 1

def check_directories():
    print("? Checking directories...")
    
    dirs = [
        ("core", "Core modules"),
        ("ui", "UI modules"),
    ]
    
    all_ok = True
    for dir_name, display in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"  ? {display} ({dir_name}/)")
        else:
            print(f"  ? {display} ({dir_name}/) not found")
            all_ok = False
    
    return all_ok

def check_config_files():
    print("? Checking configuration files...")
    
    files = [
        ("config.py", "Configuration"),
        ("requirements.txt", "Requirements"),
        ("build.spec", "Build spec"),
        ("main.py", "Main entry point"),
    ]
    
    all_ok = True
    for file_name, display in files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ? {display} ({file_name})")
        else:
            print(f"  ? {display} ({file_name}) not found")
            all_ok = False
    
    return all_ok

def check_api_keys():
    print("? Checking API keys configuration...")
    
    env_file = Path(".env")
    if env_file.exists():
        print(f"  ? .env file exists")
        with open(env_file) as f:
            content = f.read()
            if "OPENAI_API_KEY" in content:
                print(f"    ? OpenAI key configured")
            if "ANTHROPIC_API_KEY" in content:
                print(f"    ? Anthropic key configured")
            if "OLLAMA" in content:
                print(f"    ? Ollama configured")
        return True
    else:
        print(f"  ? .env file not found")
        print(f"    Optional: Create .env with API keys for cloud providers")
        return True

def check_gpu_support():
    print("? Checking GPU support...")
    
    try:
        import torch
        if torch.cuda.is_available():
            device = torch.cuda.get_device_name(0)
            print(f"  ? CUDA GPU found: {device}")
            return True
        else:
            print(f"  ? CUDA not available (CPU mode only)")
            return False
    except ImportError:
        print(f"  ? PyTorch not installed (optional)")
        return False

def run_quick_tests():
    print("? Running quick component tests...")
    
    tests_ok = True
    
    # Test config
    try:
        from config import settings
        print(f"  ? Config: {settings.APP_NAME} v{settings.APP_VERSION}")
    except Exception as e:
        print(f"  ? Config: {e}")
        tests_ok = False
    
    # Test UI import
    try:
        from PySide6.QtWidgets import QApplication
        print(f"  ? PySide6 GUI framework")
    except Exception as e:
        print(f"  ? PySide6: {e}")
        tests_ok = False
    
    # Test sandbox
    try:
        from core.sandbox import run_code
        print(f"  ? Sandbox system")
    except Exception as e:
        print(f"  ? Sandbox: {e}")
        tests_ok = False
    
    # Test file processor
    try:
        from core.file_processor import FileProcessor
        print(f"  ? File processing")
    except Exception as e:
        print(f"  ? File processor: {e}")
        tests_ok = False
    
    return tests_ok

def main():
    print_header("BlackBugsAI Installation Validator")
    
    print("Performing system checks...\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("External Tools", check_external_tools),
        ("Project Structure", check_directories),
        ("Configuration Files", check_config_files),
        ("API Keys", check_api_keys),
        ("GPU Support", check_gpu_support),
        ("Component Tests", run_quick_tests),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ? Error: {e}\n")
            results.append((name, False))
    
    # Summary
    print_header("Validation Summary")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "? PASS" if result else "? FAIL"
        print(f"{status:8} {name}")
    
    print(f"\n{passed}/{total} checks passed\n")
    
    if passed == total:
        print("? All checks passed! Ready to run BlackBugsAI")
        print("\n  To start the application:")
        print("  - Development: python main.py")
        print("  - Quick start: run.bat (Windows)")
        print("  - Build EXE: pyinstaller build.spec")
        return 0
    else:
        print("? Some checks failed. Please fix issues before running.")
        print("\n  Common solutions:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Create .env file: copy .env.example .env")
        print("  - Check Python version: python --version")
        return 1

if __name__ == "__main__":
    sys.exit(main())
