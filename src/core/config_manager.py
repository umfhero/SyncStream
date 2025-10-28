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
        self.my_profile: Optional[Profile] = None  # User's own profile
        self.profiles: List[Profile] = []  # Peer profiles to connect to
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

            # Load my profile (user's own device)
            my_profile_data = data.get("my_profile")
            if my_profile_data:
                self.my_profile = Profile(**my_profile_data)

            # Load peer profiles (other devices to connect to)
            self.profiles = [
                Profile(**profile_data)
                for profile_data in data.get("peer_profiles", [])
            ]

            # Backward compatibility: if old format with "profiles" array exists
            if not my_profile_data and "profiles" in data:
                old_profiles = data.get("profiles", [])
                if old_profiles:
                    # First profile becomes "my_profile"
                    self.my_profile = Profile(**old_profiles[0])
                    # Rest become peer profiles
                    self.profiles = [Profile(**p) for p in old_profiles[1:]]

            # Load last connection state
            self.last_profile = data.get("last_profile")
            self.last_peer = data.get("last_peer")

            peer_count = len(self.profiles)
            has_my_profile = "Yes" if self.my_profile else "No"
            print(
                f"✅ Loaded my profile: {has_my_profile}, {peer_count} peer profile(s)")

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
        """Get a peer profile by name"""
        for profile in self.profiles:
            if profile.name == name:
                return profile
        return None

    def get_profiles(self) -> List[Profile]:
        """Get list of peer profiles (for connecting to others)"""
        return self.profiles

    def get_my_profile(self) -> Optional[Profile]:
        """Get user's own profile"""
        return self.my_profile

    def get_profile_names(self) -> List[str]:
        """Get list of peer profile names"""
        return [p.name for p in self.profiles]

    def set_my_profile(self, name: str, ip: str, port: int = 12345, description: str = "") -> None:
        """
        Set the user's own profile (created during onboarding)

        Args:
            name: Profile name
            ip: Tailscale IP address
            port: Port number (default: 12345)
            description: Optional description
        """
        self.my_profile = Profile(
            name=name, ip=ip, port=port, description=description)

    def add_profile(self, name: str, ip: str, port: int = 12345, description: str = "") -> None:
        """
        Add a new peer profile (other devices to connect to)

        Args:
            name: Profile name
            ip: Tailscale IP address
            port: Port number (default: 12345)
            description: Optional description
        """
        # Check if profile with same name already exists
        if any(p.name == name for p in self.profiles):
            raise ValueError(f"Profile '{name}' already exists")

        new_profile = Profile(name=name, ip=ip, port=port,
                              description=description)
        self.profiles.append(new_profile)

    def save_profiles(self) -> None:
        """Save all profiles to profiles.json"""
        try:
            # Save in new format with my_profile and peer_profiles
            data = {
                "my_profile": asdict(self.my_profile) if self.my_profile else None,
                "peer_profiles": [asdict(p) for p in self.profiles],
                "last_profile": self.last_profile,
                "last_peer": self.last_peer
            }

            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)

            peer_count = len(self.profiles)
            print(f"✅ Saved my profile and {peer_count} peer profile(s)")
        except Exception as e:
            print(f"❌ Error saving profiles: {e}")
            raise

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
