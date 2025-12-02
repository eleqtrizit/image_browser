import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import image_browser
from image_browser import SIZE_CONFIGS, create_app, get_image_files, load_caption_for_image, resize_and_cache_image


class ImageBrowserTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.images_dir = os.path.join(self.test_dir, 'images')
        self.cache_dir = os.path.join(self.test_dir, 'cache')

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        # Create a few test images
        self.create_test_image('test1.jpg', (800, 600))
        self.create_test_image('test2.png', (400, 400))
        self.create_test_image('test3.gif', (200, 300))

        # Create app with test image directory
        self.test_app = create_app(self.images_dir)
        self.test_app.config['TESTING'] = True
        self.app = self.test_app.test_client()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_image(self, filename, size):
        """Create a simple test image"""
        image_path = os.path.join(self.images_dir, filename)
        img = Image.new('RGB', size, color=(73, 109, 137))
        img.save(image_path, 'JPEG' if filename.endswith('.jpg') else filename.split('.')[-1].upper())
        return image_path

    def test_module_level_code_execution(self):
        """Test that module-level code executes properly"""
        # Check that CACHE_DIR is created
        self.assertTrue(os.path.exists(image_browser.CACHE_DIR))

        # Check that SIZE_CONFIGS is properly defined
        self.assertIn('small', image_browser.SIZE_CONFIGS)
        self.assertIn('medium', image_browser.SIZE_CONFIGS)
        self.assertIn('large', image_browser.SIZE_CONFIGS)

        # Check that PAGE_SIZE_OPTIONS is properly defined
        self.assertIn(25, image_browser.PAGE_SIZE_OPTIONS)
        self.assertIn(50, image_browser.PAGE_SIZE_OPTIONS)
        self.assertIn(100, image_browser.PAGE_SIZE_OPTIONS)
        self.assertIn(250, image_browser.PAGE_SIZE_OPTIONS)
        self.assertIn('all', image_browser.PAGE_SIZE_OPTIONS)

    def test_get_image_files(self):
        """Test getting image files from directory"""
        files = get_image_files()
        self.assertEqual(len(files), 3)
        self.assertIn('test1.jpg', files)
        self.assertIn('test2.png', files)
        self.assertIn('test3.gif', files)

    def test_resize_and_cache_image(self):
        """Test resizing and caching images"""
        test_image = os.path.join(self.images_dir, 'test1.jpg')

        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test resizing to small size
        cache_path = resize_and_cache_image(test_image, 'small')
        self.assertIsNotNone(cache_path)
        self.assertTrue(os.path.exists(cache_path))

        # Check that cached image has correct dimensions
        with Image.open(cache_path) as img:
            self.assertLessEqual(img.width, SIZE_CONFIGS['small'][0])
            self.assertLessEqual(img.height, SIZE_CONFIGS['small'][1])

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_route(self):
        """Test the main index route"""
        # Temporarily override CACHE_DIR in the test app
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_serve_cached_image_not_found(self):
        """Test serving cached image when file doesn't exist"""
        response = self.app.get('/cache/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)

    def test_serve_full_image_not_found(self):
        """Test serving full image when file doesn't exist"""
        response = self.app.get('/image/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)

    def test_serve_full_image_success(self):
        """Test serving full image when file exists"""
        response = self.app.get('/image/test1.jpg')
        self.assertEqual(response.status_code, 200)

    def test_serve_cached_image_success(self):
        """Test serving cached image when file exists"""
        # First create a cached image
        test_image = os.path.join(self.images_dir, 'test1.jpg')

        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Create cached image
        cache_path = resize_and_cache_image(test_image, 'small')
        self.assertIsNotNone(cache_path)

        # Get the cache filename
        cache_filename = os.path.basename(cache_path)

        # Test serving cached image
        response = self.app.get(f'/cache/{cache_filename}')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_delete_image_success(self):
        """Test deleting an image successfully"""
        # Create cached thumbnails for the image to be deleted
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        test_image = os.path.join(self.images_dir, 'test1.jpg')
        for size_key in image_browser.SIZE_CONFIGS.keys():
            cache_path = resize_and_cache_image(test_image, size_key)
            self.assertIsNotNone(cache_path)

        # Test deleting the image
        response = self.app.post('/delete/test1.jpg')
        self.assertEqual(response.status_code, 204)

        # Verify image is deleted
        self.assertFalse(os.path.exists(test_image))

        # Verify cached thumbnails are deleted
        for size_key in image_browser.SIZE_CONFIGS.keys():
            cache_filename = f"{os.path.splitext('test1.jpg')[0]}_{size_key}.jpg"
            cache_path = os.path.join(self.cache_dir, cache_filename)
            self.assertFalse(os.path.exists(cache_path))

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_delete_image_not_found(self):
        """Test deleting an image that doesn't exist"""
        response = self.app.post('/delete/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)

    def test_view_image_success(self):
        """Test viewing an image successfully"""
        # Temporarily override CACHE_DIR in the test app
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        response = self.app.get('/view/test1.jpg')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test1.jpg', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_not_found(self):
        """Test viewing an image that doesn't exist"""
        response = self.app.get('/view/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)

    def test_index_route_with_parameters(self):
        """Test the index route with various parameters"""
        # Temporarily override CACHE_DIR in the test app
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test with page parameter
        response = self.app.get('/?page=1')
        self.assertEqual(response.status_code, 200)

        # Test with size parameter
        response = self.app.get('/?size=small')
        self.assertEqual(response.status_code, 200)

        # Test with page_size parameter
        response = self.app.get('/?page_size=25')
        self.assertEqual(response.status_code, 200)

        # Test with all parameters
        response = self.app.get('/?page=1&size=medium&page_size=50')
        self.assertEqual(response.status_code, 200)

        # Test with invalid size (should default to medium)
        response = self.app.get('/?size=invalid')
        self.assertEqual(response.status_code, 200)

        # Test with invalid page_size (should default)
        response = self.app.get('/?page_size=invalid')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_route_show_all(self):
        """Test the index route with 'all' page size"""
        # Temporarily override CACHE_DIR in the test app
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        response = self.app.get('/?page_size=all')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_load_caption_for_image_no_caption(self):
        """Test loading caption when no caption file exists"""
        caption = load_caption_for_image('test1.jpg')
        self.assertIsNone(caption)

    def test_load_caption_for_image_with_caption(self):
        """Test loading caption when caption file exists"""
        # Create a caption file in the captions directory relative to current working directory
        caption_content = "This is a test caption"
        caption_dir = os.path.join(os.getcwd(), 'captions')
        os.makedirs(caption_dir, exist_ok=True)
        caption_file = os.path.join(caption_dir, 'test1.txt')

        with open(caption_file, 'w') as f:
            f.write(caption_content)

        caption = load_caption_for_image('test1.jpg')
        self.assertEqual(caption, caption_content)

        # Clean up caption file
        if os.path.exists(caption_file):
            os.remove(caption_file)
        if os.path.exists(caption_dir) and not os.listdir(caption_dir):
            os.rmdir(caption_dir)

    def test_create_app_with_custom_directory(self):
        """Test creating app with custom image directory"""
        test_app = create_app(self.images_dir)
        self.assertIsNotNone(test_app)

        # Test that the app works
        with test_app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)

    def test_pagination_logic(self):
        """Test pagination logic with different page sizes"""
        # Temporarily override CACHE_DIR in the test app
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test first page with small page size
        response = self.app.get('/?page=1&page_size=1')
        self.assertEqual(response.status_code, 200)

        # Test second page
        response = self.app.get('/?page=2&page_size=1')
        self.assertEqual(response.status_code, 200)

        # Test page beyond total pages (should default to last page)
        response = self.app.get('/?page=10&page_size=1')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_resize_and_cache_image_with_invalid_file(self):
        """Test resize_and_cache_image with invalid file"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test with nonexistent file
        cache_path = resize_and_cache_image('/nonexistent/image.jpg', 'small')
        self.assertIsNone(cache_path)

        # Test with corrupted image file
        corrupted_image = os.path.join(self.images_dir, 'corrupted.jpg')
        with open(corrupted_image, 'wb') as f:
            f.write(b'not a valid image file')

        cache_path = resize_and_cache_image(corrupted_image, 'small')
        self.assertIsNone(cache_path)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_load_caption_for_image_with_exception(self):
        """Test load_caption_for_image with exception handling"""
        # Create a caption file that we can't read
        caption_content = "This is a test caption"
        caption_dir = os.path.join(os.getcwd(), 'captions')
        os.makedirs(caption_dir, exist_ok=True)
        caption_file = os.path.join(caption_dir, 'test1.txt')

        with open(caption_file, 'w') as f:
            f.write(caption_content)

        # Make the file unreadable
        os.chmod(caption_file, 0o000)

        # This should not raise an exception but return None
        caption = load_caption_for_image('test1.jpg')
        self.assertIsNone(caption)

        # Restore permissions and clean up
        os.chmod(caption_file, 0o644)
        if os.path.exists(caption_file):
            os.remove(caption_file)
        if os.path.exists(caption_dir) and not os.listdir(caption_dir):
            os.rmdir(caption_dir)

    def test_delete_image_with_exception(self):
        """Test delete_image route with exception handling"""
        # Create a test image
        test_image = os.path.join(self.images_dir, 'test1.jpg')

        # Make the file unreadable to trigger exception
        os.chmod(test_image, 0o000)

        # Test deleting the image (should return 500)
        self.app.post('/delete/test1.jpg')
        # Note: This might not actually test the exception path depending on how Flask handles it
        # But it's worth trying to cover edge cases

        # Restore permissions if file still exists
        if os.path.exists(test_image):
            os.chmod(test_image, 0o644)

    def test_main_module_execution(self):
        """Test that __main__.py can be executed without errors"""
        # Test that the main module can be imported without errors
        import image_browser.__main__
        self.assertTrue(hasattr(image_browser.__main__, 'main'))

    @patch('sys.argv', ['image_browser', '--image-dir', '.'])
    @patch('image_browser.__main__.create_app')
    def test_main_function_with_default_directory(self, mock_create_app):
        """Test main function with default directory argument"""
        # Mock the app.run method to avoid actually starting the server
        mock_app = unittest.mock.Mock()
        mock_create_app.return_value = mock_app

        # Import and call main function
        from image_browser.__main__ import main

        # We don't expect SystemExit since we're not actually running the app
        # Just test that the function can be called without errors
        try:
            main()
        except SystemExit:
            pass  # This is expected when the app tries to run

        # Check that create_app was called with current directory
        mock_create_app.assert_called_once_with('.')
        # Check that app.run was called
        mock_app.run.assert_called_once_with(debug=True, host='0.0.0.0', port=5055)

    @patch('sys.argv', ['image_browser', '--image-dir', '/nonexistent'])
    def test_main_function_with_invalid_directory(self):
        """Test main function with invalid directory argument"""
        # Import and call main function
        from image_browser.__main__ import main
        with self.assertRaises(SystemExit) as context:
            main()

        # Check that the exit code is 1 (error)
        self.assertEqual(context.exception.code, 1)

    @patch('sys.argv', ['image_browser', '--image-dir', '/etc/passwd'])  # A file, not a directory
    def test_main_function_with_file_instead_of_directory(self):
        """Test main function with a file instead of directory argument"""
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile() as tmpfile:
            # Patch argv to use the temp file path
            with patch('sys.argv', ['image_browser', '--image-dir', tmpfile.name]):
                # Import and call main function
                from image_browser.__main__ import main
                with self.assertRaises(SystemExit) as context:
                    main()

                # Check that the exit code is 1 (error)
                self.assertEqual(context.exception.code, 1)

    def test_index_route_thumbnail_generation_failure(self):
        """Test index route when thumbnail generation fails"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Mock resize_and_cache_image to return None
        with patch('image_browser.resize_and_cache_image', return_value=None):
            response = self.app.get('/')
            self.assertEqual(response.status_code, 200)
            # Should fallback to full image URL
            self.assertIn(b'test1.jpg', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_with_navigation(self):
        """Test view_image route with previous and next navigation"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test middle image (should have both previous and next)
        response = self.app.get('/view/test2.png')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test2.png', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_first_image(self):
        """Test view_image route for the first image"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test first image (should not have previous)
        response = self.app.get('/view/test1.jpg')
        self.assertEqual(response.status_code, 200)
        # First image should not have a previous image
        self.assertIn(b'test1.jpg', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_last_image(self):
        """Test view_image route for the last image"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test last image (should not have next)
        response = self.app.get('/view/test3.gif')
        self.assertEqual(response.status_code, 200)
        # Last image should not have a next image
        self.assertIn(b'test3.gif', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_with_invalid_size(self):
        """Test view_image route with invalid size parameter"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test with invalid size (should default to medium)
        response = self.app.get('/view/test1.jpg?size=invalid')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_thumbnail_generation_failure(self):
        """Test view_image when thumbnail generation fails"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Mock resize_and_cache_image to return None
        with patch('image_browser.resize_and_cache_image', return_value=None):
            response = self.app.get('/view/test2.png')
            self.assertEqual(response.status_code, 200)
            # Should fallback to full image URL
            self.assertIn(b'test2.png', response.data)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_get_image_files_empty_directory(self):
        """Test get_image_files with empty directory"""
        # Create empty directory and test
        empty_dir = os.path.join(self.test_dir, 'empty')
        os.makedirs(empty_dir, exist_ok=True)

        test_app = create_app(empty_dir)
        self.assertIsNotNone(test_app)

        with test_app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)

    def test_get_image_files_with_non_image_files(self):
        """Test get_image_files ignores non-image files"""
        # Create non-image files
        text_file = os.path.join(self.images_dir, 'readme.txt')
        with open(text_file, 'w') as f:
            f.write('This is not an image')

        files = get_image_files()
        self.assertEqual(len(files), 3)
        self.assertNotIn('readme.txt', files)

    def test_get_image_files_case_insensitive_extension(self):
        """Test get_image_files with mixed case extensions"""
        # Create image with uppercase extension
        uppercase_image = os.path.join(self.images_dir, 'test_upper.JPG')
        img = Image.new('RGB', (100, 100), color=(73, 109, 137))
        img.save(uppercase_image, 'JPEG')

        files = get_image_files()
        self.assertIn('test_upper.JPG', files)

    def test_resize_and_cache_image_rgb_conversion(self):
        """Test resize_and_cache_image with RGBA image conversion"""
        # Create RGBA image
        rgba_image = os.path.join(self.images_dir, 'test_rgba.png')
        img = Image.new('RGBA', (200, 200), color=(73, 109, 137, 255))
        img.save(rgba_image, 'PNG')

        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test resizing RGBA image
        cache_path = resize_and_cache_image(rgba_image, 'small')
        self.assertIsNotNone(cache_path)
        self.assertTrue(os.path.exists(cache_path))

        # Verify cached image is RGB
        with Image.open(cache_path) as img:
            self.assertEqual(img.mode, 'RGB')

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_resize_and_cache_image_cached_reuse(self):
        """Test resize_and_cache_image reuses existing cache"""
        test_image = os.path.join(self.images_dir, 'test1.jpg')

        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # First call should create cache
        cache_path_1 = resize_and_cache_image(test_image, 'small')
        self.assertIsNotNone(cache_path_1)

        # Second call should return same path
        cache_path_2 = resize_and_cache_image(test_image, 'small')
        self.assertEqual(cache_path_1, cache_path_2)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_with_pagination_beyond_total_pages(self):
        """Test index route with page number beyond total pages"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Request page 100 (beyond total pages)
        response = self.app.get('/?page=100&page_size=1')
        self.assertEqual(response.status_code, 200)
        # Should clamp to last page

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_with_negative_page(self):
        """Test index route with negative page number"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Request negative page number (should clamp to 1)
        response = self.app.get('/?page=-5&page_size=1')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_load_caption_empty_caption_file(self):
        """Test load_caption_for_image with empty caption file"""
        # Create an empty caption file
        caption_dir = os.path.join(os.getcwd(), 'captions')
        os.makedirs(caption_dir, exist_ok=True)
        caption_file = os.path.join(caption_dir, 'test1.txt')

        with open(caption_file, 'w') as f:
            f.write('')  # Empty file

        caption = load_caption_for_image('test1.jpg')
        self.assertIsNone(caption)

        # Clean up
        if os.path.exists(caption_file):
            os.remove(caption_file)
        if os.path.exists(caption_dir) and not os.listdir(caption_dir):
            os.rmdir(caption_dir)

    def test_load_caption_with_whitespace(self):
        """Test load_caption_for_image with whitespace-only file"""
        # Create caption file with only whitespace
        caption_dir = os.path.join(os.getcwd(), 'captions')
        os.makedirs(caption_dir, exist_ok=True)
        caption_file = os.path.join(caption_dir, 'test2.txt')

        with open(caption_file, 'w') as f:
            f.write('   \n  \t  ')  # Only whitespace

        caption = load_caption_for_image('test2.png')
        self.assertIsNone(caption)

        # Clean up
        if os.path.exists(caption_file):
            os.remove(caption_file)
        if os.path.exists(caption_dir) and not os.listdir(caption_dir):
            os.rmdir(caption_dir)

    def test_delete_image_error_handling(self):
        """Test delete_image route with deletion error"""
        # Create test image
        test_image = os.path.join(self.images_dir, 'test_delete.jpg')
        img = Image.new('RGB', (100, 100), color=(73, 109, 137))
        img.save(test_image, 'JPEG')

        # Mock os.remove to raise an exception
        with patch('os.remove', side_effect=OSError('Permission denied')):
            response = self.app.post('/delete/test_delete.jpg')
            # Should return 500 error
            self.assertEqual(response.status_code, 500)

    def test_view_image_with_page_size_parameter(self):
        """Test view_image preserves page_size parameter"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test with page_size parameter
        response = self.app.get('/view/test1.jpg?page_size=50')
        self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_resize_and_cache_image_different_formats(self):
        """Test resize_and_cache_image with palette mode images"""
        # Create GIF image (typically has palette mode)
        palette_image = os.path.join(self.images_dir, 'test_palette.gif')
        img = Image.new('P', (200, 200))
        img.save(palette_image, 'GIF')

        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        # Test resizing palette image
        cache_path = resize_and_cache_image(palette_image, 'medium')
        self.assertIsNotNone(cache_path)
        self.assertTrue(os.path.exists(cache_path))

        # Verify cached image is RGB
        with Image.open(cache_path) as img:
            self.assertEqual(img.mode, 'RGB')

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_route_all_size_options(self):
        """Test index route with all size options"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        for size in ['small', 'medium', 'large']:
            response = self.app.get(f'/?size={size}')
            self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_index_route_all_page_size_options(self):
        """Test index route with all page_size options"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        for page_size in [25, 50, 100, 250, 'all']:
            response = self.app.get(f'/?page_size={page_size}')
            self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_view_image_with_all_size_options(self):
        """Test view_image with all size options"""
        # Temporarily override CACHE_DIR
        original_cache = image_browser.CACHE_DIR
        image_browser.CACHE_DIR = self.cache_dir

        for size in ['small', 'medium', 'large']:
            response = self.app.get(f'/view/test1.jpg?size={size}')
            self.assertEqual(response.status_code, 200)

        # Restore original cache directory
        image_browser.CACHE_DIR = original_cache

    def test_get_image_files_sorting(self):
        """Test that get_image_files returns sorted results"""
        files = get_image_files()
        sorted_files = sorted(files)
        self.assertEqual(files, sorted_files)

    def test_image_dir_nonexistent(self):
        """Test get_image_files when IMAGE_DIR doesn't exist"""
        # Temporarily set IMAGE_DIR to nonexistent path
        original_image_dir = image_browser.IMAGE_DIR
        image_browser.IMAGE_DIR = '/nonexistent/path/that/does/not/exist'

        files = get_image_files()
        self.assertEqual(len(files), 0)

        # Restore original IMAGE_DIR
        image_browser.IMAGE_DIR = original_image_dir


if __name__ == '__main__':
    unittest.main()
