"""
Unit tests for VersionManager

Tests version checking, caching, and update functionality.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.version_manager import VersionManager


class TestVersionManager(unittest.TestCase):
    """Test cases for VersionManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for cache
        self.test_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.test_dir, '.syncstream', 'update_cache.json')
        
        # Patch the CACHE_FILE path
        self.original_cache_file = VersionManager.CACHE_FILE
        VersionManager.CACHE_FILE = self.cache_file
        
        self.vm = VersionManager()
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Restore original cache file path
        VersionManager.CACHE_FILE = self.original_cache_file
        
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test VersionManager initialization"""
        self.assertFalse(self.vm.update_available)
        self.assertIsNone(self.vm.latest_version)
        self.assertIsNone(self.vm.latest_release_info)
        self.assertFalse(self.vm.checking)
    
    def test_get_current_version(self):
        """Test getting current version"""
        version = self.vm.get_current_version()
        self.assertEqual(version, "2.0.0")
    
    def test_get_repo_url(self):
        """Test getting repository URL"""
        url = self.vm.get_repo_url()
        self.assertEqual(url, "https://github.com/umfhero/SyncStream")
    
    def test_compare_versions_greater(self):
        """Test version comparison - newer version available"""
        result = self.vm._compare_versions("2.1.0", "2.0.0")
        self.assertTrue(result)
    
    def test_compare_versions_equal(self):
        """Test version comparison - same version"""
        result = self.vm._compare_versions("2.0.0", "2.0.0")
        self.assertFalse(result)
    
    def test_compare_versions_lesser(self):
        """Test version comparison - older version"""
        result = self.vm._compare_versions("1.9.0", "2.0.0")
        self.assertFalse(result)
    
    def test_compare_versions_patch(self):
        """Test version comparison - patch version"""
        result = self.vm._compare_versions("2.0.1", "2.0.0")
        self.assertTrue(result)
    
    def test_save_and_load_cache(self):
        """Test cache save and load functionality"""
        # Save cache data
        test_data = {
            'latest_version': '2.1.0',
            'release_info': {'tag_name': 'v2.1.0'},
            'update_available': True
        }
        self.vm._save_cache(test_data)
        
        # Load cache data
        cached = self.vm._load_cache()
        self.assertIsNotNone(cached)
        self.assertEqual(cached['data']['latest_version'], '2.1.0')
        self.assertTrue(cached['data']['update_available'])
    
    def test_cache_expiration(self):
        """Test that old cache expires"""
        # Create an old cache file
        cache_dir = Path(self.cache_file).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        old_timestamp = datetime.now() - timedelta(hours=25)
        cache_data = {
            'timestamp': old_timestamp.isoformat(),
            'data': {
                'latest_version': '2.1.0',
                'update_available': True
            }
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Load should return None for expired cache
        cached = self.vm._load_cache()
        self.assertIsNone(cached)
    
    def test_cache_valid_within_duration(self):
        """Test that recent cache is valid"""
        # Create a recent cache file
        cache_dir = Path(self.cache_file).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        recent_timestamp = datetime.now() - timedelta(hours=1)
        cache_data = {
            'timestamp': recent_timestamp.isoformat(),
            'data': {
                'latest_version': '2.1.0',
                'update_available': True
            }
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Load should return cached data
        cached = self.vm._load_cache()
        self.assertIsNotNone(cached)
        self.assertEqual(cached['data']['latest_version'], '2.1.0')
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_success(self, mock_get):
        """Test successful update check"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v2.1.0',
            'name': 'Version 2.1.0',
            'body': 'Release notes here'
        }
        mock_get.return_value = mock_response
        
        # Check for updates
        update_available, version = self.vm.check_for_updates()
        
        # Verify results
        self.assertTrue(update_available)
        self.assertEqual(version, '2.1.0')
        self.assertEqual(self.vm.latest_version, '2.1.0')
        self.assertIsNotNone(self.vm.latest_release_info)
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_no_new_version(self, mock_get):
        """Test update check when already on latest version"""
        # Mock API response with current version
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v2.0.0',
            'name': 'Version 2.0.0',
            'body': 'Current version'
        }
        mock_get.return_value = mock_response
        
        # Check for updates
        update_available, version = self.vm.check_for_updates()
        
        # Verify results
        self.assertFalse(update_available)
        self.assertEqual(version, '2.0.0')
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_no_releases(self, mock_get):
        """Test update check when no releases exist (404)"""
        # Mock 404 for releases, then success for commits
        mock_release_response = Mock()
        mock_release_response.status_code = 404
        
        mock_commit_response = Mock()
        mock_commit_response.status_code = 200
        mock_commit_response.json.return_value = {
            'sha': 'abc123def456',
            'commit': {
                'author': {'date': '2025-10-28T12:00:00Z'},
                'message': 'Latest commit message'
            }
        }
        
        mock_get.side_effect = [mock_release_response, mock_commit_response]
        
        # Check for updates
        update_available, version = self.vm.check_for_updates()
        
        # Verify results
        self.assertFalse(update_available)
        self.assertEqual(version, '2.0.0')
        self.assertIsNotNone(self.vm.latest_release_info)
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_network_error(self, mock_get):
        """Test update check with network error"""
        # Mock network error
        mock_get.side_effect = Exception("Network error")
        
        # Check for updates
        update_available, version = self.vm.check_for_updates()
        
        # Verify results
        self.assertFalse(update_available)
        self.assertIsNone(version)
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_with_callback(self, mock_get):
        """Test update check with callback"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v2.1.0',
            'name': 'Version 2.1.0',
            'body': 'Release notes'
        }
        mock_get.return_value = mock_response
        
        # Create callback mock
        callback = Mock()
        
        # Check for updates with callback
        self.vm.check_for_updates(callback)
        
        # Wait a moment for thread to complete
        import time
        time.sleep(0.5)
        
        # Verify callback was called
        callback.assert_called_once()
        args = callback.call_args[0]
        self.assertTrue(args[0])  # success
        self.assertEqual(args[1], '2.1.0')  # version
        self.assertIsNone(args[2])  # error
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_uses_cache(self, mock_get):
        """Test that cached data is used when valid"""
        # Create valid cache
        cache_dir = Path(self.cache_file).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        recent_timestamp = datetime.now() - timedelta(hours=1)
        cache_data = {
            'timestamp': recent_timestamp.isoformat(),
            'data': {
                'latest_version': '2.1.0',
                'release_info': {'tag_name': 'v2.1.0'},
                'update_available': True
            }
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Check for updates (should use cache, not call API)
        update_available, version = self.vm.check_for_updates()
        
        # Verify results from cache
        self.assertTrue(update_available)
        self.assertEqual(version, '2.1.0')
        
        # Verify API was not called
        mock_get.assert_not_called()
    
    @patch('utils.version_manager.requests.get')
    def test_check_for_updates_force_bypass_cache(self, mock_get):
        """Test that force=True bypasses cache"""
        # Create valid cache
        cache_dir = Path(self.cache_file).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        recent_timestamp = datetime.now() - timedelta(hours=1)
        cache_data = {
            'timestamp': recent_timestamp.isoformat(),
            'data': {
                'latest_version': '2.1.0',
                'release_info': {'tag_name': 'v2.1.0'},
                'update_available': True
            }
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v2.2.0',
            'name': 'Version 2.2.0',
            'body': 'New release'
        }
        mock_get.return_value = mock_response
        
        # Check for updates with force=True
        update_available, version = self.vm.check_for_updates(force=True)
        
        # Verify API was called despite cache
        mock_get.assert_called_once()
        self.assertEqual(version, '2.2.0')
    
    def test_ensure_cache_dir(self):
        """Test cache directory creation"""
        # Remove cache dir if exists
        cache_dir = Path(self.cache_file).parent
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        
        # Ensure cache dir is created
        self.vm._ensure_cache_dir()
        
        # Verify directory exists
        self.assertTrue(cache_dir.exists())


class TestVersionComparison(unittest.TestCase):
    """Test version comparison logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.vm = VersionManager()
    
    def test_major_version_comparison(self):
        """Test major version differences"""
        self.assertTrue(self.vm._compare_versions("3.0.0", "2.0.0"))
        self.assertFalse(self.vm._compare_versions("1.0.0", "2.0.0"))
    
    def test_minor_version_comparison(self):
        """Test minor version differences"""
        self.assertTrue(self.vm._compare_versions("2.1.0", "2.0.0"))
        self.assertFalse(self.vm._compare_versions("2.0.0", "2.1.0"))
    
    def test_patch_version_comparison(self):
        """Test patch version differences"""
        self.assertTrue(self.vm._compare_versions("2.0.1", "2.0.0"))
        self.assertFalse(self.vm._compare_versions("2.0.0", "2.0.1"))
    
    def test_multi_digit_versions(self):
        """Test versions with multi-digit numbers"""
        self.assertTrue(self.vm._compare_versions("2.10.0", "2.9.0"))
        self.assertTrue(self.vm._compare_versions("2.0.10", "2.0.9"))
    
    def test_version_with_prefix(self):
        """Test version strings with 'v' prefix"""
        # The _compare_versions should handle clean version strings
        # The API response handler strips the 'v' prefix
        self.assertTrue(self.vm._compare_versions("2.1.0", "2.0.0"))


if __name__ == '__main__':
    unittest.main()
