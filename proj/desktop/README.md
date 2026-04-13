# ?? BlackBugsAI Desktop

**Professional AI Desktop Application** - LM-Studio-like interface with multi-provider support, file attachments, sandboxed code execution, and an intelligent AI toolchain.

> Built with Python, PySide6, and modern AI/ML technologies. Single-file executable for Windows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4.svg)](https://www.microsoft.com/windows)

## ? Key Features

### ?? Multi-Provider AI
- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude 3)
- **Ollama** (Local models)
- **Local GGUF** (llama.cpp with GPU support)

### ?? Advanced Chat
- Real-time streaming responses
- Markdown formatting with syntax highlighting
- Persistent conversation history
- Search and export chats

### ?? File Attachments
- **30+ file types** supported
- Code, documents, images, archives
- AI can analyze and manipulate files
- Smart file preview system

### ??? AI Toolchain
- **Sandboxed code execution** (Python, JavaScript, Bash)
- **File operations** (read, write, list)
- **System tools** (check ports, file sizes)
- Timeout & memory protection

### ?? Local API Server
- OpenAI-compatible REST API
- Self-host your AI models
- Perfect for integrations

### ?? Security & Privacy
- All data stays on your machine
- Encrypted API key storage
- Sandboxed code execution
- No telemetry or tracking

## ?? Quick Start

### Option 1: Run from Source (Recommended for Development)

```bash
# Clone repository
git clone https://github.com/yourusername/BlackBugsAI.git
cd BlackBugsAI

# Run setup script (Windows)
run.bat

# Or manual setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Option 2: Download Pre-built EXE

Download the latest version from [Releases](https://github.com/yourusername/BlackBugsAI/releases)

```bash
# Extract and run
BlackBugsAI.exe
```

### Option 3: Build Your Own

```bash
# Install PyInstaller
pip install pyinstaller

# Build EXE
pyinstaller build.spec

# Run from dist/
dist\BlackBugsAI\BlackBugsAI.exe
```

## ?? Setup

### 1. Get API Keys (Optional)

**OpenAI:**
```bash
# Get key from https://platform.openai.com
# Add to .env file
OPENAI_API_KEY=sk-...
```

**Anthropic:**
```bash
# Get key from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Setup Local Models (Optional)

**Ollama:**
```bash
# Download from https://ollama.ai
# Run Ollama, then pull a model
ollama pull mistral
# BlackBugsAI will auto-detect available models
```

**Local GGUF:**
```bash
# Download model from Hugging Face
# Add path to .env
LOCAL_MODEL_PATH=C:\Models\mistral-7b.gguf
```

### 3. GPU Support (Optional)

```bash
# For NVIDIA CUDA (highly recommended!)
pip install llama-cpp-python --force-reinstall --no-cache-dir
# Set CMAKE_ARGS=-DLLAMA_CUDA=on before running pip install

# For AMD ROCm
set CMAKE_ARGS=-DLLAMA_HIPBLAS=on
pip install llama-cpp-python --force-reinstall
```

## ?? Usage

### Chat Interface

1. **Select AI Provider** - OpenAI, Anthropic, Ollama, or Local
2. **Adjust Settings** - Temperature, max tokens, model
3. **Type Message** - Write your prompt
4. **Attach Files** (Optional) - Click ?? to add documents/code
5. **Send** - Press Enter or click Send button
6. **Get Response** - AI responds with streaming output

### File Attachments

Supported: PDF, DOCX, Code files, Images, Archives, and 25+ more formats

```
Drag & drop or click ?? Attach File
AI automatically includes file context in responses
Works with archives - AI reads contents
```

### Code Execution

AI can safely execute code in sandbox:

```python
# AI Agent can run code safely
result = execute_python("print('Hello')")  # Safe - isolated execution
result = execute_bash("ls -la")             # Shell commands OK
```

### AI Tools Available to Agents

- `file_read` - Read file contents
- `file_write` - Create/modify files  
- `execute_python` - Run Python code
- `execute_bash` - Run shell commands
- `list_files` - List directory

## ??? Architecture

```
BlackBugsAI/
??? main.py                    # Application entry point
??? config.py                  # Configuration management
??? requirements.txt           # Python dependencies
??? build.spec                 # PyInstaller configuration
??? run.bat                    # Windows quick-start script
??? test_all.py               # Full test suite
?
??? core/                      # Backend logic
?   ??? ai_provider.py        # Multi-provider abstraction
?   ??? sandbox.py            # Code execution & tools
?   ??? file_processor.py     # File handling
?   ??? history.py            # Chat history DB
?   ??? llm_engine.py         # Local LLM inference
?   ??? api_server.py         # REST API server
?   ??? telegram_bridge.py    # Telegram bot
?
??? ui/                        # PySide6 GUI
    ??? main_window.py        # Main application window
    ??? chat_widget.py        # Chat interface
    ??? code_editor.py        # Code editor panel
    ??? models_panel.py       # Model management
    ??? settings_dialog.py    # Settings dialog
    ??? styles.py             # Dark theme CSS
```

## ?? Use Cases

### 1. **Code Analysis & Debugging**
```
Attach problematic code ? AI analyzes ? Suggests fixes
Can execute test cases to verify solutions
```

### 2. **Document Review**
```
Attach PDF/DOCX ? AI reviews ? Provides summary & insights
Great for contracts, research papers, reports
```

### 3. **Data Processing**
```
Attach CSV/data files ? AI writes processing script
Executes in sandbox ? Returns results
```

### 4. **Learning & Teaching**
```
Attach tutorial/course material ? AI explains
Interactive learning with code execution
```

### 5. **Content Creation**
```
Provide outlines ? AI generates content
Analyze and improve existing content
```

## ?? Configuration

Create `.env` file in application directory:

```ini
# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_MODEL_PATH=C:\Models\model.gguf

# Sandbox
SANDBOX_TIMEOUT=30
SANDBOX_MEMORY_LIMIT_MB=512

# API Server
API_SERVER_ENABLED=false
API_SERVER_PORT=8765

# Telegram
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=...

# Debug
DEBUG=false
```

## ?? System Requirements

| Requirement | Minimum | Recommended | Optimal |
|------------|---------|-------------|---------|
| OS | Windows 10 | Windows 11 | Windows 11 |
| RAM | 4GB | 16GB | 32GB |
| CPU | Any modern | Multi-core | High-end |
| GPU | None | GTX 1080 | RTX 4090 |
| Disk | 500MB | 10GB | 50GB |
| Internet | Optional | For APIs | Required for cloud APIs |

## ?? Testing

Run the comprehensive test suite:

```bash
python test_all.py
```

Tests include:
- Configuration loading
- Sandbox execution
- File processing
- UI components
- AI providers
- Tool registry

## ?? Deployment

### Windows Installer

```bash
# Download NSIS from https://nsis.sourceforge.io/
# Build installer
makensis installer.nsi
```

### Portable ZIP

```bash
# Create portable version
pyinstaller build.spec
Compress-Archive -Path dist\BlackBugsAI -DestinationPath BlackBugsAI-portable.zip
```

### CI/CD (GitHub Actions)

Automated builds on every release tag. See `.github/workflows/build.yml`

## ?? Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## ?? Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Detailed installation & configuration
- **[Features Reference](FEATURES.md)** - Complete feature list & API
- **[Build Guide](BUILD.md)** - Building EXE & deployment
- **[Contributing](CONTRIBUTING.md)** - Developer guide

## ?? Troubleshooting

### Q: Models not loading?
A: Check file path, ensure sufficient disk space, verify permissions

### Q: Slow responses?
A: Reduce max tokens, use smaller model, enable GPU acceleration

### Q: File attachment issues?
A: Check file size (<100MB), verify supported format, review logs

### Q: Code execution errors?
A: Ensure Python/Node.js installed, check code syntax, review sandbox output

See [Troubleshooting Guide](SETUP_GUIDE.md#troubleshooting) for more.

## ?? Performance

### Local Model Performance (RTX 4090)

| Model | Speed | Memory | Quality |
|-------|-------|--------|---------|
| Mistral 7B | 150 tokens/s | 3.5GB | Good |
| Llama 2 13B | 80 tokens/s | 7GB | Better |
| Dolphin 70B | 40 tokens/s | 33GB | Excellent |

### Cloud API Performance

| Provider | Speed | Latency | Cost |
|----------|-------|---------|------|
| OpenAI | Very Fast | 2-5s | ~$0.01/1K |
| Anthropic | Fast | 3-8s | ~$0.01/1K |
| Ollama | Local | <500ms | Free |

## ?? Roadmap

- [ ] Web UI version
- [ ] Multi-user support
- [ ] Plugin system
- [ ] Custom provider templates
- [ ] Voice input/output
- [ ] Real-time collaboration
- [ ] Mobile app (iOS/Android)
- [ ] Advanced RAG/knowledge base

## ?? License

MIT License - see [LICENSE](LICENSE) file for details

## ?? Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Local LLM inference
- [Ollama](https://ollama.ai) - Easy model deployment
- [PySide6](https://www.qt.io) - Desktop UI framework
- [FastAPI](https://fastapi.tiangolo.com) - REST API framework
- All open-source contributors and the community

## ?? Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/BlackBugsAI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/BlackBugsAI/discussions)
- **Email**: support@blackbugsai.com
- **Twitter**: [@BlackBugsAI](https://twitter.com/BlackBugsAI)
- **Discord**: [Join Community](https://discord.gg/blackbugsai)

## ?? Learning Resources

- [Getting Started Guide](SETUP_GUIDE.md)
- [Features & API Reference](FEATURES.md)
- [Build & Deployment](BUILD.md)
- [llama.cpp Docs](https://github.com/ggerganov/llama.cpp)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [PySide6 Documentation](https://doc.qt.io/qtforpython)

---

**Made with ?? by BlackBugsAI Team**

*Last Updated: 2024*
