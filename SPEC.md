# RichFM - Rich Filemanager Flask Wrapper

## Project Overview
- **Project Name**: RichFM
- **Project Type**: Flask Blueprint wrapper for Rich Filemanager
- **Core Functionality**: Multi-session isolated file system management with REST API
- **Target Users**: Web developers needing file management capabilities in Flask apps

## Technology Stack
- Python 3.10+
- Flask 2.3+
- Flask-SQLAlchemy 3.0+
- Pydantic 2.0+ for validation
- Pillow for image thumbnails
- structlog for logging

## Functionality Specification

### 1. Session Management
- **Session ID**: UUID4 format
- **Storage**: SQLite database with SQLAlchemy
- **Identification**: Query param `session_id`, Header `X-Session-ID`, or cookie fallback
- **Metadata**: session_id, emulated_root, created_at, last_accessed, is_active, config_json
- **Operations**: Create, Get, Update, Delete sessions

### 2. Rich Filemanager API Endpoints

| Endpoint | Mode | Description |
|----------|------|-------------|
| GET/POST / | init | Initialize connection |
| GET / | getinfo | Get file/folder info |
| GET / | readfolder | List directory contents |
| GET/POST / | addfolder | Create directory |
| POST / | upload | Upload file |
| POST / | rename | Rename file/folder |
| POST / | move | Move file/folder |
| POST / | copy | Copy file/folder |
| POST / | savefile | Save file content |
| POST / | delete | Delete file/folder |
| GET / | download | Download file |
| GET / | getimage | Get image thumbnail |
| GET / | readfile | Read file content |
| POST / | extract | Extract ZIP archive |

### 3. Path Emulation
- Virtual paths relative to session's emulated_root
- Translation: virtual_path -> real_path = emulated_root + virtual_path
- Security: Block all `../` traversal attempts

### 4. Security Features
- Path traversal protection
- Configurable file type allowlist/blocklist
- Max file size per session
- Read-only mode option

### 5. Configuration
- Environment variable support
- Default config file generation
- Per-session configuration overrides

## Data Models

### Session Model
```python
class Session:
    session_id: UUID
    emulated_root: str  # Absolute path
    created_at: datetime
    last_accessed: datetime
    is_active: bool
    config_json: str  # JSON string
```

### Request Models (Pydantic)
```python
class CreateSessionRequest:
    emulated_root: str
    config: SessionConfig

class SessionConfig:
    read_only: bool = False
    allowed_extensions: list[str] | None = None
    blocked_extensions: list[str] | None = None
    max_file_size: int = 104857600  # 100MB default
```

## API Response Format

### Success Response
```json
{
  "result": {
    "success": true,
    "data": { ... },
    "id": "..."
  }
}
```

### Error Response
```json
{
  "result": {
    "success": false,
    "error": "Error message",
    "code": 500
  }
}
```

## Acceptance Criteria
1. Sessions can be created via POST /filemanager/session
2. Files can be listed, created, renamed, moved, copied, deleted
3. Virtual paths are properly translated to real paths
4. Path traversal is blocked
5. File type restrictions work correctly
6. File size limits are enforced
7. All Rich Filemanager API modes are implemented
8. Unit tests pass for core functionality
9. README provides clear integration instructions