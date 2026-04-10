"""Rich Filemanager Blueprint for Flask."""

import io
import os
from pathlib import Path
from typing import Any, Optional

from flask import Blueprint, jsonify, request, send_file, make_response
from sqlalchemy import text

from richfm.config import settings
from richfm.models.session import db
from richfm.models.schemas import (
    CopyRequest,
    CreateSessionRequest,
    DeleteRequest,
    ExtractRequest,
    MoveRequest,
    RenameRequest,
    SaveFileRequest,
    SessionConfig,
    SessionResponse,
)
from richfm.services.file_ops import FileService, create_file_service
from richfm.services.session_service import SessionService
from richfm.utils.exceptions import RichFMError

rich_filemanager = Blueprint("rich_filemanager", __name__)


def get_param(name: str, default: str = "") -> str:
    """Get parameter from either GET args or POST form."""
    return request.args.get(name) or request.form.get(name, default)


def get_session_id() -> Optional[str]:
    """Get session ID from request."""
    # Try direct session_id param first
    session_id = request.args.get("session_id")
    if session_id:
        return session_id

    # Check header
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        return session_id

    # Check cookies
    session_id = request.cookies.get("richfm_session")
    if session_id:
        return session_id
    session_id = request.cookies.get("rfm_session")
    if session_id:
        return session_id

    # Search all query params for anything that looks like a UUID session_id
    for key, value in request.args.items():
        if len(value) == 36 and value.count("-") == 4:
            return value

    return None


def get_current_session():
    """Get current session."""
    session_id = get_session_id()
    if not session_id:
        raise RichFMError("No session ID provided", code=400)
    return SessionService.get(session_id)


def json_api_response(data: Any, status: int = 200) -> Any:
    """Create JSON API response."""
    return jsonify({"data": data}), status


def json_api_error(message: str, code: str = "500", status: int = 500) -> Any:
    """Create JSON API error response."""
    return jsonify(
        {
            "errors": [
                {
                    "id": "server",
                    "code": code,
                    "title": message,
                }
            ]
        }
    ), status


def handle_error(error: Exception) -> tuple:
    """Handle errors and return error response."""
    if isinstance(error, RichFMError):
        return json_api_error(error.message, str(error.code), error.code)
    return json_api_error(str(error), "500", 500)


@rich_filemanager.route("/session", methods=["POST"])
def create_session():
    """Create a new file manager session."""
    try:
        data = request.get_json()
        if not data:
            return json_api_error("No JSON data provided", "400", 400)

        validated = CreateSessionRequest.model_validate(data)

        emulated_root = validated.emulated_root
        config = validated.config.model_dump() if validated.config else None

        if config:
            session = SessionService.create(emulated_root, config)
        else:
            session = SessionService.create(emulated_root)

        Path(emulated_root).mkdir(parents=True, exist_ok=True)

        return json_api_response(
            {
                "id": session.session_id,
                "type": "session",
                "attributes": session.to_dict(),
            }
        )
    except Exception as e:
        error_response, status_code = handle_error(e)
        return error_response, status_code


@rich_filemanager.route("/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get session info."""
    try:
        session = SessionService.get(session_id)
        return json_api_response(
            {
                "id": session.session_id,
                "type": "session",
                "attributes": session.to_dict(),
            }
        )
    except Exception as e:
        error_response, status_code = handle_error(e)
        return error_response, status_code


@rich_filemanager.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete (deactivate) session."""
    try:
        SessionService.delete(session_id)
        return json_api_response({"id": session_id, "type": "session"})
    except Exception as e:
        error_response, status_code = handle_error(e)
        return error_response, status_code


@rich_filemanager.route("/session", methods=["GET"])
def list_sessions():
    """List all sessions."""
    try:
        active_only = request.args.get("active_only", "true").lower() == "true"
        sessions = SessionService.get_all(active_only=active_only)
        data = [
            {"id": s.session_id, "type": "session", "attributes": s.to_dict()}
            for s in sessions
        ]
        return json_api_response(data)
    except Exception as e:
        error_response, status_code = handle_error(e)
        return error_response, status_code


def build_file_attributes(file_info: dict, path: str) -> dict:
    """Build JSON API attributes for a file/folder."""
    import time

    attrs = {
        "name": file_info.get("name", ""),
        "path": path,
        "readable": 1,
        "writable": 1,
    }

    # Parse date
    date_str = file_info.get("date", "")
    if date_str:
        try:
            from datetime import datetime

            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            attrs["created"] = int(dt.timestamp())
            attrs["modified"] = int(dt.timestamp())
        except:
            attrs["created"] = None
            attrs["modified"] = None
    else:
        attrs["created"] = None
        attrs["modified"] = None

    if file_info.get("type") == "file":
        attrs["size"] = file_info.get("size", 0)
    else:
        attrs["size"] = 0

    return attrs


@rich_filemanager.route("/", methods=["GET", "POST"])
def handle_filemanager():
    """Handle all Rich Filemanager API requests."""
    try:
        session_id = get_session_id()
        if not session_id:
            return json_api_error("No session ID provided", "401", 400)

        session = SessionService.get(session_id)
        base_path = Path(session.emulated_root)
        config = session.config

        file_service = create_file_service(base_path, {"security": config})

        mode = (
            request.args.get("mode")
            or request.args.get("mode")
            or request.form.get("mode")
        )

        if request.method == "POST":
            post_mode = request.form.get("mode")
            if post_mode:
                mode = post_mode

        if mode == "initiate":
            return json_api_response(
                {
                    "id": "/",
                    "type": "initiate",
                    "attributes": {
                        "config": {
                            "security": {
                                "readOnly": config.get("read_only", False),
                                "allowNoExtension": True,
                                "extensions": {
                                    "policy": "ALLOW_LIST",
                                    "ignoreCase": True,
                                    "restrictions": [],
                                },
                            },
                            "upload": {
                                "fileSizeLimit": config.get("max_file_size", 104857600),
                            },
                        }
                    },
                }
            )

        elif mode == "getinfo":
            path = request.args.get("path", "/")
            info = file_service.get_info(path)
            file_type = "folder" if info.get("type") == "folder" else "file"
            return json_api_response(
                {
                    "id": path,
                    "type": file_type,
                    "attributes": build_file_attributes(info, path),
                }
            )

        elif mode == "readfolder":
            path = request.args.get("path", "/")
            content = file_service.read_folder(path)
            items = []
            for item in content.get("items", []):
                item_path = item.get("path", "")
                item_type = item.get("type", "file")
                items.append(
                    {
                        "id": item_path,
                        "type": item_type,
                        "attributes": build_file_attributes(item, item_path),
                    }
                )
            return json_api_response(items)

        elif mode == "addfolder":
            name = request.form.get("name") or request.args.get("name")
            path = request.form.get("path", "/") or request.args.get("path", "/")
            if not name:
                return json_api_error("Name required", "400", 400)
            result = file_service.add_folder(path, name)
            folder_path = path.rstrip("/") + "/" + name
            return json_api_response(
                {
                    "id": folder_path,
                    "type": "folder",
                    "attributes": build_file_attributes(result, folder_path),
                }
            )

        if mode == "upload":
            path = get_param("path", "/")
            file = request.files.get("file")
            if not file:
                return json_api_error("No file provided", "400", 400)
            filename = file.filename or "uploaded_file"
            file_data = file.read()
            overwrite = get_param("overwrite", "true").lower() == "true"
            result = file_service.upload_file(path, filename, file_data, overwrite)
            file_path = path.rstrip("/") + "/" + filename
            return json_api_response(
                {
                    "id": file_path,
                    "type": "file",
                    "attributes": build_file_attributes(result, file_path),
                }
            )

        if mode == "rename":
            old = get_param("old")
            new = get_param("new")
            item_type = get_param("type", "file")
            path = get_param("path", "/")
            if not old or not new:
                return json_api_error("Old and new names required", "400", 400)
            result = file_service.rename_item(path, old, new, item_type)
            new_path = path.rstrip("/") + "/" + new
            return json_api_response(
                {
                    "id": new_path,
                    "type": item_type,
                    "attributes": build_file_attributes(result, new_path),
                }
            )

        if mode == "move":
            old = get_param("old")
            new = get_param("new")
            item_type = get_param("type", "file")
            path = get_param("path", "/")
            if not old or not new:
                return json_api_error("Old and new paths required", "400", 400)
            result = file_service.move_item(path, old, new, item_type)
            moved_path = new.rstrip("/") + "/" + old
            return json_api_response(
                {
                    "id": moved_path,
                    "type": item_type,
                    "attributes": build_file_attributes(result, moved_path),
                }
            )

        if mode == "copy":
            old = get_param("old")
            new = get_param("new")
            item_type = get_param("type", "file")
            path = get_param("path", "/")
            if not old or not new:
                return json_api_error("Source and destination required", "400", 400)
            result = file_service.copy_item(path, old, new, item_type)
            copy_path = new.rstrip("/") + "/" + old
            return json_api_response(
                {
                    "id": copy_path,
                    "type": item_type,
                    "attributes": build_file_attributes(result, copy_path),
                }
            )

        if mode == "delete":
            path = get_param("path")
            item_type = get_param("type", "file")
            if not path:
                return json_api_error("Path required", "400", 400)
            file_service.delete_item(path, item_type)
            return json_api_response({"id": path, "type": item_type})

        if mode == "savefile":
            content = get_param("content", "")
            path = get_param("path", "/")
            name = get_param("name")
            if not name:
                return json_api_error("Name required", "400", 400)
            result = file_service.save_file(path, content, name)
            file_path = path.rstrip("/") + "/" + name
            return json_api_response(
                {
                    "id": file_path,
                    "type": "file",
                    "attributes": build_file_attributes(result, file_path),
                }
            )

        elif mode == "download":
            path = request.args.get("path")
            if not path:
                return json_api_error("Path required", "400", 400)
            data = file_service.read_file(path)
            filename = path.split("/")[-1]
            return send_file(
                io.BytesIO(data),
                as_attachment=True,
                download_name=filename,
            )

        elif mode == "getimage":
            path = request.args.get("path")
            if not path:
                return json_api_error("Path required", "400", 400)
            size = tuple(request.args.get("size", "48,48").split(","))
            size_tuple = (int(size[0]), int(size[1]))
            data = file_service.get_image(path, size_tuple)
            return send_file(
                io.BytesIO(data),
                mimetype="image/png",
            )

        elif mode == "readfile":
            path = request.args.get("path")
            if not path:
                return json_api_error("Path required", "400", 400)
            data = file_service.read_file(path)
            return make_response(data)

        elif mode == "summarize":
            path = request.args.get("path", "/")
            summary = file_service.summarize(path)
            return json_api_response(
                {
                    "id": "/",
                    "type": "summary",
                    "attributes": {
                        "size": summary.get("size", 0),
                        "files": summary.get("numFiles", 0),
                        "folders": summary.get("numDirs", 0),
                        "sizeLimit": config.get("max_file_size", 104857600),
                    },
                }
            )

        if mode == "extract":
            source = get_param("source")
            destination = get_param("destination", "/")
            if not source:
                return json_api_error("Source required", "400", 400)
            result = file_service.extract_archive(source, destination)
            return json_api_response(
                {
                    "id": destination,
                    "type": "folder",
                    "attributes": build_file_attributes(result, destination),
                }
            )

        else:
            return json_api_error(f"Unknown mode: {mode}", "400", 400)

    except Exception as e:
        error_response, status_code = handle_error(e)
        return error_response, status_code


@rich_filemanager.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    version = _get_version()
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return jsonify(
        {
            "status": "healthy",
            "version": version,
            "database": db_status,
        }
    )


@rich_filemanager.route("/docs", methods=["GET"])
def api_docs():
    """OpenAPI documentation endpoint."""
    return jsonify(
        {
            "openapi": "3.0.0",
            "info": {
                "title": "RichFM API",
                "version": "1.0.0",
                "description": "Rich Filemanager Flask Blueprint API",
            },
        }
    )


def _get_version() -> str:
    """Get version."""
    try:
        from richfm import __about__

        return __about__.__version__
    except ImportError:
        return "1.0.0"


def create_rich_filemanager_blueprint(import_name: str = __name__) -> Blueprint:
    """Factory function to create the Rich Filemanager Blueprint."""
    return rich_filemanager
