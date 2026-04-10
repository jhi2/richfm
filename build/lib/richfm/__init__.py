"""Flask application factory for RichFM."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from flask import Flask
from flask_cors import CORS

from richfm.blueprint.filemanager import rich_filemanager
from richfm.blueprint.ui import create_ui_blueprint
from richfm.config import RichFMSettings, create_default_config, settings
from richfm.models.session import db

if TYPE_CHECKING:
    from richfm.config import RichFMSettings


def _get_version() -> str:
    """Get version string."""
    try:
        from richfm import __about__

        return __about__.__version__
    except ImportError:
        return "1.0.0"


def create_app(config: Optional[RichFMSettings] = None) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)

    if config is None:
        config = settings

    app.config["SECRET_KEY"] = config.secret_key
    app.config["DEBUG"] = config.debug
    app.config["SQLALCHEMY_DATABASE_URI"] = config.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    CORS(
        app,
        origins=config.cors_origins.split(",") if config.cors_origins != "*" else "*",
        supports_credentials=True,
    )

    app.register_blueprint(rich_filemanager, url_prefix="/filemanager")

    # Register UI blueprint at /fileui/
    ui_blueprint = create_ui_blueprint()
    app.register_blueprint(ui_blueprint, url_prefix="/fileui")

    _configure_logging(app, config)

    with app.app_context():
        db.create_all()

    app.config["RICHFm_VERSION"] = _get_version()

    return app


def _configure_logging(app: Flask, config: RichFMSettings) -> None:
    """Configure application logging."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    config.logs_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(str(config.logs_dir / "richfm.log")),
            logging.StreamHandler(),
        ],
    )

    app.logger.setLevel(log_level)


def create_app_with_defaults() -> Flask:
    """Create app with default configuration and directories."""
    for directory in [settings.uploads_dir, settings.sessions_dir, settings.logs_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    config_path = settings.base_dir / "richfm_config.yaml"
    if not config_path.exists():
        import yaml

        with open(config_path, "w") as f:
            yaml.dump(create_default_config(config_path), f)

    return create_app()


if __name__ == "__main__":
    app = create_app_with_defaults()
    app.run(host="0.0.0.0", port=5000, debug=True)
