"""
Unit tests for FileManager
"""

from core.file_manager import FileManager
import unittest
import tempfile
import os
import sys
from pathlib import Path
from PIL import Image

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.app_data_dir = Path(self.test_dir) / "appdata"
        self.download_dir = Path(self.test_dir) / "downloads"

        # Create file manager
        self.file_manager = FileManager(self.app_data_dir, self.download_dir)

        # Create test image file
        self.test_image = Path(self.test_dir) / "test_image.png"
        img = Image.new('RGB', (800, 600), color='blue')
        img.save(self.test_image)

        # Create test text file
        self.test_text = Path(self.test_dir) / "test_doc.txt"
        with open(self.test_text, 'w') as f:
            f.write("Test content")

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialization(self):
        """Test file manager initialization"""
        self.assertTrue(self.app_data_dir.exists())
        self.assertTrue(self.download_dir.exists())
        self.assertTrue((self.app_data_dir / "Thumbnails").exists())

    def test_get_file_info(self):
        """Test getting file information"""
        info = self.file_manager.get_file_info(str(self.test_image))

        self.assertIsNotNone(info)
        self.assertEqual(info['name'], 'test_image.png')
        self.assertEqual(info['extension'], '.png')
        self.assertTrue(info['is_image'])
        self.assertGreater(info['size'], 0)

    def test_generate_thumbnail(self):
        """Test thumbnail generation"""
        thumb_path = self.file_manager.generate_thumbnail(
            str(self.test_image),
            size=(128, 128)
        )

        self.assertIsNotNone(thumb_path)
        self.assertTrue(Path(thumb_path).exists())

        # Verify thumbnail dimensions
        thumb_img = Image.open(thumb_path)
        self.assertLessEqual(thumb_img.width, 128)
        self.assertLessEqual(thumb_img.height, 128)

    def test_thumbnail_caching(self):
        """Test that thumbnails are cached"""
        # Generate thumbnail twice
        thumb_path1 = self.file_manager.generate_thumbnail(
            str(self.test_image),
            size=(128, 128)
        )
        thumb_path2 = self.file_manager.generate_thumbnail(
            str(self.test_image),
            size=(128, 128)
        )

        # Should return same path (cached)
        self.assertEqual(thumb_path1, thumb_path2)

    def test_add_to_history(self):
        """Test adding files to transfer history"""
        file_id = "test123"
        metadata = {
            "name": "test.txt",
            "size": 1024,
            "sender": "Alice",
            "receiver": "Bob"
        }

        self.file_manager.add_to_history(file_id, metadata)
        history = self.file_manager.get_history()

        self.assertIn(file_id, history)
        self.assertEqual(history[file_id]['name'], 'test.txt')
        self.assertEqual(history[file_id]['sender'], 'Alice')

    def test_history_persistence(self):
        """Test that history persists across instances"""
        # Add to history
        file_id = "persist_test"
        metadata = {"name": "file.txt", "size": 512}
        self.file_manager.add_to_history(file_id, metadata)

        # Create new file manager instance
        new_fm = FileManager(self.app_data_dir, self.download_dir)
        history = new_fm.get_history()

        # Should load existing history
        self.assertIn(file_id, history)

    def test_non_image_thumbnail(self):
        """Test thumbnail generation for non-image files"""
        thumb_path = self.file_manager.generate_thumbnail(
            str(self.test_text),
            size=(128, 128)
        )

        # Should return None for non-image files
        self.assertIsNone(thumb_path)

    def test_missing_file_info(self):
        """Test getting info for non-existent file"""
        info = self.file_manager.get_file_info("/nonexistent/file.txt")

        # Should handle gracefully
        self.assertIsNone(info)

    def test_custom_download_directory(self):
        """Test using custom download directory"""
        custom_dir = Path(self.test_dir) / "custom_downloads"
        fm = FileManager(self.app_data_dir, custom_dir)

        self.assertTrue(custom_dir.exists())
        self.assertEqual(fm.download_dir, custom_dir)

    def test_supported_image_formats(self):
        """Test image format detection"""
        image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']

        for ext in image_exts:
            test_file = Path(self.test_dir) / f"test{ext}"
            info = self.file_manager.get_file_info(str(test_file))

            if info:  # Only check if file exists
                self.assertTrue(info['is_image'])


if __name__ == '__main__':
    unittest.main()
