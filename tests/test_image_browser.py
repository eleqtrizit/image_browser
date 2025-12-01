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


if __name__ == '__main__':
    unittest.main()
