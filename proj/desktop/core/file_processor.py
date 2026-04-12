"""
File and document handling for chat attachments.
"""
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import zipfile
import io
from enum import Enum

try:
    from PIL import Image
    from pdf2image import convert_from_path
except ImportError:
    Image = None
    convert_from_path = None


class FileType(str, Enum):
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    PDF = "pdf"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    path: Path
    name: str
    size: int
    file_type: FileType
    mime_type: str
    content: Optional[str] = None
    preview: Optional[str] = None


class FileProcessor:
    """Process and extract content from various file types."""
    
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp", ".rs",
        ".go", ".rb", ".php", ".swift", ".kt", ".scala", ".sql", ".sh",
    }
    
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp", ".rs",
        ".go", ".rb", ".php", ".swift", ".kt", ".scala", ".sql", ".sh",
    }
    
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    
    ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".7z", ".rar"}
    
    DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"}
    
    MAX_TEXT_PREVIEW = 500
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    
    @staticmethod
    def get_file_type(file_path: Path) -> FileType:
        """Determine file type from extension."""
        suffix = file_path.suffix.lower()
        
        if suffix in FileProcessor.TEXT_EXTENSIONS:
            return FileType.CODE if suffix in FileProcessor.CODE_EXTENSIONS else FileType.TEXT
        elif suffix in FileProcessor.IMAGE_EXTENSIONS:
            return FileType.IMAGE
        elif suffix in FileProcessor.ARCHIVE_EXTENSIONS:
            return FileType.ARCHIVE
        elif suffix in FileProcessor.DOCUMENT_EXTENSIONS:
            return FileType.DOCUMENT
        else:
            return FileType.UNKNOWN
    
    @staticmethod
    def process_file(file_path: Path) -> FileInfo:
        """Process a file and extract its information."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.stat().st_size > FileProcessor.MAX_FILE_SIZE:
            raise ValueError(f"File too large (max {FileProcessor.MAX_FILE_SIZE / 1024 / 1024}MB)")
        
        file_type = FileProcessor.get_file_type(file_path)
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        
        info = FileInfo(
            path=file_path,
            name=file_path.name,
            size=file_path.stat().st_size,
            file_type=file_type,
            mime_type=mime_type,
        )
        
        # Extract content based on file type
        if file_type == FileType.TEXT or file_type == FileType.CODE:
            try:
                info.content = file_path.read_text(encoding="utf-8", errors="ignore")
                info.preview = info.content[:FileProcessor.MAX_TEXT_PREVIEW]
            except Exception:
                info.preview = "[Unable to read text file]"
        
        elif file_type == FileType.IMAGE:
            info.preview = f"[Image: {file_path.name}]"
        
        elif file_type == FileType.PDF:
            info.preview = f"[PDF document: {file_path.name}]"
        
        elif file_type == FileType.ARCHIVE:
            try:
                info.preview = FileProcessor._get_archive_contents(file_path)
            except Exception:
                info.preview = "[Unable to read archive]"
        
        elif file_type == FileType.DOCUMENT:
            info.preview = f"[Document: {file_path.name}]"
        
        return info
    
    @staticmethod
    def _get_archive_contents(file_path: Path) -> str:
        """Get contents listing of an archive."""
        try:
            if file_path.suffix.lower() == ".zip":
                with zipfile.ZipFile(file_path, 'r') as z:
                    files = z.namelist()[:20]  # First 20 files
                    return f"Archive contains {len(z.namelist())} files:\n" + "\n".join(files)
            else:
                return f"[Archive file: {file_path.name}]"
        except Exception as e:
            return f"[Error reading archive: {str(e)}]"
    
    @staticmethod
    def extract_text_from_file(file_path: Path) -> str:
        """Extract all text content from a file."""
        file_type = FileProcessor.get_file_type(file_path)
        
        if file_type == FileType.TEXT or file_type == FileType.CODE:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        
        elif file_type == FileType.IMAGE:
            return f"[Image: {file_path.name}]"
        
        elif file_type == FileType.PDF:
            try:
                if convert_from_path:
                    images = convert_from_path(str(file_path))
                    return f"[PDF with {len(images)} pages]"
            except Exception:
                pass
            return "[PDF document]"
        
        elif file_type == FileType.ARCHIVE:
            return FileProcessor._get_archive_contents(file_path)
        
        elif file_type == FileType.DOCUMENT:
            return f"[Document: {file_path.name}]"
        
        else:
            return f"[Binary file: {file_path.name}]"
    
    @staticmethod
    def extract_code_blocks(text: str, language: Optional[str] = None) -> List[str]:
        """Extract code blocks from text."""
        import re
        pattern = r"```(?:\w+)?\n(.*?)```"
        blocks = re.findall(pattern, text, re.DOTALL)
        return blocks


class FileAttachment:
    """Represents a file attachment in chat."""
    
    def __init__(self, file_path: str):
        self.path = Path(file_path)
        self.info = FileProcessor.process_file(self.path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.info.name,
            "type": self.info.file_type.value,
            "size": self.info.size,
            "mime_type": self.info.mime_type,
            "preview": self.info.preview,
            "path": str(self.path),
        }
    
    def get_content_for_context(self) -> str:
        """Get content suitable for including in LLM context."""
        if self.info.file_type == FileType.CODE:
            ext = self.path.suffix[1:]  # Remove leading dot
            return f"```{ext}\n{self.info.content}\n```"
        elif self.info.file_type == FileType.TEXT:
            return f"[{self.info.name}]\n{self.info.content}"
        else:
            return f"{self.info.preview}"
