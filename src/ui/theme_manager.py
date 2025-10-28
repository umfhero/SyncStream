"""
SyncStream - Theme Manager

Manages light and dark themes with dynamic switching.
Themes follow the design brief for clean, modern aesthetics.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ThemeColors:
    """Color scheme for a theme"""
    # Background colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_disabled: str

    # Accent colors
    accent_primary: str
    accent_hover: str
    accent_pressed: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Border and shadow
    border: str
    shadow: str

    # Special
    hover_overlay: str


class ThemeManager:
    """Manages application themes"""

    # Light Theme - Clean white/off-white with vibrant blue accent
    LIGHT_THEME = ThemeColors(
        # Backgrounds
        bg_primary="#FFFFFF",      # Pure white main background
        bg_secondary="#FFFFFF",     # Pure white for cards/panels
        bg_tertiary="#F5F5F5",      # Subtle gray for sections

        # Text
        text_primary="#2C3E50",     # Dark gray for primary text
        text_secondary="#546E7A",   # Medium gray for secondary text
        text_disabled="#B0BEC5",    # Light gray for disabled

        # Accent
        accent_primary="#34DB5E",   # Vibrant blue
        accent_hover="#29B948",     # Darker blue on hover
        accent_pressed="#1FA84D",   # Even darker when pressed

        # Status
        success="#46D883",          # Green
        warning="#F8A828",          # Orange
        error="#FF3721",            # Red
        info="#3498DB",             # Blue

        # Border and shadow
        border="#E0E0E0",           # Light border
        shadow="rgba(0, 0, 0, 0.1)",  # Subtle shadow

        # Special
        hover_overlay="rgba(0, 0, 0, 0.05)"  # Light hover effect
    )

    # Dark Theme - Deep charcoal with luminous blue accent
    DARK_THEME = ThemeColors(
        # Backgrounds
        bg_primary="#121212",       # Deep charcoal main background
        bg_secondary="#2B2B2B",     # Slightly lighter for cards/top bar
        bg_tertiary="#252525",      # Between primary and secondary

        # Text
        text_primary="#ECEFF1",     # Light gray for primary text
        text_secondary="#B0BEC5",   # Medium gray for secondary text
        text_disabled="#546E7A",    # Darker gray for disabled

        # Accent
        accent_primary="#3498DB",   # Vibrant blue (same as light)
        accent_hover="#5DADE2",     # Lighter blue on hover
        accent_pressed="#2E86C1",   # Slightly darker when pressed

        # Status
        success="#2ECC71",          # Bright green
        warning="#F39C12",          # Orange
        error="#E74C3C",            # Red
        info="#3498DB",             # Blue

        # Border and shadow
        border="#3A3A3A",           # Subtle border
        shadow="rgba(0, 0, 0, 0.3)",  # Stronger shadow

        # Special
        # Light overlay for dark theme
        hover_overlay="rgba(255, 255, 255, 0.05)"
    )

    def __init__(self, current_theme: str = "dark"):
        """
        Initialize theme manager

        Args:
            current_theme: "light" or "dark"
        """
        self.current_theme_name = current_theme
        self._callbacks = []

    @property
    def current_theme(self) -> ThemeColors:
        """Get the current theme colors"""
        return self.LIGHT_THEME if self.current_theme_name == "light" else self.DARK_THEME

    def toggle_theme(self) -> str:
        """
        Toggle between light and dark theme

        Returns:
            New theme name
        """
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self._notify_callbacks()
        return self.current_theme_name

    def set_theme(self, theme_name: str) -> None:
        """
        Set a specific theme

        Args:
            theme_name: "light" or "dark"
        """
        if theme_name in ["light", "dark"]:
            self.current_theme_name = theme_name
            self._notify_callbacks()

    def register_callback(self, callback):
        """Register a callback to be called when theme changes"""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notify all registered callbacks of theme change"""
        for callback in self._callbacks:
            try:
                callback(self.current_theme_name)
            except Exception as e:
                print(f"Error in theme callback: {e}")

    def get_ctk_theme_mode(self) -> str:
        """Get theme mode for CustomTkinter"""
        return "light" if self.current_theme_name == "light" else "dark"

    def get_button_colors(self) -> Dict:
        """Get button color configuration for CustomTkinter"""
        theme = self.current_theme
        return {
            "fg_color": theme.accent_primary,
            "hover_color": theme.accent_hover,
            "text_color": "#FFFFFF"
        }

    def get_frame_colors(self) -> Dict:
        """Get frame color configuration"""
        theme = self.current_theme
        return {
            "fg_color": theme.bg_secondary,
            "border_color": theme.border
        }

    def get_entry_colors(self) -> Dict:
        """Get entry/input color configuration"""
        theme = self.current_theme
        return {
            "fg_color": theme.bg_secondary,
            "border_color": theme.border,
            "text_color": theme.text_primary
        }


if __name__ == "__main__":
    # Test the theme manager
    print("🎨 Testing ThemeManager...")

    manager = ThemeManager("dark")
    print(f"\n📱 Current theme: {manager.current_theme_name}")
    print(f"🎨 Primary background: {manager.current_theme.bg_primary}")
    print(f"✨ Accent color: {manager.current_theme.accent_primary}")

    print("\n🔄 Toggling theme...")
    new_theme = manager.toggle_theme()
    print(f"📱 New theme: {new_theme}")
    print(f"🎨 Primary background: {manager.current_theme.bg_primary}")
    print(f"✨ Accent color: {manager.current_theme.accent_primary}")
