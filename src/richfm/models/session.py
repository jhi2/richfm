"""Database models for RichFM."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Session(db.Model):
    """File manager session model."""

    __tablename__ = "sessions"

    session_id: str = db.Column(db.String(36), primary_key=True)
    emulated_root: str = db.Column(db.String(512), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: bool = db.Column(db.Boolean, default=True)
    config_json: str = db.Column(db.Text, default="{}")

    @property
    def config(self) -> dict[str, Any]:
        """Get session configuration as dict."""
        if self.config_json:
            return json.loads(self.config_json)
        return {}

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        """Set session configuration from dict."""
        self.config_json = json.dumps(value)

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "emulated_root": self.emulated_root,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat()
            if self.last_accessed
            else None,
            "is_active": self.is_active,
            "config": self.config,
        }

    @classmethod
    def create_new(
        cls, emulated_root: str, config: Optional[dict[str, Any]] = None
    ) -> "Session":
        """Create a new session."""
        session = cls(
            session_id=str(uuid4()),
            emulated_root=emulated_root,
            is_active=True,
            config_json=json.dumps(config or {}),
        )
        return session
