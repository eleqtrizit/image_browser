# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application for browsing images in a directory with thumbnail previews. The application allows users to:
- Browse images in a directory with thumbnail previews
- View full-size images with navigation controls
- Delete images from the browser
- Configure thumbnail sizes and pagination
- Add captions to images via accompanying .txt files

## Project Structure

```
image_browser/
├── image_browser/           # Main application package
│   ├── __init__.py         # Core Flask application with routes and logic
│   ├── __main__.py         # Entry point with command-line argument parsing
│   └── templates/          # HTML templates
│       ├── index.html      # Main gallery view
│       └── thumbnail_viewer.html  # Single image viewer
├── tests/                  # Unit tests
│   └── test_image_browser.py
├── README.md               # Project documentation
├── pyproject.toml          # Project configuration and dependencies
├── Makefile                # Development commands
└── CLAUDE.md              # This file
```

## Key Components

### Main Application (`image_browser/__init__.py`)
- Flask application creation and configuration
- Route definitions for:
  - `/` - Main gallery view with pagination and thumbnail generation
  - `/cache/<filename>` - Serving cached thumbnails
  - `/image/<filename>` - Serving full-size images
  - `/delete/<filename>` - Deleting images
  - `/view/<filename>` - Single image viewer with navigation
- Image processing functions for thumbnail generation
- Caption loading functionality

### Entry Point (`image_browser/__main__.py`)
- Command-line argument parsing for specifying image directory
- Application startup with debug mode on port 5055

### Templates
- `index.html` - Responsive grid layout for image gallery
- `thumbnail_viewer.html` - Full-screen image viewer with navigation controls

## Development Commands

### Setup
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync
uv sync --group dev
```

### Running the Application
```bash
# Run with default settings (current directory)
python -m image_browser

# Run with specific image directory
python -m image_browser --image-dir /path/to/your/images
```

### Testing
```bash
# Run tests
make test

# Run tests with coverage
make cov
```

### Code Quality
```bash
# Run linters
make lint

# Format code
make format
```

## Dependencies
- Flask >= 3.1.2
- Pillow >= 12.0.0 (for image processing)
- Rich >= 14.2.0 (for rich terminal output)
- autopep8 >= 2.3.2 (for code formatting)
- flake8 >= 7.3.0 (for linting)
- isort >= 7.0.0 (for import sorting)
- mypy >= 1.19.0 (for type checking)
- pytest >= 9.0.1 (for testing)
- pytest-cov >= 7.0.0 (for test coverage)

## Configuration
- Thumbnail cache directory: `/tmp/image_browser`
- Supported image formats: PNG, JPG, JPEG, GIF, BMP, WEBP
- Default thumbnail sizes: small (150x150), medium (300x300), large (600x600)
- Default images per page: 25
- Page size options: 25, 50, 100, 250, 'all'

## Key Features
1. Thumbnail generation with caching
2. Responsive grid layout
3. Pagination with configurable page sizes
4. Keyboard navigation in image viewer
5. Image deletion with confirmation
6. Caption support via .txt files
7. Navigation direction tracking after deletion
8. Preloading of adjacent images for smoother navigation

## Testing
Unit tests cover:
- Image file discovery
- Thumbnail generation and caching
- Route responses
- Error handling for missing files

Run tests with `make test` or `pytest tests/`.