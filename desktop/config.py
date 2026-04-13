"""
Global configuration and settings for BlackBugsAI.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "BlackBugsAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Paths
    DATA_DIR: Path = Path.home() / ".blackbugsai"
    MODELS_DIR: Path = DATA_DIR / "models"
    CHATS_DIR: Path = DATA_DIR / "chats"
    CACHE_DIR: Path = DATA_DIR / "cache"
    TEMP_DIR: Path = DATA_DIR / "temp"
    
    # API Keys (load from .env)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Local LLM settings
    ENABLE_LOCAL_LLM: bool = True
    LOCAL_MODEL_PATH: Optional[str] = None
    
    # Chat settings
    MAX_CONTEXT_LENGTH: int = 4096
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_EXTENSIONS: list = [
        "txt", "md", "pdf", "py", "js", "java", "cpp", "c", "h", "hpp",
        "json", "yaml", "yml", "xml", "html", "css", "sql",
        "png", "jpg", "jpeg", "gif", "webp",
        "docx", "doc", "xlsx", "xls", "pptx", "ppt",
        "zip", "tar", "gz", "7z", "rar"
    ]
    
    # Sandbox settings
    ENABLE_SANDBOX: bool = True
    SANDBOX_TIMEOUT: int = 30
    SANDBOX_MEMORY_LIMIT_MB: int = 512
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Create necessary directories
        for directory in [self.DATA_DIR, self.MODELS_DIR, self.CHATS_DIR, 
                         self.CACHE_DIR, self.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

settings = Settings()
