# BlackBugsAI Desktop - Complete Setup Guide

**BlackBugsAI** is a professional, LM-Studio-like AI desktop application supporting multiple providers (OpenAI, Anthropic, Ollama, local GGUF models) with advanced chat, file attachment, and sandboxed code execution capabilities.

## ?? Features

### Core Features
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama, local llama-cpp (GGUF)
- **Modern Chat Interface**: Real-time message streaming with attachments
- **File Attachment System**: Support for documents, code, images, archives
- **Sandboxed Code Execution**: Safely run Python, JavaScript, and Bash code
- **AI Agent Tools**: File operations, code execution, system commands
- **Beautiful Dark Theme**: LM-Studio-inspired professional UI
- **Chat History**: Persistent conversation management with SQLite

### Advanced Features
- **Document Processing**: PDF, DOCX, images, and code files
- **Archive Support**: Read contents of ZIP, TAR, and other archives
- **Code Highlighting**: Syntax highlighting for 50+ languages
- **Telegram Integration**: Control the bot via Telegram
- **Local API Server**: OpenAI-compatible API endpoint
- **GPU Support**: CUDA acceleration for local models

## ?? Installation

### Prerequisites
- Windows 10/11
- Python 3.10+ or use pre-built EXE
- Node.js (optional, for JavaScript execution)

### Option 1: Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/BlackBugsAI.git
cd BlackBugsAI

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Option 2: Build EXE

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Build the EXE
pyinstaller build.spec

# The executable will be in dist/BlackBugsAI/BlackBugsAI.exe
```

### Option 3: Download Pre-built EXE
Visit the [Releases page](https://github.com/yourusername/BlackBugsAI/releases) to download the latest EXE.

## ?? Configuration

Create a `.env` file in the application directory to configure providers:

```ini
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Local model path
LOCAL_MODEL_PATH=/path/to/model.gguf

# Debug mode
DEBUG=false

# Sandbox settings
SANDBOX_TIMEOUT=30
SANDBOX_MEMORY_LIMIT_MB=512
```

## ?? Usage Guide

### Chat Interface

1. **Select Provider**: Choose from OpenAI, Anthropic, Ollama, or Local LLaMA
2. **Configure Parameters**:
   - Temperature: 0.0 (deterministic) to 2.0 (creative)
   - Max Tokens: Maximum response length
3. **Type Message**: Write your prompt in the input field
4. **Attach Files**: Click "?? Attach File" to include documents
5. **Send**: Press Enter or click Send button

### File Attachments

**Supported file types:**
- **Documents**: PDF, DOCX, XLSX, PPTX
- **Code**: Python, JavaScript, Java, C++, Rust, Go, etc.
- **Text**: TXT, MD, JSON, YAML, XML, HTML
- **Images**: PNG, JPG, GIF, WebP
- **Archives**: ZIP, TAR, 7Z, RAR

**How it works:**
1. Click "?? Attach File"
2. Select one or more files
3. Files are automatically included in the chat context
4. AI can reference and analyze file contents

### AI Tools/Toolchain

The AI agent has access to powerful tools:

#### Available Tools

**1. `file_read`** - Read file contents
```python
# Agent can read local files
```

**2. `file_write`** - Write to files
```python
# Agent can create and modify files
```

**3. `execute_python`** - Run Python code safely
```python
# Code runs in isolated sandbox with timeout
```

**4. `execute_bash`** - Run shell commands
```python
# Bash/Shell commands available
```

**5. `list_files`** - List directory contents
```python
# Explore file structure
```

### Code Execution

The application includes a **sandboxed code executor** for safety:

- **Timeout Protection**: 30-second limit (configurable)
- **Memory Limits**: 512MB limit (configurable)
- **Process Isolation**: Runs in subprocess with restricted permissions
- **Output Capture**: Captures stdout/stderr

**Dangerous operations blocked:**
- `os.system()`, `subprocess`, `shutil.rmtree()`
- Direct file writes to sensitive locations
- Socket/network operations
- `eval()`, `exec()` on untrusted code

### Conversation Management

**Create New Chat**:
- Click "? New Chat" or press Ctrl+N
- Starts fresh conversation with selected model

**Load Previous Chat**:
- Select from "Conversations" panel on left
- All history automatically loaded

**Delete Chat**:
- Right-click conversation ? Delete
- Or click "?? Delete Selected"

### Provider Setup

#### OpenAI
1. Get API key from [platform.openai.com](https://platform.openai.com)
2. Add to `.env`: `OPENAI_API_KEY=sk-...`
3. Select "OpenAI" from provider dropdown
4. Models: gpt-4, gpt-4-turbo, gpt-3.5-turbo

#### Anthropic
1. Get API key from [console.anthropic.com](https://console.anthropic.com)
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Select "Anthropic" from provider dropdown
4. Models: Claude 3 Opus, Sonnet, Haiku

#### Ollama (Local)
1. Download & install [Ollama](https://ollama.ai)
2. Run: `ollama serve`
3. Pull a model: `ollama pull mistral`
4. Select "Ollama" from provider dropdown

#### Local GGUF Models
1. Download model: [Hugging Face](https://huggingface.co)
2. Add path to `.env`: `LOCAL_MODEL_PATH=/path/to/model.gguf`
3. Select "Local LLaMA" from provider dropdown

### Local API Server

Run BlackBugsAI as an OpenAI-compatible API:

```bash
# Enable in settings or .env
API_SERVER_ENABLED=true
API_SERVER_PORT=8765
```

**Example usage:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8765/v1",
    api_key="local"
)

response = client.chat.completions.create(
    model="local",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)
```

### Telegram Integration

Control the bot via Telegram:

```bash
# Set in .env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_ENABLED=true
```

**Commands:**
- `/start` - Start the bot
- `/help` - Show help
- `<any message>` - Send to AI model

## ??? Architecture

```
BlackBugsAI/
??? main.py                 # Entry point
??? config.py              # Settings & config
??? requirements.txt       # Python dependencies
??? build.spec            # PyInstaller config
?
??? core/                 # Backend logic
?   ??? ai_provider.py   # Multi-provider abstraction
?   ??? sandbox.py       # Code execution & tools
?   ??? file_processor.py # File handling
?   ??? history.py       # Chat history (SQLite)
?   ??? llm_engine.py    # Local LLM inference
?   ??? api_server.py    # FastAPI endpoint
?   ??? telegram_bridge.py # Telegram bot
?
??? ui/                   # PySide6 UI
    ??? main_window.py   # Main application window
    ??? chat_widget.py   # Chat interface
    ??? code_editor.py   # Code editor
    ??? models_panel.py  # Model management
    ??? settings_dialog.py # Settings/configuration
    ??? styles.py        # Dark theme styling
```

## ?? Developer Guide

### Adding a New AI Provider

```python
# In core/ai_provider.py

class CustomProvider(AIProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
    
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        # Implement API call
        pass
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        **kwargs
    ) -> AsyncIterator[str]:
        # Implement streaming
        pass
    
    async def list_models(self) -> List[str]:
        # Return available models
        pass
```

### Adding a New Tool

```python
# In core/sandbox.py - ToolRegistry

def _setup_tools(self):
    self.register_tool(
        "custom_tool",
        "Description of what the tool does",
        {"param1": "str", "param2": "int"},
        self._tool_custom
    )

async def _tool_custom(self, param1: str, param2: int):
    # Implement tool logic
    return "result"
```

### Customizing the UI

Edit `ui/styles.py` to modify colors:

```python
COLORS = {
    "bg_primary": "#0d1117",
    "accent_primary": "#58a6ff",
    # ... more colors
}
```

## ?? Troubleshooting

### Models not loading
- Ensure model file path is correct
- Check file permissions
- Verify sufficient disk space

### Slow responses
- Reduce max tokens
- Decrease temperature
- Use faster model variant

### File attachment issues
- Check file size (max 100MB)
- Verify file type is supported
- Ensure read permissions

### Code execution errors
- Check Python/Node.js installation
- Verify code syntax
- Review sandbox output/errors

## ?? Performance Tips

1. **For Local Models**:
   - Use quantized GGUF models (Q4, Q5)
   - Enable GPU acceleration: `CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python`
   - Use smaller models for faster inference

2. **For API Providers**:
   - Use cheaper models for drafting (gpt-3.5, Claude Haiku)
   - Batch requests when possible
   - Monitor API usage in provider dashboard

3. **General**:
   - Adjust context window size
   - Use appropriate temperature settings
   - Cache frequently used files

## ?? License

MIT License - See LICENSE file

## ?? Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Submit pull request
4. Follow code style

## ?? Support

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions
- **Docs**: See full documentation on [Wiki](https://github.com/yourusername/BlackBugsAI/wiki)

## ?? Learning Resources

- [llama.cpp documentation](https://github.com/ggerganov/llama.cpp)
- [Ollama documentation](https://github.com/ollama/ollama)
- [OpenAI API docs](https://platform.openai.com/docs)
- [PySide6 documentation](https://doc.qt.io/qtforpython)
- [FastAPI documentation](https://fastapi.tiangolo.com)

---

**Made with ?? by BlackBugsAI Team**
