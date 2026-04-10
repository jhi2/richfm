from setuptools import setup, find_packages
import os

# Include UI files and other static files
ui_files = []
ui_dir = "ui"
if os.path.exists(ui_dir):
    for root, dirs, files in os.walk(ui_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, ".")
            ui_files.append(rel_path)

setup(
    name="richfm",
    version="1.0.0",
    description="Rich Filemanager Flask Blueprint Wrapper",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    author="Johnny",
    author_email="johndrostan@outlook.com",
    url="https://github.com/richfm/richfm",
    keywords=["flask", "filemanager", "richfilemanager", "blueprint"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    data_files=ui_files,
    install_requires=[
        "Flask>=2.3.0",
        "Flask-SQLAlchemy>=3.0.0",
        "Flask-CORS>=4.0.0",
        "SQLAlchemy>=2.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0.0",
        "Pillow>=10.0.0",
        "structlog>=23.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.12.0",
            "mypy>=1.0.0",
            "black>=23.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
