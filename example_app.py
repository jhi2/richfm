#!/usr/bin/env python3
"""Example Flask application using RichFM Blueprint."""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from richfm import create_app

app = create_app()

if __name__ == "__main__":
    print("Starting RichFM File Manager...")
    print("Access the UI at: http://localhost:5000/")
    print("API endpoints at: http://localhost:5000/filemanager/")
    app.run(host="0.0.0.0", port=5000, debug=True)
