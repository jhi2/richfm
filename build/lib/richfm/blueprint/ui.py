"""Rich Filemanager UI Blueprint for Flask."""

import json
from pathlib import Path
from typing import Optional

from flask import (
    Blueprint,
    jsonify,
    make_response,
    request,
    render_template_string,
    send_from_directory,
)

ui_bp = Blueprint("richfm_ui", __name__)


def get_ui_path() -> Optional[Path]:
    """Get the path to UI files."""
    # Try multiple locations to find UI files
    possible_paths = [
        # Development: from project root
        Path(__file__).parent.parent.parent.parent / "ui",
        # Installed as package: next to richfm module
        Path(__file__).parent.parent / "richfm" / "ui",
        Path(__file__).parent / "ui",
        # Current working directory
        Path.cwd() / "ui",
    ]

    for ui_dir in possible_paths:
        if ui_dir.exists() and (ui_dir / "index.html").exists():
            return ui_dir

    # Fallback: return first path for error reporting
    return possible_paths[0]  # type: ignore[return-value]


@ui_bp.route("/")
def index():
    """Serve the Rich Filemanager UI."""
    ui_path = get_ui_path()
    if ui_path and (ui_path / "index.html").exists():
        html = (ui_path / "index.html").read_text()

        # Get session_id from URL and set cookie
        session_id = request.args.get("session_id", "")
        response = make_response(render_template_string(html))
        if session_id:
            response.set_cookie("richfm_session", session_id, max_age=86400, path="/")
        return response

    return jsonify(
        {
            "error": "Rich Filemanager UI not found",
            "message": "UI files not found. Please ensure ui/ directory exists.",
        }
    ), 404


# Serve all static files with various path prefixes the UI expects
@ui_bp.route("/src/css/<path:filename>")
def serve_src_css(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "src" / "css", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/src/js/<path:filename>")
def serve_src_js(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "src" / "js", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/src/templates/<path:filename>")
def serve_src_templates(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "src" / "templates", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/css/<path:filename>")
def serve_css(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "src" / "css", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/js/<path:filename>")
def serve_js(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "src" / "js", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/themes/<path:filename>")
def serve_themes(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "themes", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/themes/css/<path:filename>")
def serve_themes_css(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "themes" / "css", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/themes/images/<path:filename>")
def serve_themes_images(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "themes" / "images", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/libs/<path:filename>")
def serve_libs(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "libs", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/libs/css/<path:filename>")
def serve_libs_css(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "libs" / "css", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/libs/js/<path:filename>")
def serve_libs_js(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "libs" / "js", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/images/<path:filename>")
def serve_images(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "images", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/connectors/<path:filename>")
def serve_connectors(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "connectors", filename)
    return jsonify({"error": "Not found"}), 404


@ui_bp.route("/userfiles/<path:filename>")
def serve_userfiles(filename: str):
    ui_path = get_ui_path()
    if ui_path:
        return send_from_directory(ui_path / "userfiles", filename)
    return jsonify({"error": "Not found"}), 404


# Config file routes (these are what the UI JavaScript expects)
@ui_bp.route("/config/filemanager.config.json")
def config_json():
    ui_path = get_ui_path()
    if ui_path and (ui_path / "config" / "filemanager.config.json").exists():
        config_path = ui_path / "config" / "filemanager.config.json"
        with open(config_path) as f:
            config = json.load(f)

        # Get session_id from URL query params or cookie
        session_id = (
            request.args.get("session_id")
            or request.cookies.get("rfm_session")
            or request.cookies.get("richfm_session", "")
        )

        # If no session, check if it's anywhere in query string (for caching scenarios)
        if not session_id:
            for k, v in request.args.items():
                if len(v) == 36 and v.count("-") == 4:
                    session_id = v
                    break

        if "api" in config:
            config["api"]["connectorUrl"] = "/filemanager/"
            # Pass session_id to all API requests
            config["api"]["requestParams"] = {
                "GET": {"session_id": session_id},
                "POST": {"session_id": session_id},
                "MIXED": {"session_id": session_id},
            }

        response = jsonify(config)
        # No caching - always include fresh session_id
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Set cookie so subsequent requests have session_id
        if session_id:
            response.set_cookie("richfm_session", session_id, max_age=86400, path="/")
        return response

    return jsonify({"error": "Config not found"}), 404


@ui_bp.route("/config/filemanager.config.default.json")
def config_default_json():
    ui_path = get_ui_path()
    if ui_path and (ui_path / "config" / "filemanager.config.default.json").exists():
        config_path = ui_path / "config" / "filemanager.config.default.json"
        with open(config_path) as f:
            config = json.load(f)

        if "api" in config:
            config["api"]["connectorUrl"] = "/filemanager/"

        return jsonify(config)

    return jsonify({"error": "Config not found"}), 404


@ui_bp.route("/config/filemanager.init.js")
def config_js():
    """Serve init JS."""
    ui_path = get_ui_path()
    if ui_path and (ui_path / "config" / "filemanager.init.js.example").exists():
        init_path = ui_path / "config" / "filemanager.init.js.example"
        content = init_path.read_text()
        return content, 200, {"Content-Type": "application/javascript"}
    return "{}", 404


@ui_bp.route("/languages/<lang>.json")
def language(lang: str):
    ui_path = get_ui_path()
    if ui_path:
        lang_path = ui_path / "languages" / f"{lang}.json"
        if lang_path.exists():
            return send_from_directory(ui_path / "languages", f"{lang}.json")
    return jsonify({})


def create_ui_blueprint() -> Blueprint:
    return ui_bp
