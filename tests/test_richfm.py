"""Unit tests for RichFM."""

import json
import os
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from richfm.models.schemas import (
    CopyRequest,
    CreateSessionRequest,
    DeleteRequest,
    ExtractRequest,
    MoveRequest,
    RenameRequest,
    SaveFileRequest,
    SessionConfig,
)
from richfm.services.file_ops import FileService
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
    is_safe_path,
    sanitize_filename,
    translate_path,
)


class TestHelpers:
    """Tests for helper functions."""

    def test_is_safe_path_valid(self):
        """Test safe path detection with valid paths."""
        base = Path("/base")
        assert is_safe_path(base, "folder/file.txt")
        assert is_safe_path(base, ".")
        assert is_safe_path(base, "subfolder")

    def test_is_safe_path_traversal(self):
        """Test safe path detection with traversal attempts."""
        base = Path("/base")
        assert not is_safe_path(base, "../etc/passwd")
        assert not is_safe_path(base, "folder/../../../etc")
        assert not is_safe_path(base, "..")

    def test_translate_path(self):
        """Test path translation."""
        base = Path("/base")
        result = translate_path(base, "/folder/file.txt")
        assert result == Path("/base/folder/file.txt")

    def test_translate_path_traversal(self):
        """Test path translation with traversal."""
        base = Path("/base")
        with pytest.raises(ValueError):
            translate_path(base, "/../etc/passwd")

    def test_get_file_extension(self):
        """Test file extension extraction."""
        assert get_file_extension("file.txt") == "txt"
        assert get_file_extension("archive.tar.gz") == "gz"
        assert get_file_extension("noext") is None

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("file.txt") == "file.txt"
        assert sanitize_filename("../etc/passwd") == "..etc.passwd"
        assert sanitize_filename("  file  ") == "file"
        assert sanitize_filename("a" * 300) == "a" * 255


class TestFileService:
    """Tests for FileService."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_service(self, temp_dir):
        """Create FileService instance."""
        config = {
            "security": {
                "read_only": False,
                "allowed_extensions": None,
                "blocked_extensions": [],
                "max_file_size": 1000000,
            }
        }
        return FileService(temp_dir, config)

    def test_read_folder_empty(self, file_service, temp_dir):
        """Test reading empty folder."""
        result = file_service.read_folder("/")
        assert result["numDirs"] == 0
        assert result["numFiles"] == 0
        assert result["items"] == []

    def test_read_folder_with_files(self, file_service, temp_dir):
        """Test reading folder with files."""
        (temp_dir / "test.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        result = file_service.read_folder("/")
        assert result["numDirs"] == 1
        assert result["numFiles"] == 1

    def test_read_folder_nonexistent(self, file_service):
        """Test reading nonexistent folder."""
        with pytest.raises(FileNotFoundError):
            file_service.read_folder("/nonexistent")

    def test_get_info_file(self, file_service, temp_dir):
        """Test getting file info."""
        (temp_dir / "test.txt").write_text("content")

        result = file_service.get_info("/test.txt")
        assert result["name"] == "test.txt"
        assert result["type"] == "file"
        assert "size" in result
        assert result["extension"] == "txt"

    def test_get_info_folder(self, file_service, temp_dir):
        """Test getting folder info."""
        (temp_dir / "subdir").mkdir()

        result = file_service.get_info("/subdir")
        assert result["name"] == "subdir"
        assert result["type"] == "folder"

    def test_add_folder(self, file_service):
        """Test creating folder."""
        result = file_service.add_folder("/", "newfolder")
        assert result["name"] == "newfolder"
        assert result["type"] == "folder"

    def test_add_folder_read_only(self, temp_dir):
        """Test creating folder in read-only mode."""
        config = {"security": {"read_only": True}}
        service = FileService(temp_dir, config)

        with pytest.raises(ReadOnlyError):
            service.add_folder("/", "newfolder")

    def test_upload_file(self, file_service, temp_dir):
        """Test uploading file."""
        content = b"file content"
        result = file_service.upload_file("/", "test.txt", content)
        assert result["name"] == "test.txt"
        assert (temp_dir / "test.txt").read_bytes() == content

    def test_upload_file_overwrite(self, file_service, temp_dir):
        """Test overwriting existing file."""
        (temp_dir / "test.txt").write_text("old")

        result = file_service.upload_file("/", "test.txt", b"new", overwrite=True)
        assert (temp_dir / "test.txt").read_bytes() == b"new"

    def test_upload_file_blocked_extension(self, file_service):
        """Test uploading blocked file type."""
        config = {
            "security": {
                "read_only": False,
                "allowed_extensions": None,
                "blocked_extensions": ["exe"],
                "max_file_size": 1000000,
            }
        }
        service = FileService(file_service.base_path, config)

        with pytest.raises(InvalidFileTypeError):
            service.upload_file("/", "malware.exe", b"data")

    def test_upload_file_size_exceeded(self, file_service):
        """Test uploading file exceeding size limit."""
        config = {
            "security": {
                "read_only": False,
                "allowed_extensions": None,
                "blocked_extensions": [],
                "max_file_size": 10,
            }
        }
        service = FileService(file_service.base_path, config)

        with pytest.raises(FileSizeExceededError):
            service.upload_file("/", "large.txt", b"12345678901")

    def test_rename_file(self, file_service, temp_dir):
        """Test renaming file."""
        (temp_dir / "old.txt").write_text("content")

        result = file_service.rename_item("/", "old.txt", "new.txt")
        assert result["name"] == "new.txt"
        assert not (temp_dir / "old.txt").exists()
        assert (temp_dir / "new.txt").exists()

    def test_move_file(self, file_service, temp_dir):
        """Test moving file."""
        (temp_dir / "source.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        result = file_service.move_item("/", "source.txt", "/subdir")
        assert not (temp_dir / "source.txt").exists()
        assert (temp_dir / "subdir" / "source.txt").exists()

    def test_copy_file(self, file_service, temp_dir):
        """Test copying file."""
        (temp_dir / "source.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        result = file_service.copy_item("/", "source.txt", "/subdir")
        assert (temp_dir / "source.txt").exists()
        assert (temp_dir / "subdir" / "source.txt").exists()

    def test_delete_file(self, file_service, temp_dir):
        """Test deleting file."""
        (temp_dir / "test.txt").write_text("content")

        file_service.delete_item("/test.txt")
        assert not (temp_dir / "test.txt").exists()

    def test_delete_folder_not_empty(self, file_service, temp_dir):
        """Test deleting non-empty folder."""
        (temp_dir / "folder").mkdir()
        (temp_dir / "folder" / "file.txt").write_text("content")

        with pytest.raises(DirectoryNotEmptyError):
            file_service.delete_item("/folder")

    def test_read_file(self, file_service, temp_dir):
        """Test reading file content."""
        (temp_dir / "test.txt").write_bytes(b"content")

        result = file_service.read_file("/test.txt")
        assert result == b"content"

    def test_save_file(self, file_service):
        """Test saving file."""
        result = file_service.save_file("/", "test content", "new.txt")
        assert result["name"] == "new.txt"
        assert (file_service.base_path / "new.txt").read_text() == "test content"

    def test_extract_archive(self, file_service, temp_dir):
        """Test extracting ZIP archive."""
        archive_path = temp_dir / "archive.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("file.txt", "content")

        file_service.extract_archive("/archive.zip", "/extracted")

        assert (temp_dir / "extracted" / "file.txt").exists()
        assert (temp_dir / "extracted" / "file.txt").read_text() == "content"

    def test_path_traversal_blocked(self, file_service):
        """Test path traversal is blocked."""
        with pytest.raises(PathTraversalError):
            file_service.read_folder("/../etc/passwd")


class TestSessionSchemas:
    """Tests for Pydantic schemas."""

    def test_create_session_request(self):
        """Test creating session request."""
        data = {
            "emulated_root": "/var/sandbox/user123",
            "config": {
                "read_only": False,
                "allowed_extensions": ["jpg", "png"],
                "max_file_size": 10485760,
            },
        }
        req = CreateSessionRequest.model_validate(data)
        assert req.emulated_root == "/var/sandbox/user123"
        assert req.config is not None
        assert req.config.read_only is False
        assert req.config.allowed_extensions == ["jpg", "png"]

    def test_session_config_defaults(self):
        """Test session config defaults."""
        config = SessionConfig()
        assert config.read_only is False
        assert config.max_file_size == 104857600


class TestExceptions:
    """Tests for custom exceptions."""

    def test_richfm_error(self):
        """Test base exception."""
        err = RichFMError("Test error", code=400)
        assert err.message == "Test error"
        assert err.code == 400

    def test_session_not_found_error(self):
        """Test session not found error."""
        err = SessionNotFoundError("test-id")
        assert err.session_id == "test-id"
        assert err.code == 404

    def test_file_not_found_error(self):
        """Test file not found error."""
        err = FileNotFoundError("/path/to/file")
        assert err.path == "/path/to/file"
        assert err.code == 404

    def test_read_only_error(self):
        """Test read-only error."""
        err = ReadOnlyError()
        assert err.code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
