"""
Unit tests for ThemeManager

Tests theme loading, switching, and color management.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.theme_manager import ThemeManager, ThemeColors


class TestThemeColors(unittest.TestCase):
    """Test cases for ThemeColors class"""
    
    def test_theme_initialization(self):
        """Test ThemeColors dataclass initialization"""
        theme = ThemeColors(
            bg_primary="#FFFFFF",
            bg_secondary="#F5F5F5",
            bg_tertiary="#EEEEEE",
            text_primary="#000000",
            text_secondary="#666666",
            text_disabled="#CCCCCC",
            accent_primary="#4CAF50",
            accent_hover="#45A049",
            accent_pressed="#3D8B40",
            success="#4CAF50",
            warning="#FF9800",
            error="#F44336",
            info="#2196F3",
            border="#E0E0E0",
            shadow="#00000020",
            hover_overlay="#00000010"
        )
        
        self.assertEqual(theme.bg_primary, "#FFFFFF")
        self.assertEqual(theme.accent_primary, "#4CAF50")
    
    def test_theme_attributes(self):
        """Test that all theme attributes are accessible"""
        theme = ThemeColors(
            bg_primary="#FFFFFF",
            bg_secondary="#F5F5F5",
            bg_tertiary="#EEEEEE",
            text_primary="#000000",
            text_secondary="#666666",
            text_disabled="#CCCCCC",
            accent_primary="#4CAF50",
            accent_hover="#45A049",
            accent_pressed="#3D8B40",
            success="#4CAF50",
            warning="#FF9800",
            error="#F44336",
            info="#2196F3",
            border="#E0E0E0",
            shadow="#00000020",
            hover_overlay="#00000010"
        )
        
        # Test all attributes are present
        self.assertTrue(hasattr(theme, 'bg_primary'))
        self.assertTrue(hasattr(theme, 'bg_secondary'))
        self.assertTrue(hasattr(theme, 'text_primary'))
        self.assertTrue(hasattr(theme, 'accent_primary'))
        self.assertTrue(hasattr(theme, 'success'))
        self.assertTrue(hasattr(theme, 'warning'))
        self.assertTrue(hasattr(theme, 'error'))


class TestThemeManager(unittest.TestCase):
    """Test cases for ThemeManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tm = ThemeManager()
    
    def test_initialization_default_dark(self):
        """Test ThemeManager initializes with dark theme by default"""
        self.assertEqual(self.tm.current_theme_name, "dark")
        self.assertIsNotNone(self.tm.current_theme)
    
    def test_initialization_with_light(self):
        """Test ThemeManager initializes with light theme when specified"""
        tm = ThemeManager(current_theme="light")
        self.assertEqual(tm.current_theme_name, "light")
    
    def test_dark_theme_colors(self):
        """Test dark theme has correct colors"""
        self.tm.set_theme("dark")
        theme = self.tm.current_theme
        
        self.assertEqual(theme.bg_primary, "#262C27")
        self.assertEqual(theme.accent_primary, "#3498DB")  # Blue accent in dark theme
        self.assertIsInstance(theme.text_primary, str)
        self.assertTrue(theme.text_primary.startswith("#"))
    
    def test_light_theme_colors(self):
        """Test light theme has correct colors"""
        self.tm.set_theme("light")
        theme = self.tm.current_theme
        
        self.assertEqual(theme.bg_primary, "#FFFFFF")
        self.assertEqual(theme.accent_primary, "#34DB5E")  # Green accent in light theme
        self.assertIsInstance(theme.text_primary, str)
        self.assertTrue(theme.text_primary.startswith("#"))
    
    def test_toggle_theme_dark_to_light(self):
        """Test toggling from dark to light theme"""
        self.tm.set_theme("dark")
        self.assertEqual(self.tm.current_theme_name, "dark")
        
        result = self.tm.toggle_theme()
        self.assertEqual(self.tm.current_theme_name, "light")
        self.assertEqual(result, "light")
    
    def test_toggle_theme_light_to_dark(self):
        """Test toggling from light to dark theme"""
        self.tm.set_theme("light")
        self.assertEqual(self.tm.current_theme_name, "light")
        
        result = self.tm.toggle_theme()
        self.assertEqual(self.tm.current_theme_name, "dark")
        self.assertEqual(result, "dark")
    
    def test_multiple_toggles(self):
        """Test multiple theme toggles"""
        initial_theme = self.tm.current_theme_name
        
        self.tm.toggle_theme()
        self.assertNotEqual(self.tm.current_theme_name, initial_theme)
        
        self.tm.toggle_theme()
        self.assertEqual(self.tm.current_theme_name, initial_theme)
    
    def test_get_ctk_theme_mode_dark(self):
        """Test CTk theme mode for dark theme"""
        self.tm.set_theme("dark")
        mode = self.tm.get_ctk_theme_mode()
        self.assertEqual(mode, "dark")
    
    def test_get_ctk_theme_mode_light(self):
        """Test CTk theme mode for light theme"""
        self.tm.set_theme("light")
        mode = self.tm.get_ctk_theme_mode()
        self.assertEqual(mode, "light")
    
    def test_get_frame_colors(self):
        """Test getting frame colors"""
        colors = self.tm.get_frame_colors()
        
        self.assertIsInstance(colors, dict)
        self.assertIn('fg_color', colors)
        self.assertIn('border_color', colors)
    
    def test_get_button_colors(self):
        """Test getting button colors"""
        colors = self.tm.get_button_colors()
        
        self.assertIsInstance(colors, dict)
        self.assertIn('fg_color', colors)
        self.assertIn('hover_color', colors)
        self.assertIn('text_color', colors)
    
    def test_get_entry_colors(self):
        """Test getting entry colors"""
        colors = self.tm.get_entry_colors()
        
        self.assertIsInstance(colors, dict)
        self.assertIn('fg_color', colors)
        self.assertIn('border_color', colors)
        self.assertIn('text_color', colors)
    
    def test_frame_colors_match_theme(self):
        """Test that frame colors match current theme"""
        self.tm.set_theme("dark")
        colors = self.tm.get_frame_colors()
        
        self.assertEqual(colors['fg_color'], self.tm.current_theme.bg_secondary)
        self.assertEqual(colors['border_color'], self.tm.current_theme.border)
    
    def test_button_colors_match_theme(self):
        """Test that button colors match current theme"""
        self.tm.set_theme("light")
        colors = self.tm.get_button_colors()
        
        self.assertEqual(colors['fg_color'], self.tm.current_theme.accent_primary)
        self.assertEqual(colors['hover_color'], self.tm.current_theme.accent_hover)
    
    def test_entry_colors_match_theme(self):
        """Test that entry colors match current theme"""
        self.tm.set_theme("dark")
        colors = self.tm.get_entry_colors()
        
        self.assertEqual(colors['fg_color'], self.tm.current_theme.bg_secondary)
        self.assertEqual(colors['text_color'], self.tm.current_theme.text_primary)
        self.assertEqual(colors['border_color'], self.tm.current_theme.border)
    
    def test_theme_consistency_after_toggle(self):
        """Test that theme remains consistent after toggle"""
        self.tm.set_theme("dark")
        dark_bg = self.tm.current_theme.bg_primary
        
        self.tm.toggle_theme()
        light_bg = self.tm.current_theme.bg_primary
        
        self.tm.toggle_theme()
        dark_bg_again = self.tm.current_theme.bg_primary
        
        # Dark theme colors should be same before and after toggle cycle
        self.assertEqual(dark_bg, dark_bg_again)
        # Light and dark should be different
        self.assertNotEqual(dark_bg, light_bg)
    
    def test_invalid_theme_name(self):
        """Test setting invalid theme name is ignored"""
        original_theme = self.tm.current_theme_name
        self.tm.set_theme("nonexistent")
        
        # Should remain unchanged
        self.assertEqual(self.tm.current_theme_name, original_theme)
    
    def test_callback_registration(self):
        """Test theme change callback registration"""
        callback_called = []
        
        def callback(theme_name):
            callback_called.append(theme_name)
        
        self.tm.register_callback(callback)
        self.tm.toggle_theme()
        
        self.assertEqual(len(callback_called), 1)
        self.assertIn(callback_called[0], ["light", "dark"])
    
    def test_multiple_callbacks(self):
        """Test multiple callback registration"""
        call_count = [0, 0]
        
        def callback1(theme_name):
            call_count[0] += 1
        
        def callback2(theme_name):
            call_count[1] += 1
        
        self.tm.register_callback(callback1)
        self.tm.register_callback(callback2)
        self.tm.toggle_theme()
        
        self.assertEqual(call_count[0], 1)
        self.assertEqual(call_count[1], 1)
    
    def test_callbacks_on_set_theme(self):
        """Test callbacks are called on set_theme"""
        callback_called = []
        
        def callback(theme_name):
            callback_called.append(theme_name)
        
        self.tm.register_callback(callback)
        self.tm.set_theme("light")
        
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], "light")
    
    def test_color_format_validation(self):
        """Test that all colors are valid hex format or rgba"""
        for theme_name in ["dark", "light"]:
            self.tm.set_theme(theme_name)
            theme = self.tm.current_theme
            
            # Check key color attributes
            for attr in ['bg_primary', 'bg_secondary', 'text_primary', 
                        'accent_primary', 'border']:
                color = getattr(theme, attr)
                self.assertIsInstance(color, str)
                # Should be hex or rgba
                self.assertTrue(color.startswith('#') or color.startswith('rgba'),
                              f"{attr} in {theme_name} theme should be valid color format")
    
    def test_theme_has_all_required_attributes(self):
        """Test that theme objects have all required attributes"""
        required_attrs = [
            'bg_primary', 'bg_secondary', 'bg_tertiary',
            'text_primary', 'text_secondary', 'text_disabled',
            'accent_primary', 'accent_hover', 'accent_pressed',
            'success', 'warning', 'error', 'info',
            'border', 'shadow', 'hover_overlay'
        ]
        
        for theme_name in ["dark", "light"]:
            self.tm.set_theme(theme_name)
            theme = self.tm.current_theme
            
            for attr in required_attrs:
                self.assertTrue(hasattr(theme, attr),
                              f"{theme_name} theme missing attribute: {attr}")



if __name__ == '__main__':
    unittest.main()
