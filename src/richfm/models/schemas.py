"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SessionConfig(BaseModel):
    """Session configuration model."""

    read_only: bool = False
    allowed_extensions: Optional[list[str]] = None
    blocked_extensions: Optional[list[str]] = None
    max_file_size: int = Field(default=104857600, ge=0)  # 100MB default


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    emulated_root: str = Field(min_length=1)
    config: Optional[SessionConfig] = None


class SessionResponse(BaseModel):
    """Response model for session."""

    session_id: str
    emulated_root: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    is_active: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class FileInfo(BaseModel):
    """File/folder info model."""

    name: str
    path: str
    size: int = 0
    date: Optional[str] = None
    extension: Optional[str] = None
    type: str = "file"  # "file" or "folder"
    hash: Optional[str] = None


class FolderContent(BaseModel):
    """Folder content model."""

    path: str
    numDirs: int = 0
    numFiles: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)


class FileItem(BaseModel):
    """File item for folder listing."""

    name: str
    path: str
    size: int = 0
    date: str
    extension: Optional[str] = None
    type: str = "file"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate item type."""
        if v not in ("file", "folder"):
            raise ValueError("Type must be 'file' or 'folder'")
        return v


class UploadRequest(BaseModel):
    """Upload request model."""

    path: str = "/"
    overwrite: bool = True


class RenameRequest(BaseModel):
    """Rename request model."""

    old: str
    new: str
    type: str = "file"


class MoveRequest(BaseModel):
    """Move request model."""

    old: str
    new: str
    type: str = "file"


class CopyRequest(BaseModel):
    """Copy request model."""

    source: str
    destination: str
    type: str = "file"


class DeleteRequest(BaseModel):
    """Delete request model."""

    items: list[str]


class SaveFileRequest(BaseModel):
    """Save file request model."""

    content: str
    path: str


class ExtractRequest(BaseModel):
    """Extract archive request model."""

    source: str
    destination: str = "/"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    timestamp: datetime
