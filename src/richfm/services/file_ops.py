"""File operations service for RichFM."""

import io
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from richfm.utils.exceptions import (
    DirectoryNotEmptyError,
    ExtractionError,
    FileExistsError,
    FileNotFoundError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidOperationError,
    PathTraversalError,
    ReadOnlyError,
)
from richfm.utils.helpers import (
    format_datetime,
    get_file_extension,
    get_file_hash,
    is_safe_path,
    sanitize_filename,
    translate_path,
)


class FileService:
    """Service for file operations."""

    def __init__(
        self,
        base_path: Path,
        config: dict[str, Any],
    ):
        """Initialize file service."""
        self.base_path = base_path
        self.config = config
        self._ensure_base_path()

    def _ensure_base_path(self) -> None:
        """Ensure base path exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _check_read_only(self) -> None:
        """Check if in read-only mode."""
        if self.config.get("security", {}).get("read_only", False):
            raise ReadOnlyError()

    def _check_file_type(self, filename: str) -> None:
        """Check if file type is allowed."""
        extension = get_file_extension(filename)
        if extension is None:
            return

        allowed = self.config.get("security", {}).get("allowed_extensions")
        blocked = self.config.get("security", {}).get("blocked_extensions", [])

        if allowed is not None and extension not in allowed:
            raise InvalidFileTypeError(extension)
        if extension in blocked:
            raise InvalidFileTypeError(extension)

    def _check_file_size(self, file_size: int) -> None:
        """Check if file size is within limits."""
        max_size = self.config.get("security", {}).get("max_file_size", 0)
        if max_size > 0 and file_size > max_size:
            raise FileSizeExceededError(file_size, max_size)

    def _resolve_path(self, virtual_path: str) -> Path:
        """Resolve virtual path to real path."""
        if not is_safe_path(self.base_path, virtual_path):
            raise PathTraversalError(virtual_path)
        return translate_path(self.base_path, virtual_path)

    def read_folder(self, virtual_path: str) -> dict[str, Any]:
        """Read folder contents."""
        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        if not real_path.is_dir():
            raise InvalidOperationError(f"Not a directory: {virtual_path}")

        items = []
        num_dirs = 0
        num_files = 0

        for item in sorted(real_path.iterdir()):
            try:
                stat = item.stat()
                item_type = "folder" if item.is_dir() else "file"

                if item_type == "folder":
                    num_dirs += 1
                else:
                    num_files += 1
                    self._check_file_type(item.name)

                items.append(
                    {
                        "name": item.name,
                        "path": (virtual_path.rstrip("/") + "/" + item.name).strip("/"),
                        "size": stat.st_size if item_type == "file" else 0,
                        "date": format_datetime(datetime.fromtimestamp(stat.st_mtime)),
                        "extension": get_file_extension(item.name),
                        "type": item_type,
                    }
                )
            except (PermissionError, OSError):
                continue

        return {
            "path": virtual_path.strip("/"),
            "numDirs": num_dirs,
            "numFiles": num_files,
            "items": items,
        }

    def get_info(self, virtual_path: str) -> dict[str, Any]:
        """Get file/folder info."""
        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        stat = real_path.stat()
        item_type = "folder" if real_path.is_dir() else "file"

        result = {
            "name": real_path.name or virtual_path.split("/")[-1],
            "path": virtual_path.strip("/"),
            "date": format_datetime(datetime.fromtimestamp(stat.st_mtime)),
            "type": item_type,
        }

        if item_type == "file":
            result["size"] = stat.st_size
            result["extension"] = get_file_extension(real_path.name)
            result["hash"] = get_file_hash(real_path)

        return result

    def add_folder(self, virtual_path: str, name: str) -> dict[str, Any]:
        """Create a new folder."""
        self._check_read_only()

        parent = self._resolve_path(virtual_path)
        new_folder_path = parent / sanitize_filename(name)

        if new_folder_path.exists():
            raise FileExistsError(str(new_folder_path))

        new_folder_path.mkdir(parents=True)
        return self.get_info(virtual_path.rstrip("/") + "/" + name)

    def upload_file(
        self,
        virtual_path: str,
        filename: str,
        file_data: bytes,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Upload a file."""
        self._check_read_only()
        self._check_file_type(filename)
        self._check_file_size(len(file_data))

        parent = self._resolve_path(virtual_path)
        target_path = parent / sanitize_filename(filename)

        if target_path.exists() and not overwrite:
            raise FileExistsError(str(target_path))

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(file_data)

        return self.get_info(virtual_path.rstrip("/") + "/" + filename)

    def rename_item(
        self,
        virtual_path: str,
        old_name: str,
        new_name: str,
        item_type: str = "file",
    ) -> dict[str, Any]:
        """Rename a file or folder."""
        self._check_read_only()

        old_path = self._resolve_path(virtual_path.rstrip("/") + "/" + old_name)
        parent = old_path.parent
        new_path = parent / sanitize_filename(new_name)

        if not old_path.exists():
            raise FileNotFoundError(str(old_path))

        if new_path.exists():
            raise FileExistsError(str(new_path))

        old_path.rename(new_path)

        new_virtual = virtual_path.rstrip("/") + "/" + new_name
        return self.get_info(new_virtual)

    def move_item(
        self,
        virtual_path: str,
        old_name: str,
        new_path: str,
        item_type: str = "file",
    ) -> dict[str, Any]:
        """Move a file or folder."""
        self._check_read_only()

        source = self._resolve_path(virtual_path.rstrip("/") + "/" + old_name)
        dest = self._resolve_path(new_path.rstrip("/") + "/" + old_name)

        if not source.exists():
            raise FileNotFoundError(str(source))

        if dest.exists():
            raise FileExistsError(str(dest))

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(dest))

        return self.get_info(new_path.rstrip("/") + "/" + old_name)

    def copy_item(
        self,
        virtual_path: str,
        old_name: str,
        new_path: str,
        item_type: str = "file",
    ) -> dict[str, Any]:
        """Copy a file or folder."""
        self._check_read_only()

        source = self._resolve_path(virtual_path.rstrip("/") + "/" + old_name)
        dest = self._resolve_path(new_path.rstrip("/") + "/" + old_name)

        if not source.exists():
            raise FileNotFoundError(str(source))

        if dest.exists():
            raise FileExistsError(str(dest))

        dest.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(str(source), str(dest))
        else:
            shutil.copy2(str(source), str(dest))

        return self.get_info(new_path.rstrip("/") + "/" + old_name)

    def delete_item(self, virtual_path: str, item_type: str = "file") -> None:
        """Delete a file or folder."""
        self._check_read_only()

        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        if real_path.is_dir():
            if any(real_path.iterdir()):
                raise DirectoryNotEmptyError(virtual_path)
            real_path.rmdir()
        else:
            real_path.unlink()

    def save_file(
        self,
        virtual_path: str,
        content: str,
        filename: str,
    ) -> dict[str, Any]:
        """Save file content."""
        self._check_read_only()
        self._check_file_type(filename)

        parent = self._resolve_path(virtual_path)
        file_path = parent / sanitize_filename(filename)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        return self.get_info(virtual_path.rstrip("/") + "/" + filename)

    def read_file(self, virtual_path: str) -> bytes:
        """Read file content."""
        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        if real_path.is_dir():
            raise InvalidOperationError("Cannot read directory")

        return real_path.read_bytes()

    def get_image(
        self,
        virtual_path: str,
        size: tuple[int, int] = (48, 48),
    ) -> bytes:
        """Get image thumbnail."""
        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        if real_path.is_dir():
            raise InvalidOperationError("Cannot get image of directory")

        try:
            with Image.open(real_path) as img:
                img.thumbnail(size)
                buffer = io.BytesIO()
                img_format = img.format or "PNG"
                img.save(buffer, format=img_format)
                return buffer.getvalue()
        except Exception as e:
            raise InvalidOperationError(f"Failed to process image: {e}")

    def summarize(self, virtual_path: str) -> dict[str, Any]:
        """Get summary of folder."""
        real_path = self._resolve_path(virtual_path)

        if not real_path.exists():
            raise FileNotFoundError(virtual_path)

        if not real_path.is_dir():
            return self.get_info(virtual_path)

        total_size = 0
        file_count = 0
        dir_count = 0

        for item in real_path.rglob("*"):
            try:
                if item.is_dir():
                    dir_count += 1
                else:
                    file_count += 1
                    total_size += item.stat().st_size
            except (PermissionError, OSError):
                continue

        return {
            "path": virtual_path.strip("/"),
            "numDirs": dir_count,
            "numFiles": file_count,
            "size": total_size,
        }

    def extract_archive(
        self,
        source_path: str,
        dest_path: str,
    ) -> dict[str, Any]:
        """Extract archive."""
        self._check_read_only()

        source = self._resolve_path(source_path)
        dest = self._resolve_path(dest_path)

        if not source.exists():
            raise FileNotFoundError(source_path)

        if not zipfile.is_zipfile(source):
            raise ExtractionError("Not a valid ZIP file")

        dest.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(source, "r") as zf:
                zf.extractall(dest)
        except Exception as e:
            raise ExtractionError(str(e))

        return self.get_info(dest_path)


def create_file_service(
    base_path: Path,
    config: dict[str, Any],
) -> FileService:
    """Factory function to create FileService."""
    return FileService(base_path, config)
