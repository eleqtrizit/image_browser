import os
import shutil
import tempfile
import unittest

from PIL import Image

from image_browser import SIZE_CONFIGS, app, get_image_files, resize_and_cache_image


class ImageBrowserTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.app.testing = True

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

        # Update app configuration for testing
        app.config['TESTING'] = True

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_image(self, filename, size):
        """Create a simple test image"""
        image_path = os.path.join(self.images_dir, filename)
        img = Image.new('RGB', size, color=(73, 109, 137))
        img.save(image_path, 'JPEG' if filename.endswith('.jpg') else filename.split('.')[-1].upper())
        return image_path

    def test_get_image_files(self):
        """Test getting image files from directory"""
        # Temporarily override IMAGE_DIR
        import image_browser
        original_dir = image_browser.IMAGE_DIR
        image_browser.IMAGE_DIR = self.images_dir

        files = get_image_files()
        self.assertEqual(len(files), 3)
        self.assertIn('test1.jpg', files)
        self.assertIn('test2.png', files)
        self.assertIn('test3.gif', files)

        # Restore original directory
        image_browser.IMAGE_DIR = original_dir

    def test_resize_and_cache_image(self):
        """Test resizing and caching images"""
        test_image = os.path.join(self.images_dir, 'test1.jpg')

        # Temporarily override CACHE_DIR
        import image_browser
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
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_serve_cached_image_not_found(self):
        """Test serving cached image when file doesn't exist"""
        response = self.app.get('/cache/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)

    def test_serve_full_image_not_found(self):
        """Test serving full image when file doesn't exist"""
        response = self.app.get('/image/nonexistent.jpg')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
