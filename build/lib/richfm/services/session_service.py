"""Session service for database operations."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from richfm.models.session import Session as SessionModel
from richfm.models.session import db
from richfm.utils.exceptions import SessionInactiveError, SessionNotFoundError


class SessionService:
    """Service for session management."""

    @staticmethod
    def create(
        emulated_root: str,
        config: Optional[dict[str, Any]] = None,
    ) -> SessionModel:
        """Create a new session."""
        session = SessionModel.create_new(emulated_root, config)
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def get(session_id: str, check_active: bool = True) -> SessionModel:
        """Get session by ID."""
        session = db.session.get(SessionModel, session_id)

        if session is None:
            raise SessionNotFoundError(session_id)

        if check_active and not session.is_active:
            raise SessionInactiveError(session_id)

        # Update last accessed
        session.last_accessed = datetime.utcnow()
        db.session.commit()

        return session

    @staticmethod
    def get_all(active_only: bool = True) -> list[SessionModel]:
        """Get all sessions."""
        query = db.session.query(SessionModel)
        if active_only:
            query = query.filter(SessionModel.is_active == True)
        return query.all()

    @staticmethod
    def update(
        session_id: str,
        emulated_root: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> SessionModel:
        """Update session."""
        session = SessionService.get(session_id, check_active=False)

        if emulated_root is not None:
            session.emulated_root = emulated_root
        if config is not None:
            session.config = config
        if is_active is not None:
            session.is_active = is_active

        session.last_accessed = datetime.utcnow()
        db.session.commit()

        return session

    @staticmethod
    def delete(session_id: str) -> None:
        """Delete (deactivate) session."""
        session = SessionService.get(session_id, check_active=False)
        session.is_active = False
        db.session.commit()

    @staticmethod
    def cleanup_expired(days: int = 7) -> int:
        """Clean up expired sessions."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        expired = (
            db.session.query(SessionModel)
            .filter(
                SessionModel.is_active == True,  # type: ignore[attr-defined]
                SessionModel.last_accessed < cutoff,
            )
            .all()
        )

        count = len(expired)
        for session in expired:
            session.is_active = False

        db.session.commit()
        return count
