# BlackBugsAI - Quick Reference Guide

## ?? 5-Minute Quick Start

### 1. Install
```bash
# Windows quick-start
run.bat

# Or manually:
pip install -r requirements.txt
python main.py
```

### 2. Configure (Optional)
Create `.env`:
```ini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Use
1. Select AI Provider (OpenAI, Anthropic, Ollama, Local)
2. Type message
3. Attach files (optional)
4. Press Enter or click Send
5. Get streaming response

## ?? Command Reference

### Python
```bash
# Run application
python main.py

# Build EXE
pyinstaller build.spec

# Run tests
python test_all.py
python validate.py

# Quick test
python -c "from config import settings; print(settings.APP_NAME)"
```

### Windows Batch
```bash
# Quick start with setup
run.bat

# Create venv
python -m venv venv

# Activate venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Deactivate
deactivate
```

## ?? Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line |
| `Ctrl+N` | New chat |
| `Ctrl+1` | Chat tab |
| `Ctrl+2` | Code tab |
| `Ctrl+3` | Models tab |
| `Ctrl+,` | Settings |
| `Ctrl+Q` | Quit |

## ?? Chat Tips

### Prompt Format
```
<Your question>
[Optional: Attach files with ??]
[Optional: Reference specific lines from files]
```

### Example Prompts
```
"Analyze this Python file for bugs"
"Summarize this PDF document"
"Create a Python script to process this CSV"
"Fix the error in this code"
"Explain how this JavaScript works"
```

### File Attachments
```
Press ?? ? Select file ? Click send
Supported: PDF, DOCX, Code, Images, Archives
Max size: 100MB per file
```

## ?? AI Provider Matrix

| Provider | Speed | Cost | Best For | Needs Internet |
|----------|-------|------|----------|---|
| **OpenAI** | Very Fast | ~$0.01/1K tokens | General tasks | ? Yes |
| **Anthropic** | Fast | ~$0.01/1K tokens | Reasoning | ? Yes |
| **Ollama** | Local | Free | Development | ? No |
| **Local GGUF** | Local | Free | Privacy | ? No |

## ??? Common Tasks

### Task: Setup OpenAI
```
1. Get key: https://platform.openai.com/api-keys
2. Create .env: OPENAI_API_KEY=sk-...
3. Select OpenAI in app
4. Choose model (gpt-4, gpt-3.5-turbo)
5. Start chatting!
```

### Task: Setup Local Model
```
1. Download from Hugging Face
2. Create .env: LOCAL_MODEL_PATH=/path/model.gguf
3. Select "Local LLaMA" in app
4. Wait for model to load
5. Chat with local model (no internet needed!)
```

### Task: Setup Ollama
```
1. Download: https://ollama.ai
2. Run: ollama serve
3. Pull model: ollama pull mistral
4. Select "Ollama" in app
5. Choose available model
6. Chat!
```

### Task: Enable GPU Acceleration
```bash
# For NVIDIA CUDA (highly recommended!)
pip install llama-cpp-python --force-reinstall
# Set CMAKE_ARGS=-DLLAMA_CUDA=on before install

# For AMD ROCm
set CMAKE_ARGS=-DLLAMA_HIPBLAS=on
pip install llama-cpp-python --force-reinstall
```

### Task: Build EXE
```bash
pip install pyinstaller
pyinstaller build.spec
# Output: dist/BlackBugsAI/BlackBugsAI.exe
```

### Task: Debug Issues
```bash
# Run validation
python validate.py

# Check dependencies
pip list | grep -E "PySide|openai|anthropic"

# Run tests
python test_all.py

# Check logs
# .env file for debug mode: DEBUG=true
```

## ?? Settings Explained

### Chat Settings
- **Temperature** (0-2): 
  - 0 = Deterministic (always same answer)
  - 0.7 = Balanced (default)
  - 1.5+ = Creative/random
  
- **Max Tokens** (256-32768):
  - Higher = longer responses
  - Lower = faster responses
  - Typical: 1024-2048

### Model Settings
- **Provider**: Choose AI service
- **Model**: Specific model variant
- **System Prompt**: Behavior instruction

## ?? File Locations

| Item | Location |
|------|----------|
| Config | `.env` or `~/.blackbugsai/` |
| Chat History | `~/.blackbugsai/chats/` |
| Models | `~/.blackbugsai/models/` |
| Cache | `~/.blackbugsai/cache/` |
| Temp Files | `~/.blackbugsai/temp/` |

## ?? Troubleshooting

### "Module not found" error
```
Solution: pip install -r requirements.txt
```

### "API key invalid"
```
Solution 1: Check .env file
Solution 2: Get new key from provider
Solution 3: Restart app after changing .env
```

### "Model loading slow"
```
Solutions:
- Use GPU: CMAKE_ARGS="-DLLAMA_CUDA=on"
- Use smaller model (e.g., 7B instead of 70B)
- Reduce max tokens
```

### "Code execution errors"
```
Check:
1. Python/Node.js installed
2. Syntax is correct
3. No dangerous operations
4. Enough memory available
```

### App won't start
```
Try:
1. python validate.py (check setup)
2. Delete __pycache__ folder
3. Reinstall: pip install -r requirements.txt
4. Clear .env and use defaults
```

## ?? File Reference

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `config.py` | Global settings |
| `requirements.txt` | Python dependencies |
| `build.spec` | PyInstaller configuration |
| `.env` | API keys (not in repo) |
| `.env.example` | Template for .env |
| `README.md` | Project overview |
| `SETUP_GUIDE.md` | Installation guide |
| `FEATURES.md` | Feature documentation |
| `BUILD.md` | Build & deployment |

## ?? Customization

### Change Theme Color
Edit `ui/styles.py`:
```python
"accent_primary": "#58a6ff",  # Change to desired color
```

### Change Font Size
Edit stylesheet in relevant UI file

### Add Custom Provider
1. Create class in `core/ai_provider.py`
2. Implement `AIProvider` interface
3. Add to `ProviderFactory`

## ?? Performance Tips

### Faster Responses
- Use smaller model
- Reduce max tokens
- Lower temperature
- Enable GPU acceleration

### Lower Memory Usage
- Use quantized models (Q4, Q5)
- Reduce context window
- Close other applications

### Better Quality
- Use larger model
- Increase max tokens
- Higher temperature (but not too high)
- Better prompting technique

## ?? Security Checklist

- [ ] .env file created and filled
- [ ] API keys kept secret (not in git)
- [ ] No sharing of .env file
- [ ] Sandbox enabled for code execution
- [ ] Temp files cleaned up
- [ ] Recent chats archived if sensitive

## ?? API Server Usage

Enable in .env:
```ini
API_SERVER_ENABLED=true
API_SERVER_PORT=8765
```

Then use with OpenAI client:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8765/v1",
    api_key="local"
)

response = client.chat.completions.create(
    model="local",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## ?? Getting Help

1. Check **SETUP_GUIDE.md** for detailed help
2. Run `python validate.py` to diagnose issues
3. Check **FEATURES.md** for feature documentation
4. See **BUILD.md** for build issues
5. Review code comments for implementation details

## ?? Contact & Support

- GitHub Issues: Report bugs
- Discussions: Ask questions
- Wiki: Find more info
- Email: support@blackbugsai.com

---

**Last Updated**: 2024
**Version**: 1.0.0
**Status**: Production Ready ?
