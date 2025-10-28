"""
Unit tests for ConfigManager
"""

from core.config_manager import ConfigManager
import unittest
import json
import tempfile
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test configs
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create test profiles
        self.test_profiles = {
            "Alice": {
                "ip": "100.64.0.1",
                "port": 5000,
                "last_connected": "2025-01-01T12:00:00"
            },
            "Bob": {
                "ip": "100.64.0.2",
                "port": 5001,
                "last_connected": None
            }
        }

        # Save test profiles
        profiles_file = self.config_dir / "profiles.json"
        with open(profiles_file, 'w') as f:
            json.dump(self.test_profiles, f)

        # Create test settings
        self.test_settings = {
            "theme": "dark",
            "download_dir": str(Path.home() / "Downloads"),
            "auto_accept": False,
            "compression": True
        }

        # Save test settings
        settings_file = self.config_dir / "settings.json"
        with open(settings_file, 'w') as f:
            json.dump(self.test_settings, f)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_profiles(self):
        """Test loading profiles"""
        config = ConfigManager(self.config_dir)
        profiles = config.get_profiles()

        self.assertEqual(len(profiles), 2)
        self.assertIn("Alice", profiles)
        self.assertIn("Bob", profiles)
        self.assertEqual(profiles["Alice"]["ip"], "100.64.0.1")
        self.assertEqual(profiles["Bob"]["port"], 5001)

    def test_load_settings(self):
        """Test loading settings"""
        config = ConfigManager(self.config_dir)
        settings = config.get_settings()

        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["compression"], True)
        self.assertEqual(settings["auto_accept"], False)

    def test_add_profile(self):
        """Test adding a new profile"""
        config = ConfigManager(self.config_dir)

        new_profile = {
            "ip": "100.64.0.3",
            "port": 5002
        }

        config.add_profile("Charlie", new_profile)
        profiles = config.get_profiles()

        self.assertIn("Charlie", profiles)
        self.assertEqual(profiles["Charlie"]["ip"], "100.64.0.3")

    def test_update_profile(self):
        """Test updating an existing profile"""
        config = ConfigManager(self.config_dir)

        config.update_profile("Alice", {"ip": "100.64.0.10"})
        profiles = config.get_profiles()

        self.assertEqual(profiles["Alice"]["ip"], "100.64.0.10")
        # Should preserve other fields
        self.assertEqual(profiles["Alice"]["port"], 5000)

    def test_remove_profile(self):
        """Test removing a profile"""
        config = ConfigManager(self.config_dir)

        config.remove_profile("Bob")
        profiles = config.get_profiles()

        self.assertNotIn("Bob", profiles)
        self.assertEqual(len(profiles), 1)

    def test_update_settings(self):
        """Test updating settings"""
        config = ConfigManager(self.config_dir)

        config.update_settings({"theme": "light", "auto_accept": True})
        settings = config.get_settings()

        self.assertEqual(settings["theme"], "light")
        self.assertEqual(settings["auto_accept"], True)
        # Should preserve other settings
        self.assertEqual(settings["compression"], True)

    def test_get_last_connection(self):
        """Test getting last connection info"""
        config = ConfigManager(self.config_dir)

        last_conn = config.get_last_connection()
        # Since Alice has the most recent timestamp, she should be returned
        self.assertEqual(last_conn["profile"], "Alice")
        self.assertEqual(last_conn["ip"], "100.64.0.1")

    def test_save_last_connection(self):
        """Test saving last connection"""
        config = ConfigManager(self.config_dir)

        config.save_last_connection("Bob")
        profiles = config.get_profiles()

        # Bob should now have a last_connected timestamp
        self.assertIsNotNone(profiles["Bob"].get("last_connected"))

    def test_missing_profiles_file(self):
        """Test handling missing profiles file"""
        empty_dir = Path(self.test_dir) / "empty"
        empty_dir.mkdir(exist_ok=True)

        config = ConfigManager(empty_dir)
        profiles = config.get_profiles()

        # Should return empty dict or create default
        self.assertIsInstance(profiles, dict)

    def test_invalid_json(self):
        """Test handling invalid JSON in config files"""
        invalid_dir = Path(self.test_dir) / "invalid"
        invalid_dir.mkdir(exist_ok=True)

        # Write invalid JSON
        profiles_file = invalid_dir / "profiles.json"
        with open(profiles_file, 'w') as f:
            f.write("{ invalid json }")

        config = ConfigManager(invalid_dir)
        profiles = config.get_profiles()

        # Should handle gracefully and return empty dict
        self.assertIsInstance(profiles, dict)


if __name__ == '__main__':
    unittest.main()
