import os
import math
from flask import Flask, render_template, request, send_file, abort
from PIL import Image
import threading

app = Flask(__name__)

# Configuration
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = '/tmp/image_browser'
IMAGES_PER_PAGE = 12

# Page size options
PAGE_SIZE_OPTIONS = [25, 50, 100, 250, 'all']

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

# Size configurations
SIZE_CONFIGS = {
    'small': (150, 150),
    'medium': (300, 300),
    'large': (600, 600)
}

def get_image_files():
    """Get all image files from the images directory"""
    extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
    image_files = []

    if os.path.exists(IMAGE_DIR):
        for filename in os.listdir(IMAGE_DIR):
            if filename.lower().endswith(extensions):
                image_files.append(filename)

    # Sort files alphabetically
    image_files.sort()
    return image_files


def load_caption_for_image(filename):
    """Load caption for an image file if it exists"""
    # Get the base name without extension
    base_name = os.path.splitext(filename)[0]
    caption_filename = f"{base_name}.txt"
    caption_path = os.path.join('captions', caption_filename)

    # Check if caption file exists
    if os.path.exists(caption_path):
        try:
            with open(caption_path, 'r', encoding='utf-8') as f:
                caption = f.read().strip()
                return caption if caption else None
        except Exception as e:
            print(f"Error reading caption for {filename}: {e}")
            return None
    return None

def resize_and_cache_image(image_path, size_key):
    """Resize an image and cache it"""
    size = SIZE_CONFIGS[size_key]
    cache_filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_{size_key}.jpg"
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    # If cached image already exists, return its path
    if os.path.exists(cache_path):
        return cache_path

    try:
        # Open and resize the image
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Calculate aspect ratio preserving dimensions
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Save resized image to cache
            img.save(cache_path, 'JPEG', quality=85, optimize=True)

        return cache_path
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

@app.route('/')
def index():
    # Get page number, size, and page size from request arguments
    page = int(request.args.get('page', 1))
    size = request.args.get('size', 'medium')
    page_size = request.args.get('page_size', '12')  # Default to 12 for backward compatibility

    # Validate size parameter
    if size not in SIZE_CONFIGS:
        size = 'medium'

    # Validate page_size parameter
    if page_size == 'all':
        images_per_page = None  # Show all images
    else:
        try:
            images_per_page = int(page_size)
            # Check if the page size is in our allowed options (excluding 'all' since it's not an int)
            if images_per_page not in [25, 50, 100, 250]:
                images_per_page = IMAGES_PER_PAGE  # Default to 12 if invalid
        except ValueError:
            images_per_page = IMAGES_PER_PAGE  # Default to 12 if not a number

    # Get all image files
    image_files = get_image_files()

    # Calculate pagination
    total_images = len(image_files)

    if images_per_page is None:  # Show all images
        total_pages = 1
        page = 1
        page_images = image_files
    else:
        total_pages = max(1, math.ceil(total_images / images_per_page))

        # Ensure page is within valid range
        page = max(1, min(page, total_pages))

        # Calculate start and end indices for current page
        start_idx = (page - 1) * images_per_page
        end_idx = start_idx + images_per_page
        page_images = image_files[start_idx:end_idx]

    # Prepare image data for template
    images_data = []
    for filename in page_images:
        image_path = os.path.join(IMAGE_DIR, filename)
        if os.path.exists(image_path):
            # Generate and cache the thumbnail
            cache_path = resize_and_cache_image(image_path, size)
            if cache_path:
                # Generate cache URL for the thumbnail
                cache_filename = os.path.basename(cache_path)
                cache_url = f"/cache/{cache_filename}"
                images_data.append({
                    'filename': filename,
                    'cache_url': cache_url,
                    'full_url': f"/image/{filename}",
                    'caption': load_caption_for_image(filename)
                })
            else:
                # Fallback to full image if thumbnail generation fails
                images_data.append({
                    'filename': filename,
                    'cache_url': f"/image/{filename}",
                    'full_url': f"/image/{filename}",
                    'caption': load_caption_for_image(filename)
                })

    return render_template('index.html',
                          images=images_data,
                          current_page=page,
                          total_pages=total_pages,
                          current_size=size,
                          sizes=list(SIZE_CONFIGS.keys()),
                          page_size_options=PAGE_SIZE_OPTIONS,
                          current_page_size=page_size,
                          total_images=total_images)

@app.route('/cache/<filename>')
def serve_cached_image(filename):
    """Serve a cached resized image"""
    cache_path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(cache_path):
        return send_file(cache_path)
    else:
        # If cache doesn't exist, return 404
        abort(404)

@app.route('/image/<filename>')
def serve_full_image(filename):
    """Serve a full-size image"""
    image_path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(image_path):
        return send_file(image_path)
    else:
        abort(404)


@app.route('/delete/<filename>', methods=['POST'])
def delete_image(filename):
    """Delete an image file"""
    image_path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
            # Also remove cached thumbnails for this image
            for size_key in SIZE_CONFIGS.keys():
                cache_filename = f"{os.path.splitext(filename)[0]}_{size_key}.jpg"
                cache_path = os.path.join(CACHE_DIR, cache_filename)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
            return '', 204  # Success, no content
        except Exception as e:
            print(f"Error deleting image {filename}: {e}")
            abort(500)
    else:
        abort(404)

@app.route('/view/<filename>')
def view_image(filename):
    """Display a single image with navigation controls"""
    # Get all image files
    image_files = get_image_files()

    # Check if requested file exists
    if filename not in image_files:
        abort(404)

    # Find current index
    current_index = image_files.index(filename)

    # Determine previous and next images
    prev_filename = image_files[current_index - 1] if current_index > 0 else None
    next_filename = image_files[current_index + 1] if current_index < len(image_files) - 1 else None

    # Get thumbnail URLs for navigation
    current_size = request.args.get('size', 'medium')
    if current_size not in SIZE_CONFIGS:
        current_size = 'medium'

    # Get page size parameter to pass back to gallery
    page_size = request.args.get('page_size', '12')

    # Generate thumbnails for previous, current, and next images
    prev_thumb_url = None
    if prev_filename:
        prev_image_path = os.path.join(IMAGE_DIR, prev_filename)
        if os.path.exists(prev_image_path):
            prev_cache_path = resize_and_cache_image(prev_image_path, current_size)
            if prev_cache_path:
                prev_cache_filename = os.path.basename(prev_cache_path)
                prev_thumb_url = f"/cache/{prev_cache_filename}"
            else:
                prev_thumb_url = f"/image/{prev_filename}"

    next_thumb_url = None
    if next_filename:
        next_image_path = os.path.join(IMAGE_DIR, next_filename)
        if os.path.exists(next_image_path):
            next_cache_path = resize_and_cache_image(next_image_path, current_size)
            if next_cache_path:
                next_cache_filename = os.path.basename(next_cache_path)
                next_thumb_url = f"/cache/{next_cache_filename}"
            else:
                next_thumb_url = f"/image/{next_filename}"

    # Get full image URL
    full_image_url = f"/image/{filename}"

    # Generate and get thumbnail URL for current image
    current_image_path = os.path.join(IMAGE_DIR, filename)
    current_cache_path = resize_and_cache_image(current_image_path, current_size)
    if current_cache_path:
        current_cache_filename = os.path.basename(current_cache_path)
        current_thumb_url = f"/cache/{current_cache_filename}"
    else:
        current_thumb_url = f"/image/{filename}"

    # Load caption for current image
    current_caption = load_caption_for_image(filename)

    return render_template('thumbnail_viewer.html',
                          filename=filename,
                          full_image_url=full_image_url,
                          current_thumb_url=current_thumb_url,
                          prev_filename=prev_filename,
                          next_filename=next_filename,
                          prev_thumb_url=prev_thumb_url,
                          next_thumb_url=next_thumb_url,
                          current_index=current_index + 1,
                          total_images=len(image_files),
                          current_size=current_size,
                          current_page_size=page_size,
                          caption=current_caption)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5055)
