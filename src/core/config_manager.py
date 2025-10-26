"""
SyncStream - Configuration Manager

Handles loading and saving of:
- User profiles (from profiles.json)
- Application settings (theme, download location, compression)
- Last connection state
- Transfer history
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Profile:
    """Represents a user profile with connection details"""
    name: str
    ip: str
    port: int
    description: str = ""


@dataclass
class AppSettings:
    """Application-wide settings"""
    theme: str = "dark"  # "dark" or "light"
    download_location: Optional[str] = None  # None means use default AppData
    compression_enabled: bool = False
    auto_reconnect: bool = True
    reconnect_timeout: int = 180  # seconds (3 minutes)
    notifications_enabled: bool = True
    window_width: int = 1200
    window_height: int = 800
    window_x: Optional[int] = None
    window_y: Optional[int] = None


class ConfigManager:
    """Manages all configuration and settings for SyncStream"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Path to config directory (defaults to ./config)
        """
        if config_dir is None:
            # Get the project root (parent of src directory)
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self.profiles_file = self.config_dir / "profiles.json"
        self.settings_file = self.config_dir / "settings.json"

        # Application data directory (in %APPDATA%)
        self.app_data_dir = Path(os.getenv('APPDATA')) / "SyncStream"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)

        # Transfer history file
        self.history_file = self.app_data_dir / "transfer_history.json"

        # Initialize data structures
        self.profiles: List[Profile] = []
        self.settings = AppSettings()
        self.last_profile: Optional[str] = None
        self.last_peer: Optional[str] = None

        # Load configuration
        self._load_profiles()
        self._load_settings()

    def _load_profiles(self) -> None:
        """Load profiles from profiles.json"""
        if not self.profiles_file.exists():
            print(f"⚠️  Warning: {self.profiles_file} not found!")
            print(
                "📝 Please copy profiles.json.template to profiles.json and configure it.")
            return

        try:
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)

            # Load profiles
            self.profiles = [
                Profile(**profile_data)
                for profile_data in data.get("profiles", [])
            ]

            # Load last connection state
            self.last_profile = data.get("last_profile")
            self.last_peer = data.get("last_peer")

            print(f"✅ Loaded {len(self.profiles)} profiles")

        except Exception as e:
            print(f"❌ Error loading profiles: {e}")

    def _load_settings(self) -> None:
        """Load application settings from settings.json"""
        if not self.settings_file.exists():
            # Create default settings file
            self._save_settings()
            return

        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)

            # Update settings with loaded data
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)

            print("✅ Loaded application settings")

        except Exception as e:
            print(f"❌ Error loading settings: {e}")

    def _save_settings(self) -> None:
        """Save current settings to settings.json"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(asdict(self.settings), f, indent=2)
        except Exception as e:
            print(f"❌ Error saving settings: {e}")

    def save_last_connection(self, profile: Optional[str], peer: Optional[str]) -> None:
        """
        Save the last used profile and peer connection

        Args:
            profile: Name of the user's profile
            peer: Name of the connected peer
        """
        self.last_profile = profile
        self.last_peer = peer

        try:
            # Load current profiles data
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"profiles": []}

            # Update last connection
            data["last_profile"] = profile
            data["last_peer"] = peer

            # Save back
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"❌ Error saving last connection: {e}")

    def get_profile_by_name(self, name: str) -> Optional[Profile]:
        """Get a profile by name"""
        for profile in self.profiles:
            if profile.name == name:
                return profile
        return None

    def get_profile_names(self) -> List[str]:
        """Get list of all profile names"""
        return [p.name for p in self.profiles]

    def get_download_location(self) -> Path:
        """Get the download location (custom or default)"""
        if self.settings.download_location:
            return Path(self.settings.download_location)
        return self.app_data_dir / "Downloads"

    def set_download_location(self, path: str) -> None:
        """Set custom download location"""
        self.settings.download_location = path
        self._save_settings()

    def set_theme(self, theme: str) -> None:
        """Set application theme"""
        if theme in ["light", "dark"]:
            self.settings.theme = theme
            self._save_settings()

    def toggle_theme(self) -> str:
        """Toggle between light and dark theme"""
        new_theme = "light" if self.settings.theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme

    def set_compression(self, enabled: bool) -> None:
        """Enable or disable compression"""
        self.settings.compression_enabled = enabled
        self._save_settings()

    def save_window_geometry(self, width: int, height: int, x: int, y: int) -> None:
        """Save window position and size"""
        self.settings.window_width = width
        self.settings.window_height = height
        self.settings.window_x = x
        self.settings.window_y = y
        self._save_settings()


if __name__ == "__main__":
    # Test the config manager
    print("🧪 Testing ConfigManager...")
    config = ConfigManager()

    print(f"\n📋 Profiles: {config.get_profile_names()}")
    print(f"🎨 Theme: {config.settings.theme}")
    print(f"📁 Download Location: {config.get_download_location()}")
    print(f"🔄 Last Profile: {config.last_profile}")
    print(f"🔗 Last Peer: {config.last_peer}")
