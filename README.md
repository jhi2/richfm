# RichFM - Rich Filemanager Flask Blueprint

A modern Flask Blueprint wrapper for Rich Filemanager with multi-session isolation and secure file operations.

## Features

- **Multi-Session Architecture**: Each session has its own emulated root path (chroot-like isolation)
- **Session Management**: Create, list, get, and delete sessions via REST API
- **Rich Filemanager API**: Full implementation of all standard modes
  - `initiate`, `getinfo`, `readfolder`, `seekfolder`
  - `addfolder`, `upload`, `rename`, `move`, `copy`
  - `savefile`, `delete`, `download`, `getimage`
  - `readfile`, `summarize`, `extract`
- **Security Features**:
  - Path traversal protection (`../` blocking)
  - File type allowlist/blocklist
  - Max file size limits per session
  - Read-only mode support
- **Modern Flask Practices**:
  - Flask 2.0+ with type hints
  - Pydantic models for validation
  - Flask-SQLAlchemy for session persistence
  - Flask-CORS for frontend integration
  - Blueprint factory pattern
- **Additional Features**:
  - ZIP extraction support
  - Image thumbnail generation (Pillow)
  - Health check endpoint
  - OpenAPI documentation endpoint

## Project Structure

```
richfm/
├── src/richfm/
│   ├── __init__.py          # Flask app factory
│   ├── __about__.py         # Version info
│   ├── config.py            # Settings
│   ├── blueprint/
│   │   └── filemanager.py   # Main Blueprint
│   ├── models/
│   │   ├── session.py       # Database model
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/
│   │   ├── file_ops.py      # File operations
│   │   └── session_service.py
│   └── utils/
│       ├── exceptions.py    # Custom exceptions
│       └── helpers.py       # Utility functions
├── tests/
│   └── test_richfm.py       # Unit tests
├── uploads/                 # Upload directory
├── sessions/                # Session root directories
├── logs/                    # Log files
├── requirements.txt
├── pyproject.toml
├── setup.py
├── example_app.py
└── README.md
```

## Installation

### Quick Start (Using Setup Script)

```bash
# Run the setup script
python setup.py

# Activate virtual environment
source venv/bin/activate

# Run the example app
python example_app.py
```

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Configuration

Environment variables (prefix: `RICHFM_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev-secret-key | Flask secret key |
| `DEBUG` | false | Debug mode |
| `DATABASE_URL` | sqlite:///richfm.db | Database URL |
| `LOG_LEVEL` | INFO | Logging level |
| `SESSION_COOKIE_NAME` | richfm_session | Session cookie name |

## Usage Example

### Creating a New Session

```python
import requests

# Create a new isolated session
response = requests.post("http://localhost:5000/filemanager/session", json={
    "emulated_root": "/home/johnny/Applications/richfm/sessions/user123",
    "config": {
        "read_only": False,
        "allowed_extensions": ["jpg", "png", "pdf"],
        "max_file_size": 10485760  # 10MB
    }
})

session_data = response.json()
session_id = session_data["result"]["data"]["session_id"]
print(f"Session ID: {session_id}")
```

### Using the File Manager

```python
import requests

session_id = "550e8400-e29b-41d4-a716-446655440000"
base_url = "http://localhost:5000/filemanager"

# Read folder contents
response = requests.get(
    f"{base_url}/?mode=readfolder&path=/&session_id={session_id}"
)
print(response.json())

# Upload a file
with open("test.txt", "rb") as f:
    files = {"file": ("test.txt", f)}
    data = {"path": "/", "mode": "upload"}
    response = requests.post(
        f"{base_url}/",
        files=files,
        data=data,
        params={"session_id": session_id}
    )

# Create a folder
response = requests.post(
    f"{base_url}/",
    data={"mode": "addfolder", "name": "documents", "path": "/"},
    params={"session_id": session_id}
)

# Download a file
response = requests.get(
    f"{base_url}/?mode=download&path=/test.txt&session_id={session_id}"
)
```

### Integration with Flask

```python
from flask import Flask
from richfm import create_app

app = create_app()

# Or with custom configuration
from richfm.config import RichFMSettings

config = RichFMSettings(
    secret_key="your-secret-key",
    debug=True,
    database_url="sqlite:///custom.db"
)
app = create_app(config)

if __name__ == "__main__":
    app.run()
```

### Custom Blueprint Registration

```python
from flask import Flask
from richfm.blueprint.filemanager import rich_filemanager

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///richfm.db"

# Register with custom URL prefix
app.register_blueprint(rich_filemanager, url_prefix="/fm")

@app.route("/")
def index():
    return "Welcome to RichFM!"

if __name__ == "__main__":
    app.run()
```

## API Endpoints

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/filemanager/session` | Create new session |
| GET | `/filemanager/session` | List all sessions |
| GET | `/filemanager/session/<id>` | Get session info |
| DELETE | `/filemanager/session/<id>` | Delete session |

### File Manager Operations

| Method | Endpoint | Mode | Description |
|--------|----------|------|-------------|
| GET/POST | `/filemanager/` | initiate | Initialize connection |
| GET | `/filemanager/` | getinfo | Get file/folder info |
| GET | `/filemanager/` | readfolder | List directory |
| GET/POST | `/filemanager/` | addfolder | Create folder |
| POST | `/filemanager/` | upload | Upload file |
| POST | `/filemanager/` | rename | Rename item |
| POST | `/filemanager/` | move | Move item |
| POST | `/filemanager/` | copy | Copy item |
| POST | `/filemanager/` | delete | Delete item |
| POST | `/filemanager/` | savefile | Save file content |
| GET | `/filemanager/` | download | Download file |
| GET | `/filemanager/` | getimage | Get thumbnail |
| GET | `/filemanager/` | readfile | Read file |
| GET | `/filemanager/` | summarize | Get folder summary |
| POST | `/filemanager/` | extract | Extract archive |

### Additional Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/filemanager/health` | Health check |
| GET | `/filemanager/docs` | OpenAPI docs |

## Session Identification

Session ID can be provided via:
1. **Query parameter**: `?session_id=abc123`
2. **HTTP header**: `X-Session-ID: abc123`
3. **Cookie**: `richfm_session`

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/richfm --cov-report=html

# Run specific test file
pytest tests/test_richfm.py -v
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code with black
black src/richfm tests/

# Type checking
mypy src/richfm

# Run all checks
pytest && black --check src/richfm && mypy src/richfm
```

## License

MIT License