"""
Version Manager for SyncStream

Handles version checking and updates from GitHub repository.
"""

import requests
import json
import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
import threading


class VersionManager:
    """Manages application version and updates"""

    REPO_OWNER = "umfhero"
    REPO_NAME = "SyncStream"
    GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    CURRENT_VERSION = "3.0.0"

    # Cache settings
    CACHE_FILE = ".syncstream/update_cache.json"
    CACHE_DURATION_HOURS = 24  # Check for updates at most once per day

    # Files to preserve during update (user data)
    PRESERVE_FILES = [
        "config/profiles.json",
        "config/settings.json",
        ".syncstream/shared_files.json"
    ]

    # Directories to preserve
    PRESERVE_DIRS = [
        "config",
        ".syncstream"
    ]

    def __init__(self):
        self.update_available = False
        self.latest_version = None
        self.latest_release_info = None
        self.checking = False
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists"""
        cache_dir = Path(self.CACHE_FILE).parent
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Optional[Dict]:
        """Load cached update check data"""
        try:
            cache_path = Path(self.CACHE_FILE)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)

                # Check if cache is still valid
                last_check = datetime.fromisoformat(
                    cache_data.get('timestamp', ''))
                if datetime.now() - last_check < timedelta(hours=self.CACHE_DURATION_HOURS):
                    return cache_data
        except Exception as e:
            print(f"⚠️  Failed to load update cache: {e}")
        return None

    def _save_cache(self, data: Dict):
        """Save update check data to cache"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save update cache: {e}")

    def get_current_version(self) -> str:
        """Get the current application version"""
        return self.CURRENT_VERSION

    def get_repo_url(self) -> str:
        """Get the GitHub repository URL"""
        return f"https://github.com/{self.REPO_OWNER}/{self.REPO_NAME}"

    def check_for_updates(self, callback=None, force=False) -> Tuple[bool, Optional[str]]:
        """
        Check if updates are available

        Args:
            callback: Optional callback function(success, version, error_msg)
            force: Force check even if cache is valid

        Returns:
            Tuple of (update_available, latest_version)
        """
        # Try to use cached data if not forcing
        if not force:
            cached = self._load_cache()
            if cached:
                cache_data = cached.get('data', {})
                self.latest_version = cache_data.get('latest_version')
                self.latest_release_info = cache_data.get('release_info')
                self.update_available = cache_data.get(
                    'update_available', False)

                if callback:
                    callback(True, self.latest_version, None)

                return self.update_available, self.latest_version

        def _check():
            try:
                self.checking = True

                # Try to get latest release from GitHub
                response = requests.get(
                    f"{self.GITHUB_API_URL}/releases/latest",
                    timeout=10
                )

                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get(
                        "tag_name", "").lstrip("vV")

                    self.latest_release_info = release_data
                    self.latest_version = latest_version
                elif response.status_code == 404:
                    # No releases yet, check commits instead
                    commits_response = requests.get(
                        f"{self.GITHUB_API_URL}/commits/main",
                        timeout=10
                    )

                    if commits_response.status_code == 200:
                        commit_data = commits_response.json()
                        # Use current version since we can't determine from commits
                        latest_version = self.CURRENT_VERSION

                        # Create a pseudo-release info for display
                        self.latest_release_info = {
                            "tag_name": f"v{self.CURRENT_VERSION}",
                            "name": f"Version {self.CURRENT_VERSION}",
                            "body": "Latest development version from main branch.\n\n" +
                            f"Latest commit: {commit_data.get('sha', '')[:7]}\n" +
                            f"Date: {commit_data.get('commit', {}).get('author', {}).get('date', 'Unknown')}\n" +
                            f"Message: {commit_data.get('commit', {}).get('message', 'No message')}"
                        }
                        self.latest_version = latest_version
                        self.update_available = False  # Can't determine without releases

                        # Cache the result
                        self._save_cache({
                            'latest_version': latest_version,
                            'release_info': self.latest_release_info,
                            'update_available': False
                        })

                        if callback:
                            callback(True, latest_version, None)
                        return False, latest_version
                    else:
                        error_msg = f"Repository not accessible: HTTP {commits_response.status_code}"
                        if callback:
                            callback(False, None, error_msg)
                        return False, None
                else:
                    error_msg = f"Failed to check for updates: HTTP {response.status_code}"
                    if callback:
                        callback(False, None, error_msg)
                    return False, None

                if response.status_code == 200:

                    # Compare versions
                    self.update_available = self._compare_versions(
                        latest_version, self.CURRENT_VERSION
                    )

                    # Cache the result
                    self._save_cache({
                        'latest_version': latest_version,
                        'release_info': self.latest_release_info,
                        'update_available': self.update_available
                    })

                    if callback:
                        callback(True, latest_version, None)

                    return self.update_available, latest_version
                else:
                    error_msg = f"Failed to check for updates: HTTP {response.status_code}"
                    if callback:
                        callback(False, None, error_msg)
                    return False, None

            except requests.RequestException as e:
                error_msg = f"Network error: {str(e)}"
                if callback:
                    callback(False, None, error_msg)
                return False, None
            except Exception as e:
                error_msg = f"Error checking updates: {str(e)}"
                if callback:
                    callback(False, None, error_msg)
                return False, None
            finally:
                self.checking = False

        # Run in thread if callback provided
        if callback:
            thread = threading.Thread(target=_check, daemon=True)
            thread.start()
            return self.update_available, self.latest_version
        else:
            return _check()

    def _compare_versions(self, version1: str, version2: str) -> bool:
        """
        Compare two version strings

        Returns:
            True if version1 > version2
        """
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            return v1_parts > v2_parts
        except:
            return False

    def download_and_install_update(self, progress_callback=None, completion_callback=None):
        """
        Download and install the latest update

        Args:
            progress_callback: Optional callback(stage, message, progress_percent)
            completion_callback: Optional callback(success, message)
        """
        def _update():
            try:
                if not self.latest_release_info:
                    if completion_callback:
                        completion_callback(
                            False, "No update information available")
                    return

                # Stage 1: Download
                if progress_callback:
                    progress_callback("download", "Downloading update...", 10)

                download_url = self._get_download_url()
                if not download_url:
                    if completion_callback:
                        completion_callback(False, "No download URL found")
                    return

                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "update.zip")

                # Download the release
                response = requests.get(download_url, stream=True, timeout=30)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and progress_callback:
                                percent = 10 + \
                                    int((downloaded / total_size) * 40)
                                progress_callback(
                                    "download", f"Downloading... {downloaded/1024/1024:.1f}MB", percent)

                # Stage 2: Extract
                if progress_callback:
                    progress_callback("extract", "Extracting files...", 50)

                extract_dir = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Stage 3: Backup user data
                if progress_callback:
                    progress_callback("backup", "Backing up user data...", 60)

                backup_dir = os.path.join(temp_dir, "backup")
                os.makedirs(backup_dir, exist_ok=True)
                self._backup_user_data(backup_dir)

                # Stage 4: Install update
                if progress_callback:
                    progress_callback("install", "Installing update...", 70)

                self._install_update(
                    extract_dir, backup_dir, progress_callback)

                # Stage 5: Complete
                if progress_callback:
                    progress_callback("complete", "Update complete!", 100)

                if completion_callback:
                    completion_callback(
                        True, "Update installed successfully! Please restart SyncStream.")

                # Cleanup
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

            except Exception as e:
                error_msg = f"Update failed: {str(e)}"
                if completion_callback:
                    completion_callback(False, error_msg)

        # Run in thread
        thread = threading.Thread(target=_update, daemon=True)
        thread.start()

    def _get_download_url(self) -> Optional[str]:
        """Get the download URL for the latest release"""
        if not self.latest_release_info:
            return None

        assets = self.latest_release_info.get("assets", [])

        # Look for the main release zip
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".zip") and "syncstream" in name:
                return asset.get("browser_download_url")

        # Fallback: use zipball_url (source code)
        return self.latest_release_info.get("zipball_url")

    def _backup_user_data(self, backup_dir: str):
        """Backup user data files"""
        app_root = self._get_app_root()

        for rel_path in self.PRESERVE_FILES:
            src_path = os.path.join(app_root, rel_path)
            if os.path.exists(src_path):
                dst_path = os.path.join(backup_dir, rel_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

        # Backup home directory data
        home_data_dir = os.path.join(os.path.expanduser("~"), ".syncstream")
        if os.path.exists(home_data_dir):
            dst_path = os.path.join(backup_dir, ".syncstream")
            shutil.copytree(home_data_dir, dst_path, dirs_exist_ok=True)

    def _install_update(self, extract_dir: str, backup_dir: str, progress_callback=None):
        """Install the update by replacing files"""
        app_root = self._get_app_root()

        # Find the actual content directory (handle GitHub's folder structure)
        content_dir = extract_dir
        subdirs = [d for d in os.listdir(extract_dir) if os.path.isdir(
            os.path.join(extract_dir, d))]
        if len(subdirs) == 1:
            # GitHub creates a folder like "SyncStream-main" or "umfhero-SyncStream-abc123"
            potential_dir = os.path.join(extract_dir, subdirs[0])
            if os.path.exists(os.path.join(potential_dir, "src")):
                content_dir = potential_dir

        # Copy new files (excluding user data)
        exclude_patterns = ['.git', '__pycache__',
                            '*.pyc', '.syncstream', 'backup']

        for root, dirs, files in os.walk(content_dir):
            # Skip excluded directories
            dirs[:] = [
                d for d in dirs if d not in exclude_patterns and not d.startswith('.')]

            rel_root = os.path.relpath(root, content_dir)
            if rel_root == '.':
                rel_root = ''

            # Create directory structure
            if rel_root:
                dst_dir = os.path.join(app_root, rel_root)
                os.makedirs(dst_dir, exist_ok=True)

            # Copy files
            for file in files:
                if any(pattern in file for pattern in ['*.pyc', '.DS_Store']):
                    continue

                src_file = os.path.join(root, file)
                rel_file = os.path.join(rel_root, file) if rel_root else file
                dst_file = os.path.join(app_root, rel_file)

                # Don't overwrite preserved files
                if rel_file in self.PRESERVE_FILES:
                    continue

                # Copy file
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)

        # Restore user data
        for rel_path in self.PRESERVE_FILES:
            backup_path = os.path.join(backup_dir, rel_path)
            if os.path.exists(backup_path):
                dst_path = os.path.join(app_root, rel_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(backup_path, dst_path)

        # Restore home directory data
        home_backup = os.path.join(backup_dir, ".syncstream")
        if os.path.exists(home_backup):
            home_data_dir = os.path.join(
                os.path.expanduser("~"), ".syncstream")
            shutil.copytree(home_backup, home_data_dir, dirs_exist_ok=True)

    def _get_app_root(self) -> str:
        """Get the application root directory"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = Path(sys._MEIPASS)
        except Exception:
            # Running in development - go up from src/utils to root
            base_path = Path(__file__).parent.parent.parent

        return str(base_path)
