"""Custom exceptions for RichFM."""


class RichFMError(Exception):
    """Base exception for RichFM."""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


class SessionNotFoundError(RichFMError):
    """Session not found."""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}", code=404)
        self.session_id = session_id


class SessionInactiveError(RichFMError):
    """Session is inactive."""

    def __init__(self, session_id: str):
        super().__init__(f"Session is inactive: {session_id}", code=403)
        self.session_id = session_id


class PathTraversalError(RichFMError):
    """Path traversal attempt detected."""

    def __init__(self, path: str):
        super().__init__(f"Path traversal attempt detected: {path}", code=403)
        self.path = path


class FileNotFoundError(RichFMError):
    """File not found."""

    def __init__(self, path: str):
        super().__init__(f"File not found: {path}", code=404)
        self.path = path


class FileExistsError(RichFMError):
    """File already exists."""

    def __init__(self, path: str):
        super().__init__(f"File already exists: {path}", code=409)
        self.path = path


class DirectoryNotEmptyError(RichFMError):
    """Directory not empty."""

    def __init__(self, path: str):
        super().__init__(f"Directory not empty: {path}", code=409)
        self.path = path


class InvalidFileTypeError(RichFMError):
    """Invalid file type."""

    def __init__(self, extension: str):
        super().__init__(f"File type not allowed: {extension}", code=415)
        self.extension = extension


class FileSizeExceededError(RichFMError):
    """File size exceeded."""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            f"File size {size} exceeds maximum {max_size}",
            code=413,
        )
        self.size = size
        self.max_size = max_size


class ReadOnlyError(RichFMError):
    """Session is read-only."""

    def __init__(self):
        super().__init__("Session is in read-only mode", code=403)


class InvalidOperationError(RichFMError):
    """Invalid operation."""

    def __init__(self, message: str):
        super().__init__(message, code=400)


class ExtractionError(RichFMError):
    """Error extracting archive."""

    def __init__(self, message: str):
        super().__init__(f"Extraction failed: {message}", code=500)
