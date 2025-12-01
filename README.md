# Image Browser

A simple Flask-based web application for browsing images in a directory with thumbnail previews.

## Features

- Browse images in a directory with thumbnail previews
- View full-size images with navigation controls
- Delete images from the browser
- Responsive grid layout with configurable thumbnail sizes
- Pagination support for large image collections
- Caption support for images (via accompanying .txt files)


### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

## Installation with uv

```
uv tool install git+https://github.com/eleqtrizit/image_browser.git
```

That's it!

## Setup for Development

1. Clone the repository:
   ```bash
   git clone https://github.com/eleqtrizit/image_browser
   cd image_browser
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync
   uv sync --group dev
   ```

3. Run the application:
   ```bash
   python -m image_browser --image-dir /path/to/your/images
   ```

   By default, the application will run on `http://localhost:5055` and serve images from the current directory.

### Development Tools

To run tests:
```bash
make test # or make cov
```

To run linting:
```bash
make lint
```

To format code:
```bash
make format
```

## Usage

Navigate to `http://localhost:5055` in your browser to view the image gallery.


### Command Line Arguments

- `--image-dir` or `-d`: Path to the directory containing images (default: current directory)
