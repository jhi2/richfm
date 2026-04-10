"""Configuration module for RichFM."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RichFMSettings(BaseSettings):
    """RichFM application settings."""

    model_config = SettingsConfigDict(
        env_prefix="RICHFM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base paths
    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    uploads_dir: Path = Field(default_factory=lambda: Path.cwd() / "uploads")
    sessions_dir: Path = Field(default_factory=lambda: Path.cwd() / "sessions")
    logs_dir: Path = Field(default_factory=lambda: Path.cwd() / "logs")

    # Database
    database_url: str = Field(default="sqlite:///richfm.db")

    # Flask settings
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    debug: bool = False

    # File manager settings
    default_max_file_size: int = 104857600  # 100MB
    default_read_only: bool = False
    thumbnail_size: tuple[int, int] = (48, 48)

    # Session settings
    session_cookie_name: str = "richfm_session"
    session_expiry_days: int = 7

    # CORS settings
    cors_origins: str = "*"

    # Logging
    log_level: str = "INFO"

    def get_uploads_path(self, session_id: str) -> Path:
        """Get upload path for a session."""
        return self.uploads_dir / session_id

    def get_session_root_path(self, session_id: str) -> Path:
        """Get session root path."""
        return self.sessions_dir / session_id


settings = RichFMSettings()


def create_default_config(path: Optional[Path] = None) -> dict:
    """Create default configuration dictionary."""
    if path is None:
        path = Path.cwd() / "richfm_config.yaml"

    config = {
        "version": "1.0",
        "security": {
            "allow_path_traversal": False,
            "allowed_extensions": None,  # None means all allowed
            "blocked_extensions": ["exe", "sh", "bat", "cmd"],
            "max_file_size": settings.default_max_file_size,
            "read_only": False,
        },
        "upload": {
            "overwrite": True,
            "unique_filename": False,
        },
        "images": {
            "thumbnails": True,
            "thumbnail_size": [48, 48],
            "allowed_extensions": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
        },
        "logging": {
            "level": settings.log_level,
            "file": str(settings.logs_dir / "richfm.log"),
        },
    }

    return config
