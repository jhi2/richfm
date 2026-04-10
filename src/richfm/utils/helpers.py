"""Utility functions for RichFM."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def is_safe_path(base_path: Path, user_path: str) -> bool:
    """Check if the user path is safe (no path traversal)."""
    normalized = os.path.normpath(user_path)

    if ".." in normalized.split(os.sep):
        return False

    if normalized == "." or normalized == "":
        return True

    try:
        if normalized.startswith("/"):
            normalized = normalized[1:]
        resolved = (base_path / normalized).resolve()
        return resolved.is_relative_to(base_path)
    except (ValueError, OSError):
        return False


def translate_path(base_path: Path, virtual_path: str) -> Path:
    """Translate virtual path to real filesystem path."""
    normalized = os.path.normpath(virtual_path.lstrip("/"))

    if normalized == "." or normalized == "":
        return base_path

    real_path = base_path / normalized

    if not real_path.is_relative_to(base_path):
        raise ValueError("Path traversal attempt detected")

    return real_path


def get_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """Calculate file hash."""
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def format_file_size(size: float) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{int(size)} {unit}"
        size /= 1024
    return f"{int(size)} PB"


def get_file_extension(filename: str) -> Optional[str]:
    """Get file extension without dot."""
    ext = Path(filename).suffix.lstrip(".")
    return ext.lower() if ext else None


def is_image_file(
    filename: str, allowed_extensions: Optional[list[str]] = None
) -> bool:
    """Check if file is an image."""
    ext = get_file_extension(filename)
    if ext is None:
        return False

    default_images = {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp",
        "svg",
        "ico",
        "tiff",
        "tif",
    }

    if allowed_extensions:
        return ext in allowed_extensions
    return ext in default_images


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove potentially dangerous characters."""
    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # Remove path separators
    sanitized = sanitized.replace("/", "").replace("\\", "")
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[: 255 - len(ext)] + ext

    return sanitized or "unnamed"


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime for Rich Filemanager API."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_unique_filename(filename: str, directory: Path) -> str:
    """Create unique filename if file already exists."""
    if not (directory / filename).exists():
        return filename

    name, ext = os.path.splitext(filename)
    counter = 1
    while (directory / f"{name}_{counter}{ext}").exists():
        counter += 1
    return f"{name}_{counter}{ext}"
