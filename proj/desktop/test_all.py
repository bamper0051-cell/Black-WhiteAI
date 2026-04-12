"""
Test script to verify all BlackBugsAI components are working.
Run: python test_all.py
"""
import asyncio
import sys
from pathlib import Path

# Test configuration
def test_config():
    print("? Testing configuration...")
    try:
        from config import settings
        print(f"  - App: {settings.APP_NAME} v{settings.APP_VERSION}")
        print(f"  - Data dir: {settings.DATA_DIR}")
        print(f"  - Sandbox enabled: {settings.ENABLE_SANDBOX}")
        print(f"  - Max file size: {settings.MAX_FILE_SIZE_MB}MB")
        return True
    except Exception as e:
        print(f"? Config error: {e}")
        return False


# Test sandbox
def test_sandbox():
    print("? Testing sandbox...")
    try:
        from core.sandbox import run_code
        
        # Python test
        result = run_code("print('Hello from sandbox!')", "python")
        assert result.success, f"Python execution failed: {result.error}"
        assert "Hello from sandbox!" in result.output
        print(f"  - Python: OK")
        
        return True
    except Exception as e:
        print(f"? Sandbox error: {e}")
        return False


# Test file processor
def test_file_processor():
    print("? Testing file processor...")
    try:
        from core.file_processor import FileProcessor, FileType
        
        # Create test file
        test_file = Path("test_file.txt")
        test_file.write_text("Hello, this is a test file!")
        
        # Process it
        info = FileProcessor.process_file(test_file)
        assert info.file_type == FileType.TEXT
        assert info.content is not None
        print(f"  - Text file processing: OK")
        
        # Cleanup
        test_file.unlink()
        
        return True
    except Exception as e:
        print(f"? File processor error: {e}")
        return False


# Test AI providers
async def test_providers():
    print("? Testing AI providers...")
    try:
        from core.ai_provider import ProviderFactory, ProviderType, Message
        
        # Test provider creation
        try:
            provider = ProviderFactory.create(ProviderType.OLLAMA)
            print(f"  - Ollama provider: Created")
            
            # Try to list models (may fail if Ollama not running)
            try:
                models = await provider.list_models()
                print(f"  - Ollama models: {models if models else 'None available'}")
            except Exception:
                print(f"  - Ollama models: Not available (service not running)")
        except Exception as e:
            print(f"  - Ollama provider: {e}")
        
        print(f"  - Provider abstraction: OK")
        return True
    except Exception as e:
        print(f"? Providers error: {e}")
        return False


# Test PySide6 UI (check imports only, don't create window)
def test_ui():
    print("? Testing UI components...")
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
        from ui.chat_widget import ChatWidget, MessageBubble
        from ui.styles import DARK_THEME
        
        print(f"  - Chat widget: Importable")
        print(f"  - Styles: Loaded ({len(DARK_THEME)} chars)")
        print(f"  - UI components: OK")
        return True
    except Exception as e:
        print(f"? UI error: {e}")
        return False


# Test tool registry
async def test_tools():
    print("? Testing AI tools/toolchain...")
    try:
        from core.sandbox import ToolRegistry
        
        registry = ToolRegistry()
        tools = registry.get_tools_schema()
        
        print(f"  - Tools registered: {len(tools)}")
        for tool in tools:
            print(f"    - {tool['function']['name']}: {tool['function']['description']}")
        
        return True
    except Exception as e:
        print(f"? Tools error: {e}")
        return False


# Run all tests
async def main():
    print("=" * 60)
    print("BlackBugsAI Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        ("Configuration", test_config),
        ("Sandbox", test_sandbox),
        ("File Processor", test_file_processor),
        ("UI Components", test_ui),
        ("AI Tools", test_tools),
        ("AI Providers", test_providers),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"? {name} failed: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "? PASS" if result else "? FAIL"
        print(f"{status:8} {name}")
    
    print(f"\n{passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
