import argparse
import os
import sys

# Import create_app from the package
from . import create_app


def main():
    """Main entry point for the image browser application."""
    parser = argparse.ArgumentParser(description='Image Browser Application')
    parser.add_argument('--image-dir', '-d',
                        help='Path to the directory containing images (default: current directory)',
                        default=os.getcwd())
    args = parser.parse_args()

    # Validate image directory
    if not os.path.exists(args.image_dir):
        print(f"Error: Image directory '{args.image_dir}' does not exist.")
        sys.exit(1)

    if not os.path.isdir(args.image_dir):
        print(f"Error: '{args.image_dir}' is not a directory.")
        sys.exit(1)

    # Create app with specified image directory
    app = create_app(args.image_dir)

    app.run(debug=True, host='0.0.0.0', port=5055)


if __name__ == '__main__':
    main()
