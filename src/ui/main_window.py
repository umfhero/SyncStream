"""
Main window for SyncStream application
"""

import customtkinter as ctk
from pathlib import Path
import tkinter as tk
from PIL import Image
import json
import os
import sys
from typing import Optional
import webbrowser

# Import version manager
from utils.version_manager import VersionManager

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("⚠️  tkinterdnd2 not available. Drag & drop will be disabled.")

try:
    from win10toast import ToastNotifier
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("⚠️  win10toast not available. Notifications will be disabled.")

try:
    import pystray
    from pystray import MenuItem as item
    SYSTRAY_AVAILABLE = True
except ImportError:
    SYSTRAY_AVAILABLE = False
    print("⚠️  pystray not available. System tray will be disabled.")


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        # Running in development
        base_path = Path(__file__).parent.parent.parent

    return base_path / relative_path


class MainWindow(ctk.CTk if not DRAG_DROP_AVAILABLE else TkinterDnD.Tk):
    """Main application window"""

    def __init__(self, theme_manager, network_manager, file_manager):
        super().__init__()

        # Store managers
        self.theme_manager = theme_manager
        self.network_manager = network_manager
        self.file_manager = file_manager

        # Initialize config manager
        from core.config_manager import ConfigManager
        self.config_manager = ConfigManager()

        # Initialize version manager
        self.version_manager = VersionManager()

        # Set assets path for use throughout the app
        self.assets_path = get_resource_path("Assets")

        # Clear old thumbnails to regenerate with transparency
        self._clear_thumbnail_cache()

        # Configure window
        self.title("SyncStream")

        # Track onboarding state
        self.showing_onboarding = False
        self.main_ui_built = False

        # Check if we need to show onboarding
        self._check_if_onboarding_needed()

        # Set window size based on whether we're showing onboarding
        if self.showing_onboarding:
            self.geometry("900x900")  # Taller for onboarding
        else:
            self.geometry("900x700")  # Normal size

        # Set theme to green and appearance mode
        ctk.set_default_color_theme("green")
        ctk.set_appearance_mode(self.theme_manager.get_ctk_theme_mode())
        # Fix theme background by setting background color to match ThemeManager
        try:
            theme_bg = self.theme_manager.current_theme.bg_primary
            # If ThemeManager exposes a name, use it to enforce light-mode white
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                # Ensure light mode background is white
                theme_bg = '#ffffff'
            # Ensure window background matches theme primary background
            self.configure(bg=theme_bg)
        except Exception:
            # Fallback to previous handling for TkinterDnD
            if DRAG_DROP_AVAILABLE:
                if self.theme_manager.current_theme_name == "dark":
                    self.configure(bg="#242424")
                else:
                    self.configure(bg="#ffffff")

        # Use a single app icon (blackp2p.ico) regardless of theme
        try:
            icon_path = self.assets_path / "blackp2p.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
            else:
                print(f"⚠️  Icon not found: {icon_path}")
        except Exception as e:
            print(f"⚠️  Failed to load icon: {e}")

        # Initialize notification system
        if NOTIFICATIONS_AVAILABLE:
            try:
                self.toaster = ToastNotifier()
            except Exception as e:
                print(f"⚠️  Failed to initialize notifications: {e}")
                self.toaster = None
        else:
            self.toaster = None

        # Initialize system tray
        self.tray_icon = None
        if SYSTRAY_AVAILABLE:
            self._setup_system_tray()

        # Load profiles
        self._load_profiles()

        # Initialize connection state
        self.is_connected = False
        self.led_status = "idle"  # idle, connecting, connected

        # Initialize shared files list and load from disk
        self.shared_files = []
        self._load_shared_files()

        # Standard button style to use across the UI (keep consistent)
        self.btn_width = 90
        self.btn_font = ("Arial", 14, "bold")

        # Track active transfers
        self.active_transfers = {}

        # Track file widgets for progress updates
        self.file_widgets = {}  # {file_path: {"frame": frame, "progress": progress_bar}}

        # Track drag-drop state
        self.is_dragging = False
        self.original_window_fg = None

        # Track view states
        self.gallery_visible = False
        self.statistics_visible = False
        self.settings_visible = False
        self.profile_manager_visible = False

        # Save files on close
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Register network callbacks
        self.network_manager.register_callback(
            'on_connecting', self._on_connecting)
        self.network_manager.register_callback(
            'on_connected', self._on_connected)
        self.network_manager.register_callback(
            'on_disconnected', self._on_disconnected)
        self.network_manager.register_callback(
            'on_connection_error', self._on_connection_error)

        # Register transfer protocol callbacks
        self.network_manager.transfer_protocol.register_callback(
            'on_transfer_start', self._on_transfer_start)
        self.network_manager.transfer_protocol.register_callback(
            'on_transfer_progress', self._on_transfer_progress)
        self.network_manager.transfer_protocol.register_callback(
            'on_transfer_complete', self._on_transfer_complete)
        self.network_manager.transfer_protocol.register_callback(
            'on_transfer_error', self._on_transfer_error)

        # Track compact mode state (must be before _build_ui)
        self.is_compact_mode = False
        self.compact_threshold_width = 400  # Switch to compact mode below this width
        self.manual_size_override = False  # Track if user manually toggled size

        # Check if we need to show onboarding (already done earlier, build appropriate UI)
        # Build appropriate UI (onboarding or main app)
        if self.showing_onboarding:
            self._build_onboarding_ui()
        else:
            self._build_ui()
            self.main_ui_built = True

        # Setup drag and drop if available and not in onboarding
        if DRAG_DROP_AVAILABLE and not self.showing_onboarding:
            self._setup_drag_drop()

        # Bind window resize event to check for compact mode
        if not self.showing_onboarding:
            self.bind("<Configure>", self._on_window_resize)

    def _load_profiles(self):
        """Load profile information from config"""
        try:
            config_path = get_resource_path("config") / "settings.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.profiles = config.get("profiles", {})
            else:
                # Default profiles
                self.profiles = {
                    "Majid": {"ip": "100.93.161.73", "port": 5000},
                    "Majid 2.0": {"ip": "100.92.141.68", "port": 5000},
                    "Nathan": {"ip": "100.122.120.65", "port": 5000}
                }
        except Exception as e:
            print(f"⚠️  Failed to load profiles: {e}")
            self.profiles = {}

    def _clear_thumbnail_cache(self):
        """Clear thumbnail cache to force regeneration with transparency"""
        try:
            import shutil
            thumb_dir = self.file_manager.thumbnails_dir
            if thumb_dir.exists():
                shutil.rmtree(thumb_dir)
                thumb_dir.mkdir(parents=True, exist_ok=True)
                print("🗑️  Cleared thumbnail cache")
        except Exception as e:
            print(f"⚠️  Failed to clear thumbnail cache: {e}")

    def _check_if_onboarding_needed(self):
        """Check if onboarding should be shown for first-time users"""
        try:
            # Check if user has set their own profile
            from core.config_manager import ConfigManager
            temp_config = ConfigManager()
            my_profile = temp_config.get_my_profile()

            if not my_profile:
                # No user profile exists, show onboarding
                self.showing_onboarding = True
            else:
                self.showing_onboarding = False
        except Exception as e:
            print(f"⚠️  Failed to check onboarding: {e}")
            self.showing_onboarding = False

    def _build_onboarding_ui(self):
        """Build the onboarding page UI"""
        # Configure window grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Theme toggle button row
        self.grid_rowconfigure(1, weight=1)  # Scrollable content

        # Get theme colors
        frame_colors = self.theme_manager.get_frame_colors()
        text_color = self.theme_manager.current_theme.text_primary

        # Top bar with just theme toggle
        top_bar = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))

        # Theme toggle button (top right)
        theme_btn = ctk.CTkButton(
            top_bar,
            text="🌙" if self.theme_manager.current_theme_name == "light" else "☀️",
            width=40,
            height=40,
            font=("Segoe UI Emoji", 18),
            command=self._toggle_theme_onboarding,
            fg_color=frame_colors.get("fg_color"),
            hover_color=frame_colors.get("hover_color", "#3a3a3a")
        )
        theme_btn.pack(side="right")
        self.onboarding_theme_btn = theme_btn

        # Create scrollable frame for content
        scrollable = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        scrollable.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        scrollable.grid_columnconfigure(0, weight=1)

        # Welcome header
        welcome_label = ctk.CTkLabel(
            scrollable,
            text="Welcome to SyncStream",
            font=("Segoe UI", 36, "bold"),
            text_color=text_color
        )
        welcome_label.grid(row=0, column=0, pady=(20, 10))

        # Subtitle
        subtitle = ctk.CTkLabel(
            scrollable,
            text="Let's get you set up with your first profile",
            font=("Segoe UI", 16),
            text_color=text_color
        )
        subtitle.grid(row=1, column=0, pady=(0, 30))

        # Tailscale setup section
        tailscale_frame = ctk.CTkFrame(
            scrollable, fg_color=frame_colors.get("fg_color"), corner_radius=12)
        tailscale_frame.grid(row=2, column=0, sticky="ew",
                             pady=(0, 30), padx=40)
        tailscale_frame.grid_columnconfigure(0, weight=1)

        tailscale_title = ctk.CTkLabel(
            tailscale_frame,
            text="Step 1: Install Tailscale",
            font=("Segoe UI", 20, "bold"),
            text_color=text_color
        )
        tailscale_title.grid(row=0, column=0, pady=(
            20, 10), padx=20, sticky="w")

        tailscale_desc = ctk.CTkLabel(
            tailscale_frame,
            text="SyncStream uses Tailscale to securely connect your devices.\nIf you don't have Tailscale installed yet, click the button below:",
            font=("Segoe UI", 14),
            text_color=text_color,
            justify="left"
        )
        tailscale_desc.grid(row=1, column=0, pady=(0, 15), padx=20, sticky="w")

        tailscale_btn = ctk.CTkButton(
            tailscale_frame,
            text="Open Tailscale Setup Guide",
            font=("Segoe UI", 14, "bold"),
            height=40,
            command=lambda: webbrowser.open(
                "https://tailscale.com/kb/1017/install"),
            fg_color="#0ea5e9",
            hover_color="#0284c7"
        )
        tailscale_btn.grid(row=2, column=0, pady=(0, 20), padx=20)

        # Profile creation section
        profile_frame = ctk.CTkFrame(
            scrollable, fg_color=frame_colors.get("fg_color"), corner_radius=12)
        profile_frame.grid(row=3, column=0, sticky="ew", pady=(0, 30), padx=40)
        profile_frame.grid_columnconfigure(0, weight=1)

        profile_title = ctk.CTkLabel(
            profile_frame,
            text="Step 2: Create Your Profile",
            font=("Segoe UI", 20, "bold"),
            text_color=text_color
        )
        profile_title.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        profile_desc = ctk.CTkLabel(
            profile_frame,
            text="Enter your device name and Tailscale IP address.\nYou can find your Tailscale IP in the Tailscale app.",
            font=("Segoe UI", 14),
            text_color=text_color,
            justify="left"
        )
        profile_desc.grid(row=1, column=0, pady=(0, 20), padx=20, sticky="w")

        # Profile name input
        name_label = ctk.CTkLabel(
            profile_frame,
            text="Profile Name (e.g., 'My Laptop'):",
            font=("Segoe UI", 14),
            text_color=text_color
        )
        name_label.grid(row=2, column=0, pady=(0, 5), padx=20, sticky="w")

        self.onboarding_name_entry = ctk.CTkEntry(
            profile_frame,
            font=("Segoe UI", 14),
            height=40,
            placeholder_text="Enter your profile name"
        )
        self.onboarding_name_entry.grid(
            row=3, column=0, pady=(0, 20), padx=20, sticky="ew")

        # IP address input
        ip_label = ctk.CTkLabel(
            profile_frame,
            text="Your Tailscale IP Address (e.g., '100.64.0.1'):",
            font=("Segoe UI", 14),
            text_color=text_color
        )
        ip_label.grid(row=4, column=0, pady=(0, 5), padx=20, sticky="w")

        self.onboarding_ip_entry = ctk.CTkEntry(
            profile_frame,
            font=("Segoe UI", 14),
            height=40,
            placeholder_text="Enter your Tailscale IP"
        )
        self.onboarding_ip_entry.grid(
            row=5, column=0, pady=(0, 20), padx=20, sticky="ew")

        # Error label (hidden by default)
        self.onboarding_error_label = ctk.CTkLabel(
            profile_frame,
            text="",
            font=("Segoe UI", 12),
            text_color="#ef4444"
        )
        self.onboarding_error_label.grid(
            row=6, column=0, pady=(0, 10), padx=20)
        self.onboarding_error_label.grid_remove()

        # Create profile button
        create_btn = ctk.CTkButton(
            profile_frame,
            text="Create Profile & Start Using SyncStream",
            font=("Segoe UI", 16, "bold"),
            height=50,
            command=self._create_profile_from_onboarding,
            fg_color="#22c55e",
            hover_color="#16a34a"
        )
        create_btn.grid(row=7, column=0, pady=(0, 20), padx=20, sticky="ew")

    def _toggle_theme_onboarding(self):
        """Toggle theme while in onboarding"""
        self.theme_manager.toggle_theme()
        # Update theme button emoji
        self.onboarding_theme_btn.configure(
            text="🌙" if self.theme_manager.current_theme_name == "light" else "☀️"
        )
        # Rebuild the entire onboarding UI to apply new theme
        for widget in self.winfo_children():
            widget.destroy()
        self._build_onboarding_ui()

    def _create_profile_from_onboarding(self):
        """Create profile from onboarding form"""
        name = self.onboarding_name_entry.get().strip()
        address = self.onboarding_ip_entry.get().strip()

        # Validate inputs
        if not name:
            self.onboarding_error_label.configure(
                text="Please enter a profile name")
            self.onboarding_error_label.grid()
            return

        if not address:
            self.onboarding_error_label.configure(
                text="Please enter your Tailscale IP address")
            self.onboarding_error_label.grid()
            return

        # Basic IP validation
        if not self._validate_ip(address):
            self.onboarding_error_label.configure(
                text="Please enter a valid IP address (e.g., 100.64.0.1)")
            self.onboarding_error_label.grid()
            return

        # Create the profile
        try:
            # Set as user's own profile (onboarding)
            self.config_manager.set_my_profile(name, address)
            self.config_manager.save_profiles()

            print(f"✅ My profile created: {name} ({address})")

            # Switch to main UI
            self._switch_to_main_ui()
        except Exception as e:
            self.onboarding_error_label.configure(
                text=f"Failed to create profile: {str(e)}")
            self.onboarding_error_label.grid()

    def _switch_to_main_ui(self):
        """Switch from onboarding to main UI"""
        # Clear all widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Reset state
        self.showing_onboarding = False

        # Resize window back to normal height
        self.geometry("900x700")

        # Force window update to apply geometry change
        self.update_idletasks()

        # Reconfigure window grid for main UI
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Reload config to get new profiles
        from core.config_manager import ConfigManager
        self.config_manager = ConfigManager()

        # Build main UI
        self._build_ui()
        self.main_ui_built = True

        # Setup drag and drop
        if DRAG_DROP_AVAILABLE:
            self._setup_drag_drop()

        # Bind window resize event
        self.bind("<Configure>", self._on_window_resize)

        # Refresh profile dropdowns
        self._refresh_profiles()

        # Force a final update to ensure proper layout
        self.update_idletasks()

    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except:
            return False

    def _open_url(self, url: str):
        """Open URL in default browser"""
        import webbrowser
        webbrowser.open(url)

    def _check_onboarding(self):
        """Deprecated - onboarding is now checked at startup"""
        pass

    def _show_onboarding(self, config_manager):
        """Deprecated - onboarding is now a full page view"""
        pass

    def _refresh_profiles(self):
        """Refresh the profile dropdowns with latest data"""
        try:
            from core.config_manager import ConfigManager
            config_manager = ConfigManager()
            my_profile = config_manager.get_my_profile()
            peer_profiles = config_manager.get_profiles()

            if hasattr(self, 'my_profile_selector') and hasattr(self, 'peer_profile_selector'):
                # Update My Profile dropdown (only shows user's own profile)
                if my_profile:
                    self.my_profile_selector.configure(
                        values=[my_profile.name])
                    self.my_profile_selector.set(my_profile.name)
                    self.my_profile_var.set(my_profile.name)
                else:
                    self.my_profile_selector.configure(values=["No Profile"])
                    self.my_profile_selector.set("No Profile")

                # Update Connect to dropdown (shows peer profiles)
                if peer_profiles and len(peer_profiles) > 0:
                    peer_names = [p.name for p in peer_profiles]
                    self.peer_profile_selector.configure(values=peer_names)
                    self.peer_profile_selector.set(peer_names[0])
                    self.peer_profile_var.set(peer_names[0])
                else:
                    self.peer_profile_selector.configure(values=["No Peers"])
                    self.peer_profile_selector.set("No Peers")
        except Exception as e:
            print(f"⚠️  Failed to refresh profiles: {e}")

    def _load_shared_files(self):
        """Load shared files from persistent storage"""
        try:
            config_path = os.path.join(os.path.expanduser(
                "~"), ".syncstream", "shared_files.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_paths = json.load(f)
                    # Only add files that still exist
                    for path in file_paths:
                        if os.path.exists(path) and path not in self.shared_files:
                            self.shared_files.append(path)
                    print(f"✅ Loaded {len(self.shared_files)} shared files")
        except Exception as e:
            print(f"⚠️  Failed to load shared files: {e}")

    def _save_shared_files(self):
        """Save shared files to persistent storage"""
        try:
            config_dir = os.path.join(os.path.expanduser("~"), ".syncstream")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "shared_files.json")

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.shared_files, f, indent=2)
            print(f"✅ Saved {len(self.shared_files)} shared files")
        except Exception as e:
            print(f"⚠️  Failed to save shared files: {e}")

    def _on_window_close(self):
        """Handle window close event"""
        # Save shared files
        self._save_shared_files()

        # If system tray is available, minimize to tray instead of closing
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.withdraw()  # Hide window
            if self.toaster:
                self._show_notification(
                    "SyncStream",
                    "App minimized to system tray"
                )
        else:
            # Shutdown network manager
            if self.network_manager:
                self.network_manager.shutdown()
            self.destroy()

    def _build_ui(self):
        """Build the main UI"""
        # Create a container frame with theme background so the app matches theme
        try:
            # Prefer ThemeManager's primary bg when available
            theme_bg = self.theme_manager.current_theme.bg_primary
            # If ThemeManager exposes a name, use it to enforce light-mode white
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                # Ensure light mode background is white (avoid stray dark defaults)
                theme_bg = '#ffffff'
        except Exception:
            theme_bg = None
        # Fallback to CTk appearance mode if ThemeManager did not provide info
        if not theme_bg:
            try:
                app_mode = ctk.get_appearance_mode()
                if app_mode and str(app_mode).lower().startswith('light'):
                    theme_bg = '#ffffff'
                else:
                    theme_bg = '#121212'
            except Exception:
                theme_bg = '#121212'

        # Use the theme primary background for the main container so "transparent"
        # child frames render over the correct background instead of CTk's default
        container = ctk.CTkFrame(self, fg_color=theme_bg, corner_radius=0)
        container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Configure window grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Configure container grid
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=0)  # Top bar
        container.grid_rowconfigure(1, weight=1)  # Main content

        # Build sections inside container
        self._build_top_bar(container)
        self._build_main_content(container)

    def _build_top_bar(self, parent):
        """Build the top bar with profiles and connection"""
        # Theme-aware top bar frame - use corner_radius=0 and we'll add rounded bottom corners
        frame_colors = self.theme_manager.get_frame_colors()
        top_fg = frame_colors.get("fg_color", None)
        top_border = frame_colors.get("border_color", None)

        # Container frame with no rounded corners (straight on top)
        top_frame = ctk.CTkFrame(
            parent, fg_color=top_fg, border_color=top_border, border_width=1, corner_radius=0)
        # store reference for later theme updates
        self.top_frame = top_frame
        # Touch edges horizontally (no horizontal padding), small vertical gap below
        top_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 8))

        # Add a rounded overlay frame at the bottom to create bottom-rounded effect
        bottom_rounded = ctk.CTkFrame(
            top_frame, fg_color=top_fg, corner_radius=12, height=24)
        bottom_rounded.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        self.top_frame_rounded_bottom = bottom_rounded

        # Create an inner content frame so the bar can touch window edges while
        # the inner controls have comfortable padding from the sides.
        inner_top = ctk.CTkFrame(top_frame, fg_color="transparent")
        inner_top.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)

        # Configure columns on inner frame - push right elements to the right
        inner_top.grid_columnconfigure(0, weight=0)  # My Profile label
        inner_top.grid_columnconfigure(1, weight=0)  # My Profile selector
        inner_top.grid_columnconfigure(2, weight=0)  # Pipe
        inner_top.grid_columnconfigure(3, weight=0)  # Connect to label
        inner_top.grid_columnconfigure(4, weight=1)  # Peer selector - expands
        inner_top.grid_columnconfigure(5, weight=0)  # Add Profile button
        inner_top.grid_columnconfigure(6, weight=0)  # Stats button
        inner_top.grid_columnconfigure(7, weight=0)  # Settings button

        # My Profile label
        my_profile_label = ctk.CTkLabel(
            inner_top,
            text="My Profile:",
            font=("Arial", 13, "bold")
        )
        my_profile_label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        # My Profile selector (shows user's own profile)
        my_profile = self.config_manager.get_my_profile()
        my_profile_name = my_profile.name if my_profile else "No Profile"

        self.my_profile_var = ctk.StringVar(value=my_profile_name)
        self.my_profile_selector = ctk.CTkOptionMenu(
            inner_top,
            variable=self.my_profile_var,
            values=[my_profile_name],
            width=10,  # Will be updated dynamically
            font=self.btn_font,
            dynamic_resizing=True  # Enable dynamic resizing
        )
        self.my_profile_selector.grid(
            row=0, column=1, padx=(0, 10), sticky="w")

        # Pipe separator
        pipe_label = ctk.CTkLabel(
            inner_top,
            text="|",
            font=("Arial", 16, "bold")
        )
        pipe_label.grid(row=0, column=2, padx=10)

        # Connect to label
        connect_label = ctk.CTkLabel(
            inner_top,
            text="Connect to:",
            font=("Arial", 13, "bold")
        )
        connect_label.grid(row=0, column=3, padx=(0, 5), sticky="w")

        # Peer Profile selector (shows peer profiles to connect to)
        peer_profiles = self.config_manager.get_profiles()
        peer_names = [p.name for p in peer_profiles] if peer_profiles else [
            "No Peers"]
        peer_default = peer_names[0] if peer_names else "No Peers"

        self.peer_profile_var = ctk.StringVar(value=peer_default)
        self.peer_profile_selector = ctk.CTkOptionMenu(
            inner_top,
            variable=self.peer_profile_var,
            values=peer_names,
            width=10,  # Will be updated dynamically
            font=self.btn_font,
            dynamic_resizing=True  # Enable dynamic resizing
        )
        self.peer_profile_selector.grid(
            row=0, column=4, padx=(0, 10), sticky="w")

        # Add Profile button with icon
        try:
            addprofile_icon_path = Path(
                __file__).parent.parent.parent / "Assets" / "addprofile.png"
            if addprofile_icon_path.exists():
                addprofile_icon = ctk.CTkImage(
                    light_image=Image.open(addprofile_icon_path),
                    dark_image=Image.open(addprofile_icon_path),
                    size=(24, 24)
                )
                self.add_profile_btn = ctk.CTkButton(
                    inner_top,
                    image=addprofile_icon,
                    text="",
                    width=40,
                    height=40,
                    command=self._open_profile_manager,
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
                self.add_profile_btn.image = addprofile_icon  # Keep reference
            else:
                # Fallback to emoji if icon not found
                self.add_profile_btn = ctk.CTkButton(
                    inner_top,
                    text="➕",
                    width=40,
                    height=40,
                    command=self._open_profile_manager,
                    font=("Arial", 20),
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
        except Exception as e:
            print(f"⚠️  Failed to load add profile icon: {e}")
            self.add_profile_btn = ctk.CTkButton(
                inner_top,
                text="➕",
                width=40,
                height=40,
                command=self._open_profile_manager,
                font=("Arial", 20),
                fg_color="transparent",
                hover_color=("gray80", "gray30")
            )

        self.add_profile_btn.grid(row=0, column=5, padx=(0, 10), sticky="w")

        # Statistics button with icon
        try:
            stats_icon_path = Path(
                __file__).parent.parent.parent / "Assets" / "stats.png"
            if stats_icon_path.exists():
                stats_icon = ctk.CTkImage(
                    light_image=Image.open(stats_icon_path),
                    dark_image=Image.open(stats_icon_path),
                    size=(24, 24)
                )
                self.stats_btn = ctk.CTkButton(
                    inner_top,
                    image=stats_icon,
                    text="",
                    width=40,
                    height=40,
                    command=self._toggle_statistics,
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
                self.stats_btn.image = stats_icon  # Keep reference
            else:
                # Fallback to emoji if icon not found
                self.stats_btn = ctk.CTkButton(
                    inner_top,
                    text="📊",
                    width=40,
                    height=40,
                    command=self._toggle_statistics,
                    font=("Arial", 20),
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
        except Exception as e:
            print(f"⚠️  Failed to load stats icon: {e}")
            self.stats_btn = ctk.CTkButton(
                inner_top,
                text="📊",
                width=40,
                height=40,
                command=self._toggle_statistics,
                font=("Arial", 20),
                fg_color="transparent",
                hover_color=("gray80", "gray30")
            )

        self.stats_btn.grid(row=0, column=6, padx=(10, 0), sticky="e")

        # Settings button with icon
        try:
            settings_icon_path = Path(
                __file__).parent.parent.parent / "Assets" / "settings.png"
            if settings_icon_path.exists():
                settings_icon = ctk.CTkImage(
                    light_image=Image.open(settings_icon_path),
                    dark_image=Image.open(settings_icon_path),
                    size=(24, 24)
                )
                self.settings_btn = ctk.CTkButton(
                    inner_top,
                    image=settings_icon,
                    text="",
                    width=40,
                    height=40,
                    command=self._open_settings,
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
                self.settings_btn.image = settings_icon  # Keep reference
            else:
                # Fallback to emoji if icon not found
                self.settings_btn = ctk.CTkButton(
                    inner_top,
                    text="⚙️",
                    width=40,
                    height=40,
                    command=self._open_settings,
                    font=("Arial", 20),
                    fg_color="transparent",
                    hover_color=("gray80", "gray30")
                )
        except Exception as e:
            print(f"⚠️  Failed to load settings icon: {e}")
            self.settings_btn = ctk.CTkButton(
                inner_top,
                text="⚙️",
                width=40,
                height=40,
                command=self._open_settings,
                font=("Arial", 20),
                fg_color="transparent",
                hover_color=("gray80", "gray30")
            )

        self.settings_btn.grid(row=0, column=7, padx=(5, 0), sticky="e")

        # Note: Connect button and status indicator live in the bottom bar now
        # (bottom bar holds the actionable controls). We intentionally do not
        # create connect/status widgets in the top bar so the top remains a
        # clean, informational bar.
        # Apply initial theme to top/bottom bars
        try:
            self._update_top_bar_theme()
        except Exception:
            pass

    def _update_top_bar_theme(self):
        """Apply current theme colors to the top bar and bottom bar."""
        try:
            frame_colors = self.theme_manager.get_frame_colors()
            top_fg = frame_colors.get("fg_color", None)
            top_border = frame_colors.get("border_color", None)
            if hasattr(self, 'top_frame') and self.top_frame:
                self.top_frame.configure(
                    fg_color=top_fg, border_color=top_border)

            # Update the rounded bottom overlay too
            if hasattr(self, 'top_frame_rounded_bottom') and self.top_frame_rounded_bottom:
                self.top_frame_rounded_bottom.configure(fg_color=top_fg)

            # bottom bar too
            if hasattr(self, 'bottom_bar') and self.bottom_bar:
                self.bottom_bar.configure(
                    fg_color=top_fg, border_color=top_border)
        except Exception as e:
            print(f"⚠️  Failed to update top/bottom bar theme: {e}")

    def _build_main_content(self, parent):
        """Build the main content area"""
        # Determine theme background for content area (fallback if needed)
        try:
            theme_bg = self.theme_manager.current_theme.bg_primary
            # If ThemeManager exposes a name, use it to enforce light-mode white
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                # Ensure light mode background is white
                theme_bg = '#ffffff'
        except Exception:
            theme_bg = None
        if not theme_bg:
            try:
                mode = self.theme_manager.current_theme_name
            except Exception:
                mode = 'dark'
            theme_bg = '#ffffff' if mode == 'light' else '#121212'

        main_frame = ctk.CTkFrame(parent, fg_color=theme_bg)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Store reference for theme updates
        self.main_frame = main_frame

        # Configure grid
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)

        # Content frame (drag & drop area) - use theme background so transparent
        # children show the theme correctly (prevents fallback to hard-coded dark)
        self.content_frame = ctk.CTkFrame(main_frame, fg_color=theme_bg)
        self.content_frame.grid(
            row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        # Configure content frame grid
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)  # Icon
        self.content_frame.grid_rowconfigure(1, weight=0)  # Label
        self.content_frame.grid_rowconfigure(2, weight=0)  # Button
        self.content_frame.grid_rowconfigure(3, weight=1)  # Gallery

        # Store original colors for hover effect
        self.content_frame_original_fg = self.content_frame.cget("fg_color")

        # Drag and drop zone - upload icon
        try:
            icon_name = "whiteupload.png" if self.theme_manager.current_theme_name == "dark" else "blackupload.png"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                upload_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(64, 64)
                )
                self.drop_icon = ctk.CTkLabel(
                    self.content_frame,
                    text="",
                    image=upload_image
                )
            else:
                self.drop_icon = ctk.CTkLabel(
                    self.content_frame,
                    text="📤",
                    font=("Arial", 48)
                )
        except Exception as e:
            print(f"⚠️  Failed to load upload icon: {e}")
            self.drop_icon = ctk.CTkLabel(
                self.content_frame,
                text="📤",
                font=("Arial", 48)
            )

        self.drop_icon.grid(row=0, column=0, pady=(40, 10))

        # Drag & drop text
        self.drop_label = ctk.CTkLabel(
            self.content_frame,
            text="Drag & Drop Files Here or",
            font=("Arial", 16, "bold")
        )
        self.drop_label.grid(row=1, column=0, pady=5)

        # Browse button
        self.browse_btn = ctk.CTkButton(
            self.content_frame,
            text="Browse Files",
            command=self._browse_files,
            width=self.btn_width,
            font=self.btn_font
        )
        self.browse_btn.grid(row=2, column=0, pady=(5, 40))

        # File gallery (hidden by default)
        self.gallery_visible = False
        self.current_filter = "All"  # All, Images, Documents, Videos, Archives

        # Get proper theme background color
        try:
            gallery_bg = self.theme_manager.current_theme.bg_primary
            # If ThemeManager exposes a name, use it to enforce light-mode white
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                # Ensure light mode background is white
                gallery_bg = '#ffffff'
        except Exception:
            # Fallback to CTk appearance mode
            try:
                app_mode = ctk.get_appearance_mode()
                if app_mode and str(app_mode).lower().startswith('light'):
                    gallery_bg = '#ffffff'
                else:
                    gallery_bg = self.theme_manager.current_theme.bg_primary
            except Exception:
                gallery_bg = self.theme_manager.current_theme.bg_primary

        self.gallery_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text="",
            fg_color=gallery_bg
        )
        # Don't grid it yet - will be shown on toggle

        # Configure gallery grid
        for i in range(4):
            self.gallery_frame.grid_columnconfigure(i, weight=1)

        # Bind mousewheel for row-based scrolling
        self._bind_gallery_scroll()

        # Statistics page (hidden by default)
        self.statistics_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text="",
            fg_color='transparent',
            scrollbar_fg_color='transparent',
            scrollbar_button_color=("gray70", "gray30"),
            corner_radius=0,
            border_width=0
        )
        # Don't grid it yet - will be shown on toggle

        # Settings page (hidden by default)
        self.settings_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text="",
            fg_color='transparent',
            scrollbar_fg_color='transparent',
            scrollbar_button_color=("gray70", "gray30"),
            corner_radius=0,
            border_width=0
        )
        # Don't grid it yet - will be shown on toggle

        # Profile Manager page (hidden by default)
        self.profile_manager_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text="",
            fg_color='transparent',
            scrollbar_fg_color='transparent',
            scrollbar_button_color=("gray70", "gray30"),
            corner_radius=0,
            border_width=0
        )
        # Don't grid it yet - will be shown on toggle

        # Apply initial scrollable frame backgrounds
        self._update_scrollable_frame_backgrounds()

        # Bottom bar - single rounded clean bar for gallery controls
        frame_colors = self.theme_manager.get_frame_colors()
        bottom_bar = ctk.CTkFrame(main_frame, fg_color=frame_colors.get(
            "fg_color"), corner_radius=12, border_width=1, border_color=frame_colors.get("border_color"))
        # Add margin around bottom bar
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 10))

        # Store reference for theme updates
        self.bottom_bar = bottom_bar

        # Inner padded area inside the bottom bar so controls don't touch edges
        inner_bottom = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        inner_bottom.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
        # Define a consistent button style to match the Show Gallery button
        # Store on self so other methods (gallery loader) can reuse the same style
        self.btn_width = 90
        self.btn_font = ("Arial", 14, "bold")

        # Configure grid columns: left buttons, spacer, right buttons
        inner_bottom.grid_columnconfigure(0, weight=0)  # Show Gallery
        inner_bottom.grid_columnconfigure(1, weight=0)  # Search (when visible)
        inner_bottom.grid_columnconfigure(2, weight=0)  # Filter (when visible)
        # Spacer - expands to push right buttons to the right
        inner_bottom.grid_columnconfigure(3, weight=1)
        inner_bottom.grid_columnconfigure(4, weight=0)  # Right group container

        # Store bottom_bar reference for later use
        self.bottom_bar = bottom_bar
        # Allow inner_bottom to expand
        bottom_bar.grid_columnconfigure(0, weight=1)

        # Gallery toggle button (left side)
        self.gallery_btn = ctk.CTkButton(
            inner_bottom,
            text="Show Gallery",
            width=self.btn_width,
            command=self._toggle_gallery,
            font=self.btn_font
        )
        self.gallery_btn.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="w")

        # Search box (hidden by default, shown when gallery is visible)
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self._filter_gallery())
        self.search_entry = ctk.CTkEntry(
            inner_bottom,
            placeholder_text="Search here...",
            width=200,
            textvariable=self.search_var,
            font=("Arial", 11),
            fg_color="transparent"
        )
        # Don't grid it yet - will be shown when gallery is visible (column 1)

        # Filter button (hidden by default, shown when gallery is visible)
        self.filter_btn = ctk.CTkButton(
            inner_bottom,
            text="Filter: All",
            width=self.btn_width,
            command=self._cycle_filter,
            font=self.btn_font
        )
        # Don't grid it yet - will be shown when gallery is visible (column 2)

        # Create a container frame for right-aligned buttons (Connect, Status LED, Theme)
        right_buttons_frame = ctk.CTkFrame(
            inner_bottom, fg_color="transparent")
        right_buttons_frame.grid(row=0, column=4, sticky="e", padx=0, pady=0)

        # Configure right buttons frame columns - no weight so they stay together
        right_buttons_frame.grid_columnconfigure(0, weight=0)  # Connect
        right_buttons_frame.grid_columnconfigure(1, weight=0)  # Status
        right_buttons_frame.grid_columnconfigure(2, weight=0)  # Size toggle
        right_buttons_frame.grid_columnconfigure(3, weight=0)  # Theme

        try:
            icon_name = "sun.png" if self.theme_manager.current_theme_name == "dark" else "moon.png"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                icon_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(24, 24)
                )
                # Keep theme toggle but match button sizing/style - smaller width
                self.theme_btn = ctk.CTkButton(
                    right_buttons_frame,
                    text="",
                    image=icon_image,
                    command=self._toggle_theme,
                    width=40,  # Smaller width
                    height=40,
                    fg_color="transparent",
                    hover=False  # Disable hover effect completely
                )
            else:
                theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
                self.theme_btn = ctk.CTkButton(
                    right_buttons_frame,
                    text=theme_icon,
                    command=self._toggle_theme,
                    width=40,  # Smaller width
                    height=40,
                    font=self.btn_font,
                    fg_color="transparent",
                    hover=False  # Disable hover effect completely
                )
        except Exception as e:
            theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
            self.theme_btn = ctk.CTkButton(
                right_buttons_frame,
                text=theme_icon,
                command=self._toggle_theme,
                width=40,  # Smaller width
                height=40,
                font=self.btn_font,
                fg_color="transparent",
                hover=False  # Disable hover effect completely
            )

        # Connect button
        self.connect_btn = ctk.CTkButton(
            right_buttons_frame,
            text="Connect",
            command=self._toggle_connection,
            width=self.btn_width,
            font=self.btn_font
        )
        self.connect_btn.grid(row=0, column=0, padx=(0, 12))

        # Status LED
        self.status_led = ctk.CTkLabel(
            right_buttons_frame,
            text="●",
            font=("Arial", 18),
            text_color="red"
        )
        self.status_led.grid(row=0, column=1, padx=(0, 8))

        # Size toggle button (compact/normal mode toggle) with up/down icons
        try:
            # Start with down icon (for compact mode)
            icon_name = "down.png"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                size_icon_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(24, 24)
                )
                self.size_btn = ctk.CTkButton(
                    right_buttons_frame,
                    text="",
                    image=size_icon_image,
                    command=self._toggle_size_mode,
                    width=40,
                    height=40,
                    fg_color="transparent",
                    hover=False  # Disable hover effect completely
                )
            else:
                # Fallback to text if icon not found
                self.size_btn = ctk.CTkButton(
                    right_buttons_frame,
                    text="⇄",
                    command=self._toggle_size_mode,
                    width=40,
                    height=40,
                    font=("Arial", 20, "bold"),
                    fg_color="transparent",
                    hover=False  # Disable hover effect completely
                )
        except Exception as e:
            print(f"⚠️  Failed to load size icon: {e}")
            self.size_btn = ctk.CTkButton(
                right_buttons_frame,
                text="⇄",
                command=self._toggle_size_mode,
                width=40,
                height=40,
                font=("Arial", 20, "bold"),
                fg_color="transparent",
                hover=False  # Disable hover effect completely
            )

        self.size_btn.grid(row=0, column=2, padx=(0, 8))

        # Theme toggle (already created above)
        self.theme_btn.grid(row=0, column=3, padx=(0, 0))

        # Load file gallery
        self._load_file_gallery()

    def _bind_gallery_scroll(self):
        """Bind mousewheel events for row-based scrolling in gallery"""
        def on_mousewheel(event):
            if not self.gallery_visible:
                return

            # Calculate row height based on current mode
            if self.is_compact_mode:
                row_height = 259 + 16  # card_height + pady (8*2)
            else:
                row_height = 160 + 16  # card_height + pady (8*2)

            # Get the canvas
            canvas = self.gallery_frame._parent_canvas

            # Get current scroll position
            current_pos = canvas.yview()[0]  # Get top position (0.0 to 1.0)

            # Get total scrollable height
            bbox = canvas.bbox("all")
            if bbox:
                total_height = bbox[3] - bbox[1]
                visible_height = canvas.winfo_height()

                # Calculate current pixel position
                current_pixels = current_pos * total_height

                # Calculate target position (move by one row)
                if event.delta > 0:  # Scroll up
                    target_pixels = max(0, current_pixels - row_height)
                else:  # Scroll down
                    max_scroll = total_height - visible_height
                    target_pixels = min(
                        max_scroll, current_pixels + row_height)

                # Convert back to fraction
                target_fraction = target_pixels / total_height if total_height > 0 else 0

                # Set the new scroll position
                canvas.yview_moveto(target_fraction)

        # Bind to the gallery frame and its internal canvas
        self.gallery_frame.bind_all("<MouseWheel>", on_mousewheel)

    def _setup_drag_drop(self):
        """Setup drag and drop functionality"""
        if not DRAG_DROP_AVAILABLE:
            return

        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._handle_drop)
            self.dnd_bind('<<DragEnter>>', self._handle_drag_enter)
            self.dnd_bind('<<DragLeave>>', self._handle_drag_leave)

            print("✅ Drag & drop enabled")
        except Exception as e:
            print(f"⚠️  Failed to setup drag & drop: {e}")

    def _handle_drag_enter(self, event):
        """Handle drag enter - tint window to opposite theme color"""
        try:
            if self.is_dragging:
                return

            self.is_dragging = True

            # Get opposite theme color for tinting
            if self.theme_manager.current_theme_name == "dark":
                # In dark mode, tint to light color (bluish-white)
                tint_color = "#E8F4FF"  # Light blue tint
            else:
                # In light mode, tint to dark color (dark blue)
                tint_color = "#1a2332"  # Dark blue tint

            # Only tint the content frame (not root window)
            if hasattr(self, 'content_frame'):
                self.content_frame.configure(fg_color=tint_color)

            # Show a visual indicator
            if hasattr(self, 'drop_label'):
                self.drop_label.configure(
                    text="📥 Drop files here to share",
                    font=("Arial", 24, "bold")
                )

            print("📥 Drag detected - window tinted")
        except Exception as e:
            print(f"⚠️  Drag enter effect failed: {e}")

    def _handle_drag_leave(self, event):
        """Handle drag leave - restore original colors"""
        try:
            self.is_dragging = False

            # Restore content frame original color
            if hasattr(self, 'content_frame_original_fg'):
                self.content_frame.configure(
                    fg_color=self.content_frame_original_fg)

            # Restore drop label
            if hasattr(self, 'drop_label'):
                self.drop_label.configure(
                    text="Drag & Drop Files Here",
                    font=("Arial", 16)
                )

            print("📤 Drag left - colors restored")
        except Exception as e:
            print(f"⚠️  Drag leave effect failed: {e}")

    def _on_window_resize(self, event):
        """Handle window resize event to switch between normal and compact modes"""
        # Only process resize events for the main window (not child widgets)
        if event.widget != self:
            return

        # Don't auto-switch if user manually toggled (give them 3 seconds before re-enabling auto)
        if self.manual_size_override:
            return

        try:
            window_width = self.winfo_width()
            screen_width = self.winfo_screenwidth()

            # Calculate percentage of screen width
            width_percentage = (window_width / screen_width) * 100

            # Check if we need to switch modes
            should_be_compact = window_width < self.compact_threshold_width or width_percentage < 30

            if should_be_compact and not self.is_compact_mode:
                self._switch_to_compact_mode()
            elif not should_be_compact and self.is_compact_mode:
                self._switch_to_normal_mode()

            # Manage search/filter visibility based on window width even when not switching modes
            if self.gallery_visible and hasattr(self, 'search_entry') and hasattr(self, 'filter_btn'):
                if window_width < 600:
                    # Hide search and filter if window is too narrow
                    self.search_entry.grid_remove()
                    self.filter_btn.grid_remove()
                elif not self.is_compact_mode:
                    # Show search and filter if window is wide enough and not in compact mode
                    self.search_entry.grid(row=0, column=1, padx=8, sticky="w")
                    self.filter_btn.grid(
                        row=0, column=2, padx=(0, 8), sticky="w")
        except Exception as e:
            print(f"⚠️  Window resize handler error: {e}")

    def _toggle_size_mode(self):
        """Manually toggle between compact and normal modes"""
        try:
            # Set manual override to prevent auto-switching during manual toggle
            self.manual_size_override = True

            if self.is_compact_mode:
                # Switch to normal mode and resize window
                self._switch_to_normal_mode()
                # Resize window to a comfortable normal size
                self.geometry("900x700")
                # Update icon to down arrow (for going compact)
                self._update_size_button_icon("down.png")
                print("🖥️  Manual switch to normal mode")
            else:
                # Switch to compact mode and resize window
                self._switch_to_compact_mode()
                # Resize window to compact size (295px height)
                self.geometry("380x295")
                # Update icon to up arrow (for going normal)
                self._update_size_button_icon("up.png")
                print("📱 Manual switch to compact mode")

            # Re-enable auto-switching after 2 seconds
            self.after(2000, lambda: setattr(
                self, 'manual_size_override', False))
        except Exception as e:
            print(f"⚠️  Size toggle error: {e}")

    def _update_size_button_icon(self, icon_name):
        """Update the size button icon"""
        try:
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name
            if icon_path.exists():
                new_icon = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(24, 24)
                )
                self.size_btn.configure(image=new_icon)
        except Exception as e:
            print(f"⚠️  Failed to update size icon: {e}")

    def _switch_to_compact_mode(self):
        """Switch to compact mode - minimal UI"""
        try:
            self.is_compact_mode = True
            print("📱 Switching to compact mode")

            # Set compact window size (only if window is visible) - 380x295
            if self.winfo_viewable():
                self.geometry("380x295")

            # Hide top bar (profile selectors)
            if hasattr(self, 'top_frame') and self.top_frame:
                self.top_frame.grid_remove()

            # Keep gallery visible if it's already showing, but hide search and filter
            if hasattr(self, 'gallery_visible') and self.gallery_visible:
                # Reload gallery with smaller thumbnails for compact mode
                self._load_file_gallery()

            # Hide search and filter buttons
            if hasattr(self, 'search_entry') and self.search_entry:
                self.search_entry.grid_remove()
            if hasattr(self, 'filter_btn') and self.filter_btn:
                self.filter_btn.grid_remove()

            # Update gallery button text
            if hasattr(self, 'gallery_btn'):
                if hasattr(self, 'gallery_visible') and self.gallery_visible:
                    self.gallery_btn.configure(text="Hide Gallery")
                else:
                    self.gallery_btn.configure(text="Gallery")

            # Make drag-drop label more prominent in compact mode
            if hasattr(self, 'drop_label'):
                self.drop_label.configure(
                    text="Drop Files\nto Share",
                    font=("Arial", 14, "bold")
                )
        except Exception as e:
            print(f"⚠️  Failed to switch to compact mode: {e}")

    def _switch_to_normal_mode(self):
        """Switch back to normal mode - full UI"""
        try:
            self.is_compact_mode = False
            print("🖥️  Switching to normal mode")

            # Restore normal window size (only if window is visible)
            if self.winfo_viewable():
                width = self.config_manager.settings.window_width or 1200
                height = self.config_manager.settings.window_height or 800
                self.geometry(f"{width}x{height}")

            # Show top bar
            if hasattr(self, 'top_frame') and self.top_frame:
                self.top_frame.grid()

            # Reload gallery with normal size thumbnails if it was visible
            if hasattr(self, 'gallery_visible') and self.gallery_visible:
                self._load_file_gallery()
                if hasattr(self, 'gallery_frame') and self.gallery_frame:
                    self.gallery_frame.grid()
                    # Show search and filter in normal mode if window is wide enough
                    window_width = self.winfo_width()
                    if window_width > 600:
                        if hasattr(self, 'search_entry'):
                            self.search_entry.grid(
                                row=0, column=1, padx=8, sticky="w")
                        if hasattr(self, 'filter_btn'):
                            self.filter_btn.grid(
                                row=0, column=2, padx=(0, 8), sticky="w")

            # Update gallery button text
            if hasattr(self, 'gallery_btn'):
                if hasattr(self, 'gallery_visible') and self.gallery_visible:
                    self.gallery_btn.configure(text="Hide Gallery")
                else:
                    self.gallery_btn.configure(text="Show Gallery")

            # Restore normal drag-drop label
            if hasattr(self, 'drop_label'):
                self.drop_label.configure(
                    text="Drag & Drop Files Here",
                    font=("Arial", 16)
                )
        except Exception as e:
            print(f"⚠️  Failed to switch to normal mode: {e}")

    def _darken_color(self, color):
        """Darken a color by 10%"""
        if color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = max(0, int(r * 0.9))
            g = max(0, int(g * 0.9))
            b = max(0, int(b * 0.9))
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    def _setup_system_tray(self):
        """Setup system tray icon"""
        try:
            # Load icon image - check multiple locations
            icon_name = "blackp2p.ico"

            # Try multiple paths
            possible_paths = [
                Path(__file__).parent.parent.parent / "Assets" / icon_name,
                Path("Assets") / icon_name,
                Path(sys._MEIPASS) / "Assets" /
                icon_name if hasattr(sys, '_MEIPASS') else None
            ]

            icon_image = None
            for icon_path in possible_paths:
                if icon_path and icon_path.exists():
                    try:
                        icon_image = Image.open(icon_path)
                        print(f"✅ Loaded system tray icon from: {icon_path}")
                        break
                    except Exception as e:
                        print(f"⚠️ Failed to load icon from {icon_path}: {e}")
                        continue

            if not icon_image:
                # Create a simple default icon if file not found
                print("⚠️ Using default icon - blackp2p.ico not found")
                icon_image = Image.new('RGB', (64, 64), color='blue')

            # Create system tray icon with compact mode as default action
            menu = pystray.Menu(
                item('Open in Compact Mode',
                     self._show_window_compact, default=True),
                item('Show in Normal Mode', self._show_window),
                item('Hide', self._hide_window),
                pystray.Menu.SEPARATOR,
                item('Exit', self._quit_app)
            )

            self.tray_icon = pystray.Icon(
                "SyncStream",
                icon_image,
                "SyncStream P2P",
                menu
            )

            # Start tray icon in background thread
            import threading
            tray_thread = threading.Thread(
                target=self.tray_icon.run, daemon=True)
            tray_thread.start()

            # Override window close button to minimize to tray
            self.protocol("WM_DELETE_WINDOW", self._on_closing)

            print("✅ System tray icon initialized")
        except Exception as e:
            print(f"⚠️  Failed to setup system tray: {e}")
            self.tray_icon = None

    def _show_window(self, icon=None, item=None):
        """Show the main window in normal mode"""
        def show():
            # Switch to normal mode first (before showing window)
            if self.is_compact_mode:
                self._switch_to_normal_mode()

            # Restore normal window size
            width = self.config_manager.settings.window_width or 1200
            height = self.config_manager.settings.window_height or 800
            self.geometry(f"{width}x{height}")

            # Show the window
            self.deiconify()

            # Ensure window is raised and focused
            self.lift()
            self.focus_force()
        self.after(0, show)

    def _show_window_compact(self, icon=None, item=None):
        """Show the main window in compact mode"""
        def show():
            # Switch to compact mode first (before showing window)
            if not self.is_compact_mode:
                self._switch_to_compact_mode()

            # Set compact window size (same as size button: 380x295)
            self.geometry("380x295")

            # Show the window
            self.deiconify()

            # Ensure window is raised and focused
            self.lift()
            self.focus_force()
        self.after(0, show)

    def _hide_window(self, icon=None, item=None):
        """Hide the main window to system tray"""
        self.after(0, lambda: self.withdraw())

    def _on_closing(self):
        """Handle window close button - minimize to tray instead of exit"""
        if self.tray_icon:
            self._hide_window()
            if self.toaster:
                self._show_notification(
                    "SyncStream",
                    "App minimized to system tray"
                )
        else:
            self._quit_app()

    def _quit_app(self, icon=None, item=None):
        """Quit the application"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.network_manager._running = False
        self.quit()

    def _handle_drop(self, event):
        """Handle file drop with upload progress"""
        try:
            self.is_dragging = False

            # Restore colors
            if hasattr(self, 'content_frame_original_fg'):
                self.content_frame.configure(
                    fg_color=self.content_frame_original_fg)

            # Restore drop label
            if hasattr(self, 'drop_label'):
                self.drop_label.configure(
                    text="Drag & Drop Files Here",
                    font=("Arial", 16)
                )

            # Get files
            files = self.tk.splitlist(event.data)
            added_files = []

            for file_path in files:
                if Path(file_path).is_file() and file_path not in self.shared_files:
                    self.shared_files.append(file_path)
                    added_files.append(file_path)
                    print(f"📁 Added to gallery: {Path(file_path).name}")

            # Refresh gallery
            self._load_file_gallery()

            # Show gallery if hidden
            if not self.gallery_visible:
                self._toggle_gallery()

            # If connected, automatically send the dropped files
            if self.is_connected and added_files:
                self._show_notification(
                    "Files Added",
                    f"Added {len(added_files)} file(s) to gallery. Click to send."
                )

                # Show upload progress overlay
                self._show_upload_overlay(added_files)
            else:
                # Just notify files were added
                self._show_notification(
                    "Files Added",
                    f"Added {len(added_files)} file(s) to gallery"
                )

        except Exception as e:
            print(f"⚠️  Failed to handle drop: {e}")

    def _show_upload_overlay(self, files):
        """Show an upload progress overlay for dropped files"""
        try:
            # Create overlay frame
            overlay = ctk.CTkFrame(
                self,
                fg_color=("gray90", "gray10"),
                corner_radius=10
            )
            overlay.place(relx=0.5, rely=0.5, anchor="center",
                          relwidth=0.6, relheight=0.3)

            # Title
            title_label = ctk.CTkLabel(
                overlay,
                text="📤 Files Ready to Send",
                font=("Arial", 18, "bold")
            )
            title_label.pack(pady=(20, 10))

            # File list
            file_list = ctk.CTkTextbox(
                overlay,
                height=80,
                font=("Arial", 12)
            )
            file_list.pack(pady=10, padx=20, fill="both", expand=True)

            for fp in files:
                file_list.insert("end", f"• {Path(fp).name}\n")
            file_list.configure(state="disabled")

            # Buttons frame
            btn_frame = ctk.CTkFrame(overlay, fg_color="transparent")
            btn_frame.pack(pady=10)

            # Send button
            def send_all():
                overlay.destroy()
                for fp in files:
                    self._send_file(fp)

            send_btn = ctk.CTkButton(
                btn_frame,
                text="Send All",
                command=send_all,
                width=120,
                font=("Arial", 13, "bold"),
                fg_color="green",
                hover_color="darkgreen"
            )
            send_btn.pack(side="left", padx=5)

            # Cancel button
            cancel_btn = ctk.CTkButton(
                btn_frame,
                text="Cancel",
                command=overlay.destroy,
                width=120,
                font=("Arial", 13),
                fg_color="gray",
                hover_color="darkgray"
            )
            cancel_btn.pack(side="left", padx=5)

            # Auto-dismiss after 10 seconds
            self.after(10000, lambda: overlay.destroy()
                       if overlay.winfo_exists() else None)

        except Exception as e:
            print(f"⚠️  Failed to show upload overlay: {e}")

    def _browse_files(self):
        """Browse for files to share"""
        from tkinter import filedialog
        files = filedialog.askopenfilenames(title="Select Files to Share")
        if files:
            for file_path in files:
                if file_path not in self.shared_files:
                    self.shared_files.append(file_path)
            self._load_file_gallery()
            if not self.gallery_visible:
                self._toggle_gallery()

    def _toggle_gallery(self):
        """Toggle file gallery visibility"""
        if self.gallery_visible:
            # Hide gallery
            self.gallery_frame.grid_forget()
            self.drop_icon.grid()
            self.drop_label.grid()
            self.browse_btn.grid()
            self.gallery_btn.configure(text="Show Gallery")
            self.gallery_visible = False

            # Hide search and filter
            self.search_entry.grid_forget()
            self.filter_btn.grid_forget()
        else:
            # Hide statistics if showing
            if self.statistics_visible:
                self.statistics_frame.grid_forget()
                self.statistics_visible = False

            # Hide settings if showing
            if self.settings_visible:
                self.settings_frame.grid_forget()
                self.settings_visible = False

            # Hide profile manager if showing
            if self.profile_manager_visible:
                self.profile_manager_frame.grid_forget()
                self.profile_manager_visible = False

            # Show gallery
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()
            self.gallery_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.gallery_btn.configure(text="Hide Gallery")
            self.gallery_visible = True

            # Reload gallery to ensure correct layout for current mode
            self._load_file_gallery()

            # Show search and filter only if not in compact mode or if window is wide enough
            window_width = self.winfo_width()
            if not self.is_compact_mode and window_width > 600:
                self.search_entry.grid(row=0, column=1, padx=8, sticky="w")
                self.filter_btn.grid(row=0, column=2, padx=(0, 8), sticky="w")

    def _cycle_filter(self):
        """Cycle through file filters"""
        filters = ["All", "Images", "Documents", "Videos", "Archives"]
        current_index = filters.index(self.current_filter)
        next_index = (current_index + 1) % len(filters)
        self.current_filter = filters[next_index]

        # Update button text
        self.filter_btn.configure(text=f"Filter: {self.current_filter}")

        # Reload gallery with filter
        self._load_file_gallery()

    def _filter_gallery(self):
        """Filter gallery based on search text"""
        if not self.gallery_visible:
            return

        search_text = self.search_var.get().lower()
        self._load_file_gallery(search_filter=search_text)

    def _get_file_category(self, file_path):
        """Get file category based on extension"""
        ext = Path(file_path).suffix.lower()

        image_exts = ['.jpg', '.jpeg', '.png',
                      '.gif', '.bmp', '.svg', '.webp', '.ico']
        doc_exts = ['.txt', '.pdf', '.doc', '.docx', '.xls',
                    '.xlsx', '.ppt', '.pptx', '.odt', '.rtf']
        video_exts = ['.mp4', '.avi', '.mkv',
                      '.mov', '.wmv', '.flv', '.webm', '.m4v']
        archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']

        if ext in image_exts:
            return "Images"
        elif ext in doc_exts:
            return "Documents"
        elif ext in video_exts:
            return "Videos"
        elif ext in archive_exts:
            return "Archives"
        else:
            return "All"

    def _load_file_gallery(self, search_filter=""):
        """Load files into gallery"""
        # Debug: Log current mode and expected layout
        mode_str = "COMPACT" if self.is_compact_mode else "NORMAL"
        columns = 2 if self.is_compact_mode else 5
        print(
            f"🔄 Loading gallery in {mode_str} mode with {columns} columns per row")

        # Clear existing items
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Clear file widgets tracking
        self.file_widgets.clear()

        # Get files from shared_files list
        files = self.shared_files

        # Apply category filter if not "All"
        if self.current_filter != "All":
            files = [f for f in files if self._get_file_category(
                f) == self.current_filter]

        # Apply search filter if provided
        if search_filter:
            files = [f for f in files if search_filter in Path(f).name.lower()]

        if not files:
            # Use appropriate columnspan based on mode
            max_columns = 2 if self.is_compact_mode else 5
            no_files_label = ctk.CTkLabel(
                self.gallery_frame,
                text="No files found" if (
                    search_filter or self.current_filter != "All") else "No files shared yet",
                font=("Arial", 14),
                text_color="gray"
            )
            no_files_label.grid(
                row=0, column=0, columnspan=max_columns, pady=20)
            return

        # Display files in grid
        for idx, file_path in enumerate(files):
            # Adjust grid layout and sizes based on compact mode
            if self.is_compact_mode:
                columns_per_row = 2
                row = idx // columns_per_row
                col = idx % columns_per_row
                card_width = 230  # 20% bigger than 192
                card_height = 259  # 20% bigger than 216
                icon_width = 72  # 20% bigger thumbnails
                icon_height = 58  # 20% bigger thumbnails (rounded from 57.6)
                icon_font_size = 46  # 20% bigger
                name_font_size = 12
                button_width = 101  # 20% bigger (rounded from 100.8)
                button_height = 36
                button_font_size = 14
                delete_btn_size = 24
                delete_btn_x_offset = -2
                delete_btn_y_offset = 14
            else:
                columns_per_row = 5
                row = idx // columns_per_row
                col = idx % columns_per_row
                card_width = 160
                card_height = 160
                icon_width = 120
                icon_height = 90
                icon_font_size = 40
                name_font_size = 10
                button_width = self.btn_width
                button_height = 34
                button_font_size = 14
                delete_btn_size = 28
                delete_btn_width = 30  # 50% smaller (60 -> 30)
                delete_btn_x_offset = -2  # Same as compact mode
                delete_btn_y_offset = 18

            file_name = Path(file_path).name

            # Clean container with subtler styling - remove heavy border and use a minimal look
            file_frame = ctk.CTkFrame(
                self.gallery_frame,
                corner_radius=10,
                border_width=0,
                fg_color="transparent"
            )
            file_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            # Fix size so all items have equal dimensions
            try:
                file_frame.configure(width=card_width, height=card_height)
                file_frame.grid_propagate(False)
            except Exception:
                pass

            # Generate thumbnail or use icon (pass correct size based on mode)
            thumbnail = self._get_file_thumbnail(
                file_path, size=(icon_width, icon_height))

            # Icon container - fixed size so thumbnails and emojis align
            icon_container = ctk.CTkFrame(
                file_frame, fg_color="transparent", width=icon_width, height=icon_height)
            icon_container.pack(pady=(10, 5))
            try:
                icon_container.pack_propagate(False)
            except Exception:
                pass

            if thumbnail:
                # Use thumbnail image with transparent background
                file_icon = ctk.CTkLabel(
                    icon_container,
                    image=thumbnail,
                    text="",
                    fg_color="transparent"
                )
                file_icon.image = thumbnail  # Keep reference
            else:
                # Use emoji icon based on file type (scale up to container)
                icon_emoji = self._get_file_icon(file_path)
                file_icon = ctk.CTkLabel(
                    icon_container,
                    text=icon_emoji,
                    font=("Arial", icon_font_size),
                    fg_color="transparent"
                )

            file_icon.pack(expand=True)

            # File name
            name_label = ctk.CTkLabel(
                file_frame,
                text=file_name if len(
                    file_name) < 20 else file_name[:17] + "...",
                font=("Arial", name_font_size, "bold")
            )
            name_label.pack(pady=2)

            # Progress bar (initially hidden)
            progress_bar = ctk.CTkProgressBar(
                file_frame,
                width=icon_width,
                height=10,
                mode="determinate"
            )
            progress_bar.set(0)
            # Don't pack it yet - only show during transfer

            # Status label for transfer info
            status_label = ctk.CTkLabel(
                file_frame,
                text="",
                font=("Arial", 9),
                text_color="gray"
            )
            # Don't pack it yet

            # Button container - centered
            btn_container = ctk.CTkFrame(file_frame, fg_color="transparent")
            btn_container.pack(pady=8, padx=5)

            # Open button - lighter green with no icon, bolder text
            open_btn = ctk.CTkButton(
                btn_container,
                text="Open",
                width=button_width,
                height=button_height,
                command=lambda fp=file_path: self._open_file(fp),
                font=("Arial", button_font_size, "bold"),
                fg_color="#3e8a50",  # Lighter green
                hover_color="#13491F"  # Medium green
            )
            open_btn.pack(side="left", padx=3)

            # Send button (only if connected)
            if self.is_connected:
                send_btn = ctk.CTkButton(
                    btn_container,
                    text="📤",
                    width=button_width,
                    height=button_height,
                    command=lambda fp=file_path: self._send_file(fp),
                    font=self.btn_font,
                    fg_color="#28a745",  # Lighter green
                    hover_color="#218838"  # Medium green
                )
                send_btn.pack(side="left", padx=3)

            # Right-click context menu
            file_frame.bind("<Button-3>", lambda e,
                            fp=file_path: self._show_file_context_menu(e, fp))
            file_icon.bind("<Button-3>", lambda e,
                           fp=file_path: self._show_file_context_menu(e, fp))
            name_label.bind("<Button-3>", lambda e,
                            fp=file_path: self._show_file_context_menu(e, fp))

            # Store widget references for progress updates
            self.file_widgets[file_path] = {
                "frame": file_frame,
                "icon": file_icon,
                "name": name_label,
                "progress": progress_bar,
                "status": status_label,
                "btn_container": btn_container,
            }

    def _get_file_thumbnail(self, file_path, size=(80, 80)):
        """Generate thumbnail for image files with aspect ratio preserved"""
        try:
            path = Path(file_path)
            if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico']:
                # Use file_manager to generate thumbnail with requested size
                thumb_path = self.file_manager.generate_thumbnail(
                    str(file_path), size=size)
                if thumb_path and Path(thumb_path).exists():
                    # Load thumbnail as CTkImage
                    pil_image = Image.open(thumb_path)

                    # Calculate aspect ratio and adjust size to fit within bounds
                    img_width, img_height = pil_image.size
                    max_width, max_height = size

                    # Calculate scaling factor to fit within bounds while preserving aspect ratio
                    width_ratio = max_width / img_width
                    height_ratio = max_height / img_height
                    scale_factor = min(width_ratio, height_ratio)

                    # Calculate final size maintaining aspect ratio
                    final_width = int(img_width * scale_factor)
                    final_height = int(img_height * scale_factor)

                    ctk_image = ctk.CTkImage(
                        light_image=pil_image,
                        dark_image=pil_image,
                        size=(final_width, final_height)
                    )
                    return ctk_image
        except Exception as e:
            print(f"⚠️  Failed to generate thumbnail: {e}")
        return None

    def _get_file_icon(self, file_path):
        """Get emoji icon based on file type"""
        path = Path(file_path)
        ext = path.suffix.lower()

        # Image files
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico']:
            return "🖼️"
        # Video files
        elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
            return "🎬"
        # Audio files
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']:
            return "🎵"
        # Document files
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            return "📄"
        # Spreadsheet files
        elif ext in ['.xls', '.xlsx', '.csv']:
            return "📊"
        # Archive files
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return "📦"
        # Code files
        elif ext in ['.py', '.js', '.java', '.cpp', '.c', '.html', '.css']:
            return "💻"
        else:
            return "📄"

    def _open_file(self, file_path):
        """Open file with default system application"""
        try:
            import os
            import platform

            path = Path(file_path)
            if not path.exists():
                print(f"⚠️  File not found: {file_path}")
                self._show_notification(
                    "Error", f"File not found: {path.name}")
                return

            # Open file based on OS
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{file_path}"')

            print(f"📂 Opened file: {path.name}")
        except Exception as e:
            print(f"⚠️  Failed to open file: {e}")
            self._show_notification("Error", f"Failed to open file: {str(e)}")

    def _show_file_context_menu(self, event, file_path):
        """Show right-click context menu for file"""
        try:
            import tkinter as tk
            from tkinter import Menu

            path = Path(file_path)

            # Create context menu
            menu = Menu(self, tearoff=0)

            # Get file info
            file_info = self.file_manager.get_file_info(file_path)

            # Add menu items
            menu.add_command(
                label=f"📂 Open", command=lambda: self._open_file(file_path))
            menu.add_command(label=f"📁 Open Location",
                             command=lambda: self._open_file_location(file_path))
            menu.add_separator()

            if self.is_connected:
                menu.add_command(label=f"📤 Send to Peer",
                                 command=lambda: self._send_file(file_path))
                menu.add_separator()

            # File details submenu
            if file_info:
                details_label = f"📊 File Info:\n"
                details_label += f"  Name: {file_info['name']}\n"
                details_label += f"  Size: {file_info['size_mb']} MB\n"
                details_label += f"  Type: {file_info['extension']}\n"
                details_label += f"  Modified: {file_info['modified'][:10]}"

                menu.add_command(label="ℹ️ Show Details", command=lambda: self._show_file_details(
                    file_path, file_info))

            menu.add_separator()
            menu.add_command(label="Remove",
                             command=lambda: self._remove_file(file_path))

            # Display menu at cursor position
            menu.post(event.x_root, event.y_root)

        except Exception as e:
            print(f"⚠️  Failed to show context menu: {e}")

    def _open_file_location(self, file_path):
        """Open file location in file explorer"""
        try:
            import os
            import platform

            path = Path(file_path)
            if not path.exists():
                print(f"⚠️  File not found: {file_path}")
                return

            parent_dir = path.parent

            # Open folder based on OS
            if platform.system() == 'Windows':
                os.startfile(parent_dir)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{parent_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{parent_dir}"')

            print(f"📁 Opened folder: {parent_dir}")
        except Exception as e:
            print(f"⚠️  Failed to open location: {e}")

    def _show_file_details(self, file_path, file_info):
        """Show detailed file information dialog"""
        try:
            # Create dialog window
            dialog = ctk.CTkToplevel(self)
            dialog.title("File Details")
            dialog.geometry("480x360")  # 20% bigger than 400x300
            dialog.transient(self)
            dialog.grab_set()

            # Use the standard app icon for dialogs as well
            try:
                icon_path = self.assets_path / "blackp2p.ico"
                if icon_path.exists():
                    dialog.iconbitmap(str(icon_path))
            except Exception:
                pass

            # Title
            title = ctk.CTkLabel(
                dialog,
                text="File Information",
                font=("Arial", 18, "bold"),
                text_color=("gray10", "gray90")
            )
            title.pack(pady=20)

            # Details frame with explicit colors
            details_frame = ctk.CTkFrame(
                dialog,
                fg_color=("gray92", "gray14")
            )
            details_frame.pack(pady=10, padx=20, fill="both", expand=True)

            # File details (no emoji icons)
            details = [
                ("Name:", file_info['name']),
                ("Size:",
                 f"{file_info['size_mb']} MB ({file_info['size']:,} bytes)"),
                ("Type:", file_info['extension'] or "Unknown"),
                ("Modified:", file_info['modified']),
                ("Path:", file_info['path']),
                ("Is Image:", "Yes" if file_info['is_image'] else "No")
            ]

            for label, value in details:
                row = ctk.CTkFrame(details_frame, fg_color="transparent")
                row.pack(pady=5, padx=10, fill="x")

                label_widget = ctk.CTkLabel(
                    row,
                    text=label,
                    font=("Arial", 12, "bold"),
                    anchor="w",
                    width=100,
                    text_color=("gray10", "gray90")
                )
                label_widget.pack(side="left")

                value_widget = ctk.CTkLabel(
                    row,
                    text=str(value),
                    font=("Arial", 11),
                    anchor="w",
                    text_color=("gray20", "gray80")
                )
                value_widget.pack(side="left", fill="x", expand=True)

            # (Removed explicit Close button - user can close dialog via window chrome)

        except Exception as e:
            print(f"⚠️  Failed to show file details: {e}")

    def _toggle_statistics(self):
        """Toggle statistics page visibility"""
        if self.statistics_visible:
            # Hide statistics
            self.statistics_frame.grid_forget()
            self.drop_icon.grid()
            self.drop_label.grid()
            self.browse_btn.grid()
            self.statistics_visible = False
        else:
            # Hide gallery if showing
            if self.gallery_visible:
                self.gallery_frame.grid_forget()
                self.gallery_visible = False
                self.gallery_btn.configure(text="Show Gallery")
                # Hide search and filter
                self.search_entry.grid_forget()
                self.filter_btn.grid_forget()

            # Hide settings if showing
            if self.settings_visible:
                self.settings_frame.grid_forget()
                self.settings_visible = False

            # Hide profile manager if showing
            if self.profile_manager_visible:
                self.profile_manager_frame.grid_forget()
                self.profile_manager_visible = False

            # Hide drop zone
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()

            # Show statistics
            self.statistics_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.statistics_visible = True

            # Load statistics content
            self._load_statistics_page()

    def _open_settings(self):
        """Toggle settings page visibility"""
        if self.settings_visible:
            # Hide settings
            self.settings_frame.grid_forget()
            self.drop_icon.grid()
            self.drop_label.grid()
            self.browse_btn.grid()
            self.settings_visible = False
        else:
            # Hide gallery if showing
            if self.gallery_visible:
                self.gallery_frame.grid_forget()
                self.gallery_visible = False
                self.gallery_btn.configure(text="Show Gallery")
                # Hide search and filter
                self.search_entry.grid_forget()
                self.filter_btn.grid_forget()

            # Hide statistics if showing
            if self.statistics_visible:
                self.statistics_frame.grid_forget()
                self.statistics_visible = False

            # Hide profile manager if showing
            if self.profile_manager_visible:
                self.profile_manager_frame.grid_forget()
                self.profile_manager_visible = False

            # Hide drop zone
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()

            # Show settings
            self.settings_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.settings_visible = True

            # Load settings content
            self._load_settings_page()

    def _load_settings_page(self):
        """Load and display settings in the main content area"""
        try:
            # Clear existing content
            for widget in self.settings_frame.winfo_children():
                widget.destroy()

            # Main container with padding
            container = ctk.CTkFrame(
                self.settings_frame, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=20, pady=20)

            # Title
            title_label = ctk.CTkLabel(
                container,
                text="Settings",
                font=("Arial", 32, "bold")
            )
            title_label.pack(pady=(0, 30))

            # Grid container - 2 columns, 2 rows
            grid_container = ctk.CTkFrame(container, fg_color="transparent")
            grid_container.pack(fill="both", expand=True)

            # Configure grid weights
            grid_container.grid_columnconfigure(0, weight=1)  # Left column
            grid_container.grid_columnconfigure(1, weight=1)  # Right column
            grid_container.grid_rowconfigure(0, weight=1)     # Top row
            grid_container.grid_rowconfigure(1, weight=1)     # Bottom row

            # ============================================================
            # TOP LEFT: Version Info (Row 0, Column 0)
            # ============================================================
            version_container = ctk.CTkFrame(
                grid_container, fg_color="transparent")
            version_container.grid(
                row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

            # App Version
            version_label = ctk.CTkLabel(
                version_container,
                text="Current Version:",
                font=("Arial", 16, "bold")
            )
            version_label.pack(anchor="w", pady=(0, 8))

            version_value = ctk.CTkLabel(
                version_container,
                text=f"v{self.version_manager.get_current_version()}",
                font=("Arial", 24),
                text_color=("green", "lightgreen")
            )
            version_value.pack(anchor="w", pady=(0, 20))

            # Repository
            repo_label = ctk.CTkLabel(
                version_container,
                text="Repository:",
                font=("Arial", 16, "bold")
            )
            repo_label.pack(anchor="w", pady=(0, 8))

            repo_link = ctk.CTkButton(
                version_container,
                text=self.version_manager.get_repo_url(),
                font=("Arial", 13, "underline"),
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda: webbrowser.open(
                    self.version_manager.get_repo_url()),
                anchor="w"
            )
            repo_link.pack(anchor="w", pady=(0, 20))

            # Startup Settings
            startup_label = ctk.CTkLabel(
                version_container,
                text="Startup:",
                font=("Arial", 16, "bold")
            )
            startup_label.pack(anchor="w", pady=(0, 8))

            # Run on Windows startup checkbox
            self.startup_checkbox = ctk.CTkCheckBox(
                version_container,
                text="Run SyncStream when Windows starts",
                font=("Arial", 14),
                command=self._toggle_startup_setting
            )
            self.startup_checkbox.pack(anchor="w", pady=(0, 10))

            # Set initial state from settings
            if self.config_manager.settings.run_on_startup:
                self.startup_checkbox.select()
            else:
                self.startup_checkbox.deselect()

            # ============================================================
            # BOTTOM LEFT: Update Status (Row 1, Column 0)
            # ============================================================
            update_container = ctk.CTkFrame(
                grid_container, fg_color="transparent")
            update_container.grid(
                row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))

            # Status indicator
            status_header = ctk.CTkFrame(
                update_container, fg_color="transparent")
            status_header.pack(fill="x", pady=(0, 15))

            status_label = ctk.CTkLabel(
                status_header,
                text="Update Status:",
                font=("Arial", 16, "bold")
            )
            status_label.pack(side="left", padx=(0, 15))

            self.status_indicator = ctk.CTkLabel(
                status_header,
                text="⟳ Checking...",
                font=("Arial", 16),
                text_color=("gray50", "gray50")
            )
            self.status_indicator.pack(side="left")

            # Latest version info
            self.latest_version_label = ctk.CTkLabel(
                update_container,
                text="",
                font=("Arial", 13),
                text_color=("gray50", "gray70")
            )
            self.latest_version_label.pack(anchor="w", pady=(0, 15))

            # Update button
            self.update_btn = ctk.CTkButton(
                update_container,
                text="Check for Updates",
                font=("Arial", 16, "bold"),
                height=45,
                command=self._check_updates,
                state="disabled"
            )
            self.update_btn.pack(fill="x", pady=(0, 15))

            # Progress section (hidden initially)
            self.progress_container = ctk.CTkFrame(
                update_container, fg_color="transparent")

            self.progress_label = ctk.CTkLabel(
                self.progress_container,
                text="",
                font=("Arial", 13)
            )
            self.progress_label.pack(anchor="w", pady=(0, 8))

            self.progress_bar = ctk.CTkProgressBar(
                self.progress_container, height=8)
            self.progress_bar.pack(fill="x")
            self.progress_bar.set(0)

            # ============================================================
            # RIGHT SIDE: Release Notes (Row 0-1, Column 1) - Spans both rows
            # ============================================================
            notes_container = ctk.CTkFrame(
                grid_container, fg_color="transparent")
            notes_container.grid(row=0, column=1, rowspan=2,
                                 sticky="nsew", padx=(10, 0))

            # Header
            notes_label = ctk.CTkLabel(
                notes_container,
                text="Release Notes",
                font=("Arial", 16, "bold")
            )
            notes_label.pack(anchor="w", pady=(0, 10))

            # Scrollable text area for release notes
            self.notes_text = ctk.CTkTextbox(
                notes_container,
                font=("Arial", 12),
                wrap="word",
                fg_color="transparent"
            )
            self.notes_text.pack(fill="both", expand=True)
            self.notes_text.insert("1.0", "Loading release information...")
            self.notes_text.configure(state="disabled")

            # Start checking for updates
            self._check_updates()

        except Exception as e:
            print(f"⚠️  Failed to load settings page: {e}")
            import traceback
            traceback.print_exc()

    def _check_updates(self, force=False):
        """Check for available updates

        Args:
            force: If True, bypass cache and force a fresh check
        """
        if hasattr(self, 'status_indicator'):
            self.status_indicator.configure(
                text="⟳ Checking...", text_color=("gray50", "gray50"))
        if hasattr(self, 'update_btn'):
            self.update_btn.configure(state="disabled", text="Checking...")

        def callback(success, version, error):
            # Update UI on main thread
            self.after(0, lambda: self._update_check_complete(
                success, version, error))

        self.version_manager.check_for_updates(callback, force=force)

    def _update_check_complete(self, success, version, error):
        """Handle update check completion"""
        if not hasattr(self, 'status_indicator'):
            return  # Settings page was closed

        if success:
            if self.version_manager.update_available:
                # Update available
                self.status_indicator.configure(
                    text="⚠️ Outdated",
                    text_color=("orange", "orange")
                )
                self.latest_version_label.configure(
                    text=f"Latest version: v{version}"
                )
                self.update_btn.configure(
                    state="normal",
                    text="Install Update",
                    command=self._install_update
                )
            else:
                # Up to date
                self.status_indicator.configure(
                    text="✓ Synced",
                    text_color=("green", "lightgreen")
                )
                self.latest_version_label.configure(
                    text="You're running the latest version"
                )
                self.update_btn.configure(
                    state="normal",
                    text="Check for Updates"
                )

            # Load release notes
            self._load_release_notes()
        else:
            # Error
            self.status_indicator.configure(
                text="✗ Error",
                text_color=("red", "lightcoral")
            )
            self.latest_version_label.configure(
                text=error or "Failed to check for updates"
            )
            self.update_btn.configure(
                state="normal",
                text="Retry",
                command=lambda: self._check_updates(force=True)
            )

    def _load_release_notes(self):
        """Load release notes from GitHub"""
        if not hasattr(self, 'notes_text'):
            return  # Settings page was closed

        try:
            release_info = self.version_manager.latest_release_info
            if release_info:
                notes = release_info.get("body", "No release notes available.")
                release_name = release_info.get("name", "")
                tag_name = release_info.get("tag_name", "")

                self.notes_text.configure(state="normal")
                self.notes_text.delete("1.0", "end")

                if release_name:
                    self.notes_text.insert("end", f"{release_name}\n\n")
                elif tag_name:
                    self.notes_text.insert("end", f"{tag_name}\n\n")

                self.notes_text.insert("end", notes)
                self.notes_text.configure(state="disabled")
            else:
                self.notes_text.configure(state="normal")
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert(
                    "1.0", "No release information available.")
                self.notes_text.configure(state="disabled")
        except Exception as e:
            self.notes_text.configure(state="normal")
            self.notes_text.delete("1.0", "end")
            self.notes_text.insert(
                "1.0", f"Failed to load release notes: {str(e)}")
            self.notes_text.configure(state="disabled")

    def _install_update(self):
        """Install the available update"""
        from tkinter import messagebox

        # Confirm with user
        response = messagebox.askyesno(
            "Install Update",
            f"Install update to v{self.version_manager.latest_version}?\n\n"
            "Your profiles and settings will be preserved.\n"
            "The application will need to restart after the update.",
            parent=self
        )

        if not response:
            return

        # Show progress
        if hasattr(self, 'progress_container'):
            self.progress_container.pack(fill="x", pady=(10, 0))
        if hasattr(self, 'update_btn'):
            self.update_btn.configure(state="disabled")

        def progress_callback(stage, message, percent):
            self.after(0, lambda: self._update_progress(message, percent))

        def completion_callback(success, message):
            self.after(0, lambda: self._update_complete(success, message))

        self.version_manager.download_and_install_update(
            progress_callback,
            completion_callback
        )

    def _update_progress(self, message, percent):
        """Update progress display"""
        if hasattr(self, 'progress_label'):
            self.progress_label.configure(text=message)
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(percent / 100.0)

    def _update_complete(self, success, message):
        """Handle update completion"""
        from tkinter import messagebox

        if success:
            messagebox.showinfo(
                "Update Complete",
                message,
                parent=self
            )

            # Prompt to restart
            restart = messagebox.askyesno(
                "Restart Required",
                "Would you like to restart SyncStream now?",
                parent=self
            )
            if restart:
                self.quit()
        else:
            messagebox.showerror(
                "Update Failed",
                message,
                parent=self
            )
            if hasattr(self, 'update_btn'):
                self.update_btn.configure(state="normal")
            if hasattr(self, 'progress_container'):
                self.progress_container.pack_forget()

    def _toggle_startup_setting(self):
        """Toggle the run on startup setting"""
        from tkinter import messagebox

        try:
            # Get the checkbox state
            enabled = self.startup_checkbox.get() == 1

            # Update the setting
            self.config_manager.set_run_on_startup(enabled)

            # Show confirmation
            if enabled:
                self._show_notification(
                    "Startup Enabled",
                    "SyncStream will now start when Windows starts"
                )
            else:
                self._show_notification(
                    "Startup Disabled",
                    "SyncStream will no longer start automatically"
                )

        except Exception as e:
            # Show error and revert checkbox
            messagebox.showerror(
                "Error",
                f"Failed to update startup setting: {str(e)}\n\n"
                "Make sure you have permission to modify Windows startup programs.",
                parent=self
            )
            # Revert checkbox to previous state
            if enabled:
                self.startup_checkbox.deselect()
            else:
                self.startup_checkbox.select()

    def _open_profile_manager(self):
        """Toggle profile manager page visibility"""
        if self.profile_manager_visible:
            # Hide profile manager
            self.profile_manager_frame.grid_forget()
            self.drop_icon.grid()
            self.drop_label.grid()
            self.browse_btn.grid()
            self.profile_manager_visible = False
        else:
            # Hide gallery if showing
            if self.gallery_visible:
                self.gallery_frame.grid_forget()
                self.gallery_visible = False
                self.gallery_btn.configure(text="Show Gallery")
                # Hide search and filter
                self.search_entry.grid_forget()
                self.filter_btn.grid_forget()

            # Hide statistics if showing
            if self.statistics_visible:
                self.statistics_frame.grid_forget()
                self.statistics_visible = False

            # Hide settings if showing
            if self.settings_visible:
                self.settings_frame.grid_forget()
                self.settings_visible = False

            # Hide drop zone
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()

            # Show profile manager
            self.profile_manager_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.profile_manager_visible = True

            # Load profile manager content
            self._load_profile_manager_page()

    def _load_profile_manager_page(self):
        """Load and display profile manager in the main content area"""
        try:
            # Clear existing content
            for widget in self.profile_manager_frame.winfo_children():
                widget.destroy()

            # Get theme colors
            frame_colors = self.theme_manager.get_frame_colors()
            text_color = self.theme_manager.current_theme.text_primary

            # Set proper background color based on theme
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                bg_color = '#ffffff'
            else:
                bg_color = self.theme_manager.current_theme.bg_primary

            # Update profile manager frame background
            self.profile_manager_frame.configure(fg_color=bg_color)

            # Main container with padding
            container = ctk.CTkFrame(
                self.profile_manager_frame, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=40, pady=(10, 40))

            # Title
            title_label = ctk.CTkLabel(
                container,
                text="Manage Connection Profiles",
                font=("Segoe UI", 32, "bold"),
                text_color=text_color
            )
            title_label.pack(pady=(0, 10))

            # Subtitle
            subtitle = ctk.CTkLabel(
                container,
                text="Add other people's profiles to connect to their devices (max 2)",
                font=("Segoe UI", 14),
                text_color=text_color
            )
            subtitle.pack(pady=(0, 30))

            # Get current peer profiles (not including my_profile)
            profiles = self.config_manager.get_profiles()
            print(
                f"🔍 Debug - Profiles found: {len(profiles) if profiles else 0}")
            if profiles:
                for p in profiles:
                    print(f"   - {p.name}: {p.ip}")

            # Add profile button (only if less than 2 profiles) - Show FIRST
            if len(profiles) < 2:
                # Get card background color based on theme
                is_dark = self.theme_manager.current_theme_name == "dark"
                card_bg = "#2d2d2d" if is_dark else "#f0f0f0"

                add_frame = ctk.CTkFrame(
                    container,
                    fg_color=card_bg,
                    corner_radius=12
                )
                add_frame.pack(fill="x", pady=(0, 20))

                # Add new profile section
                add_title = ctk.CTkLabel(
                    add_frame,
                    text="Add New Profile",
                    font=("Segoe UI", 20, "bold"),
                    text_color=text_color
                )
                add_title.pack(pady=(20, 15), padx=20)

                # Name input
                name_label = ctk.CTkLabel(
                    add_frame,
                    text="Profile Name:",
                    font=("Segoe UI", 14),
                    text_color=text_color
                )
                name_label.pack(pady=(0, 5), padx=20, anchor="w")

                self.new_profile_name_entry = ctk.CTkEntry(
                    add_frame,
                    font=("Segoe UI", 14),
                    height=40,
                    placeholder_text="e.g., Friend's PC"
                )
                self.new_profile_name_entry.pack(
                    pady=(0, 15), padx=20, fill="x")

                # Address input
                address_label = ctk.CTkLabel(
                    add_frame,
                    text="Tailscale IP Address:",
                    font=("Segoe UI", 14),
                    text_color=text_color
                )
                address_label.pack(pady=(0, 5), padx=20, anchor="w")

                self.new_profile_address_entry = ctk.CTkEntry(
                    add_frame,
                    font=("Segoe UI", 14),
                    height=40,
                    placeholder_text="e.g., 100.64.0.2"
                )
                self.new_profile_address_entry.pack(
                    pady=(0, 15), padx=20, fill="x")

                # Error label
                self.profile_error_label = ctk.CTkLabel(
                    add_frame,
                    text="",
                    font=("Segoe UI", 12),
                    text_color="#ef4444"
                )
                self.profile_error_label.pack(pady=(0, 10), padx=20)

                # Buttons container
                buttons_container = ctk.CTkFrame(
                    add_frame, fg_color="transparent")
                buttons_container.pack(pady=(0, 20), padx=20, fill="x")
                buttons_container.grid_columnconfigure(0, weight=1)
                buttons_container.grid_columnconfigure(1, weight=1)

                # Add button with icon
                addprofile_icon_path = Path(
                    __file__).parent.parent.parent / "Assets" / "addprofile.png"
                if addprofile_icon_path.exists():
                    addprofile_icon = ctk.CTkImage(
                        light_image=Image.open(addprofile_icon_path),
                        dark_image=Image.open(addprofile_icon_path),
                        size=(20, 20)
                    )
                    add_btn = ctk.CTkButton(
                        buttons_container,
                        text="  Add Profile",
                        image=addprofile_icon,
                        compound="left",
                        font=("Segoe UI", 14, "bold"),
                        height=40,
                        command=self._add_new_profile,
                        fg_color="#22c55e",
                        hover_color="#16a34a"
                    )
                else:
                    add_btn = ctk.CTkButton(
                        buttons_container,
                        text="➕  Add Profile",
                        font=("Segoe UI", 14, "bold"),
                        height=40,
                        command=self._add_new_profile,
                        fg_color="#22c55e",
                        hover_color="#16a34a"
                    )
                add_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

                # Import button
                import_btn = ctk.CTkButton(
                    buttons_container,
                    text="📂  Import Profiles",
                    font=("Segoe UI", 14, "bold"),
                    height=40,
                    command=self._import_profiles,
                    fg_color="#3b82f6",
                    hover_color="#2563eb"
                )
                import_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

            # Profile list container (only show if there are profiles) - Show AFTER add section
            if profiles and len(profiles) > 0:
                profiles_container = ctk.CTkFrame(
                    container, fg_color="transparent")
                profiles_container.pack(fill="both", expand=True, pady=(0, 20))

                # Display existing profiles
                for idx, profile in enumerate(profiles):
                    self._create_profile_card(profiles_container, profile, idx)

            # Tailscale Setup Guide Section
            is_dark = self.theme_manager.current_theme_name == "dark"
            guide_bg = "#2d2d2d" if is_dark else "#f0f0f0"

            guide_frame = ctk.CTkFrame(
                container,
                fg_color=guide_bg,
                corner_radius=12
            )
            guide_frame.pack(fill="x", pady=(20, 0))

            # Guide title and link
            guide_label = ctk.CTkLabel(
                guide_frame,
                text="Need help? Check the Tailscale Setup Guide:",
                font=("Segoe UI", 14),
                text_color=text_color,
                anchor="w"
            )
            guide_label.pack(pady=(15, 5), padx=20, anchor="w")

            # Clickable link button
            link_btn = ctk.CTkButton(
                guide_frame,
                text="https://tailscale.com/kb/1017/install",
                font=("Segoe UI", 13, "underline"),
                text_color=("#1e40af", "#60a5fa"),
                fg_color="transparent",
                hover_color=("gray90", "gray20"),
                anchor="w",
                command=lambda: self._open_url(
                    "https://tailscale.com/kb/1017/install")
            )
            link_btn.pack(pady=(0, 15), padx=20, anchor="w")

        except Exception as e:
            import traceback
            print(f"❌ Error loading profile manager: {e}")
            traceback.print_exc()

    def _create_profile_card(self, parent, profile, index):
        """Create a card for displaying and editing a profile"""
        text_color = self.theme_manager.current_theme.text_primary

        # Get card background color based on theme
        is_dark = self.theme_manager.current_theme_name == "dark"
        card_bg = "#2d2d2d" if is_dark else "#f0f0f0"

        # Profile card
        card = ctk.CTkFrame(
            parent,
            fg_color=card_bg,
            corner_radius=12
        )
        card.pack(fill="x", pady=(0, 15))

        # Profile info container
        info_container = ctk.CTkFrame(card, fg_color="transparent")
        info_container.pack(fill="x", padx=20, pady=20)
        info_container.grid_columnconfigure(0, weight=1)
        info_container.grid_columnconfigure(1, weight=0)

        # Name
        name_label = ctk.CTkLabel(
            info_container,
            text=f"{profile.name}",
            font=("Segoe UI", 18, "bold"),
            text_color=text_color,
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # IP
        ip_label = ctk.CTkLabel(
            info_container,
            text=f"IP: {profile.ip}",
            font=("Segoe UI", 14),
            text_color=text_color,
            anchor="w"
        )
        ip_label.grid(row=1, column=0, sticky="w")

        # Delete button with icon
        deleteprofile_icon_path = Path(
            __file__).parent.parent.parent / "Assets" / "deleteprofile.png"
        if deleteprofile_icon_path.exists():
            deleteprofile_icon = ctk.CTkImage(
                light_image=Image.open(deleteprofile_icon_path),
                dark_image=Image.open(deleteprofile_icon_path),
                size=(24, 24)
            )
            delete_btn = ctk.CTkButton(
                info_container,
                image=deleteprofile_icon,
                text="",
                width=40,
                height=40,
                command=lambda: self._delete_profile(profile.name),
                fg_color="transparent",
                hover_color=("gray80", "gray30")
            )
            delete_btn.image = deleteprofile_icon  # Keep reference
        else:
            # Fallback to emoji if icon not found
            delete_btn = ctk.CTkButton(
                info_container,
                text="🗑️",
                width=40,
                height=40,
                font=("Arial", 16),
                command=lambda: self._delete_profile(profile.name),
                fg_color="transparent",
                hover_color=("gray80", "gray30")
            )
        delete_btn.grid(row=0, column=1, rowspan=2, padx=(10, 0))

    def _add_new_profile(self):
        """Add a new profile from the profile manager"""
        name = self.new_profile_name_entry.get().strip()
        address = self.new_profile_address_entry.get().strip()

        # Validate inputs
        if not name:
            self.profile_error_label.configure(
                text="Please enter a profile name")
            return

        if not address:
            self.profile_error_label.configure(
                text="Please enter a Tailscale IP address")
            return

        # Basic IP validation
        if not self._validate_ip(address):
            self.profile_error_label.configure(
                text="Please enter a valid IP address (e.g., 100.64.0.1)")
            return

        # Create the profile
        try:
            self.config_manager.add_profile(name, address)
            self.config_manager.save_profiles()

            print(f"✅ Profile added: {name} ({address})")

            # Clear inputs
            self.new_profile_name_entry.delete(0, 'end')
            self.new_profile_address_entry.delete(0, 'end')
            self.profile_error_label.configure(text="")

            # Reload the page
            self._load_profile_manager_page()

            # Refresh profile dropdowns
            self._refresh_profiles()

        except Exception as e:
            self.profile_error_label.configure(
                text=f"Failed to add profile: {str(e)}")

    def _import_profiles(self):
        """Import profiles from a JSON file"""
        from tkinter import filedialog, messagebox
        import json

        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Profiles File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            parent=self
        )

        if not file_path:
            return

        try:
            # Read the JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)

            imported_count = 0
            skipped_count = 0

            # Handle both old format (list) and new format (dict with my_profile/peer_profiles)
            profiles_to_import = []

            if isinstance(data, list):
                # Old format: direct list of profiles
                profiles_to_import = data
            elif isinstance(data, dict):
                # New format: check for peer_profiles or profiles key
                if "peer_profiles" in data:
                    profiles_to_import = data["peer_profiles"]
                elif "profiles" in data:
                    profiles_to_import = data["profiles"]
                else:
                    raise ValueError("Invalid profile file format")

            # Import each profile
            for profile_data in profiles_to_import:
                name = profile_data.get("name", "").strip()
                address = profile_data.get("address", "").strip()

                if not name or not address:
                    skipped_count += 1
                    continue

                # Check if profile already exists
                existing = any(
                    p.name == name for p in self.config_manager.profiles)
                if existing:
                    # Ask user if they want to overwrite
                    overwrite = messagebox.askyesno(
                        "Profile Exists",
                        f"Profile '{name}' already exists. Overwrite?",
                        parent=self
                    )
                    if not overwrite:
                        skipped_count += 1
                        continue
                    # Remove existing profile
                    self.config_manager.profiles = [
                        p for p in self.config_manager.profiles if p.name != name
                    ]

                # Add the profile
                self.config_manager.add_profile(name, address)
                imported_count += 1

            # Save profiles
            if imported_count > 0:
                self.config_manager.save_profiles()

            # Show result
            message = f"Successfully imported {imported_count} profile(s)"
            if skipped_count > 0:
                message += f"\n{skipped_count} profile(s) skipped"

            messagebox.showinfo("Import Complete", message, parent=self)

            # Reload the page
            self._load_profile_manager_page()

            # Refresh profile dropdowns
            self._refresh_profiles()

        except json.JSONDecodeError:
            messagebox.showerror(
                "Import Error",
                "Invalid JSON file format",
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                "Import Error",
                f"Failed to import profiles: {str(e)}",
                parent=self
            )

    def _delete_profile(self, profile_name):
        """Delete a profile"""
        from tkinter import messagebox

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Delete Profile",
            f"Are you sure you want to delete the profile '{profile_name}'?",
            parent=self
        )

        if confirm:
            try:
                # Find and remove the profile
                self.config_manager.profiles = [
                    p for p in self.config_manager.profiles if p.name != profile_name
                ]
                self.config_manager.save_profiles()

                print(f"✅ Profile deleted: {profile_name}")

                # Reload the page
                self._load_profile_manager_page()

                # Refresh profile dropdowns
                self._refresh_profiles()

            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to delete profile: {str(e)}",
                    parent=self
                )

    def _load_statistics_page(self):
        """Load and display statistics in the main content area"""
        try:
            # Clear existing content
            for widget in self.statistics_frame.winfo_children():
                widget.destroy()

            # Get history from file manager
            history = self.file_manager.get_history()

            # Calculate statistics
            total_transfers = len(history)
            total_bytes = sum(item.get('size', 0) for item in history.values())
            total_mb = total_bytes / (1024 * 1024)
            total_gb = total_bytes / (1024 * 1024 * 1024)

            # Count by type (sent vs received)
            sent_count = sum(1 for item in history.values() if item.get(
                'sender') == self.my_profile_var.get())
            received_count = total_transfers - sent_count

            # File format statistics
            format_stats = {}
            for item in history.values():
                ext = item.get('extension', 'Unknown')
                if ext not in format_stats:
                    format_stats[ext] = 0
                format_stats[ext] += 1

            # Per-user statistics
            user_stats = {}
            for item in history.values():
                sender = item.get('sender', 'Unknown')
                receiver = item.get('receiver', 'Unknown')
                size = item.get('size', 0)

                # Track sent data
                if sender not in user_stats:
                    user_stats[sender] = {'sent': 0, 'received': 0, 'count': 0}
                user_stats[sender]['sent'] += size
                user_stats[sender]['count'] += 1

                # Track received data
                if receiver not in user_stats:
                    user_stats[receiver] = {
                        'sent': 0, 'received': 0, 'count': 0}
                user_stats[receiver]['received'] += size

            # Compact mode - show pie chart
            if self.is_compact_mode:
                # Title
                title = ctk.CTkLabel(
                    self.statistics_frame,
                    text="📊 File Types",
                    font=("Arial", 18, "bold"),
                    text_color=("gray10", "gray90")
                )
                title.pack(pady=(10, 15))

                if format_stats:
                    # Create pie chart using matplotlib
                    try:
                        import matplotlib
                        matplotlib.use('Agg')  # Non-interactive backend
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                        # Sort and get top 5 formats
                        sorted_formats = sorted(
                            format_stats.items(), key=lambda x: x[1], reverse=True)[:5]
                        labels = [ext for ext, _ in sorted_formats]
                        sizes = [count for _, count in sorted_formats]
                        colors = ["#e74c3c", "#3498db",
                                  "#2ecc71", "#f39c12", "#9b59b6"]

                        # Create figure with dark/light background based on theme
                        is_dark = self.theme_manager.current_theme_name == "dark"
                        fig_bg = "#2b2b2b" if is_dark else "#f0f0f0"
                        text_color = "#e0e0e0" if is_dark else "#1a1a1a"

                        fig, ax = plt.subplots(
                            figsize=(5, 5), facecolor=fig_bg)
                        ax.set_facecolor(fig_bg)

                        # Create pie chart
                        wedges, texts, autotexts = ax.pie(
                            sizes,
                            labels=labels,
                            colors=colors,
                            autopct='%1.0f%%',
                            startangle=90,
                            textprops={'color': text_color,
                                       'fontsize': 11, 'weight': 'bold'}
                        )

                        # Equal aspect ratio ensures circular pie
                        ax.axis('equal')

                        # Embed in tkinter
                        chart_container = ctk.CTkFrame(
                            self.statistics_frame,
                            fg_color=("gray90", "gray20"),
                            corner_radius=12
                        )
                        chart_container.pack(
                            pady=10, padx=15, fill="both", expand=True)

                        canvas = FigureCanvasTkAgg(fig, master=chart_container)
                        canvas.draw()
                        canvas.get_tk_widget().pack(pady=10, padx=10, fill="both", expand=True)

                        # Close the figure to free memory
                        plt.close(fig)

                    except ImportError:
                        # Fallback to bar chart if matplotlib not available
                        format_section = ctk.CTkFrame(
                            self.statistics_frame,
                            fg_color=("gray90", "gray20"),
                            corner_radius=12
                        )
                        format_section.pack(
                            pady=10, padx=15, fill="both", expand=True)

                        sorted_formats = sorted(
                            format_stats.items(), key=lambda x: x[1], reverse=True)[:5]
                        chart_frame = ctk.CTkFrame(
                            format_section, fg_color="transparent")
                        chart_frame.pack(pady=15, padx=15,
                                         fill="both", expand=True)

                        bar_colors = ["#e74c3c", "#3498db",
                                      "#2ecc71", "#f39c12", "#9b59b6"]
                        max_count = max(
                            [count for _, count in sorted_formats]) if sorted_formats else 1

                        for idx, (ext, count) in enumerate(sorted_formats):
                            row_frame = ctk.CTkFrame(
                                chart_frame, fg_color="transparent")
                            row_frame.pack(fill="x", pady=6)

                            ext_label = ctk.CTkLabel(
                                row_frame,
                                text=f"{ext}:",
                                font=("Arial", 12, "bold"),
                                width=60,
                                anchor="w",
                                text_color=("gray10", "gray90")
                            )
                            ext_label.pack(side="left", padx=(0, 8))

                            bar_width = int((count / max_count) * 200)
                            bar = ctk.CTkFrame(
                                row_frame,
                                width=bar_width,
                                height=25,
                                fg_color=bar_colors[idx % len(bar_colors)],
                                corner_radius=5
                            )
                            bar.pack(side="left", padx=(0, 8))
                            bar.pack_propagate(False)

                            count_label = ctk.CTkLabel(
                                bar,
                                text=f"{count}",
                                font=("Arial", 11, "bold"),
                                text_color="white"
                            )
                            count_label.place(
                                relx=0.5, rely=0.5, anchor="center")
                else:
                    # No data message
                    no_data = ctk.CTkLabel(
                        self.statistics_frame,
                        text="No transfer data yet",
                        font=("Arial", 14),
                        text_color="gray"
                    )
                    no_data.pack(pady=40)

                return  # Exit early for compact mode

            # Normal mode - full statistics view
            # Title
            title = ctk.CTkLabel(
                self.statistics_frame,
                text="Transfer Statistics",
                font=("Arial", 28, "bold"),
                text_color=("gray10", "gray90")
            )
            title.pack(pady=(20, 30))

            # Top metrics row with colorful cards
            metrics_row = ctk.CTkFrame(
                self.statistics_frame, fg_color="transparent")
            metrics_row.pack(pady=10, padx=20, fill="x")

            # Configure columns for even distribution
            for i in range(4):
                metrics_row.grid_columnconfigure(i, weight=1)

            # Metric cards
            metrics = [
                ("Total Transfers", f"{total_transfers}", "#3498db"),  # Blue
                ("Total Data", f"{total_gb:.2f} GB", "#2ecc71"),  # Green
                ("Files Sent", f"{sent_count}", "#e74c3c"),  # Red
                ("Files Received", f"{received_count}", "#f39c12"),  # Orange
            ]

            for idx, (label, value, color) in enumerate(metrics):
                card = ctk.CTkFrame(
                    metrics_row,
                    fg_color=color,
                    corner_radius=12
                )
                card.grid(row=0, column=idx, padx=10, pady=5, sticky="ew")

                value_label = ctk.CTkLabel(
                    card,
                    text=value,
                    font=("Arial", 32, "bold"),
                    text_color="white"
                )
                value_label.pack(pady=(15, 5))

                name_label = ctk.CTkLabel(
                    card,
                    text=label,
                    font=("Arial", 13),
                    text_color="white"
                )
                name_label.pack(pady=(0, 15))

            # File format pie chart section
            if format_stats:
                format_section = ctk.CTkFrame(
                    self.statistics_frame,
                    fg_color=("gray90", "gray20"),
                    corner_radius=12
                )
                format_section.pack(pady=20, padx=20, fill="both")

                format_title = ctk.CTkLabel(
                    format_section,
                    text="📁 Most Sent File Formats",
                    font=("Arial", 20, "bold"),
                    text_color=("gray10", "gray90")
                )
                format_title.pack(pady=(15, 10))

                # Sort formats by count
                sorted_formats = sorted(
                    format_stats.items(), key=lambda x: x[1], reverse=True)[:6]

                # Create visual bar chart
                chart_frame = ctk.CTkFrame(
                    format_section, fg_color="transparent")
                chart_frame.pack(pady=10, padx=30, fill="both", expand=True)

                # Colors for bars
                bar_colors = ["#e74c3c", "#3498db", "#2ecc71",
                              "#f39c12", "#9b59b6", "#1abc9c"]

                max_count = max(
                    [count for _, count in sorted_formats]) if sorted_formats else 1

                for idx, (ext, count) in enumerate(sorted_formats):
                    row_frame = ctk.CTkFrame(
                        chart_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=8)

                    # Extension label
                    ext_label = ctk.CTkLabel(
                        row_frame,
                        text=f"{ext}:",
                        font=("Arial", 14, "bold"),
                        width=80,
                        anchor="w",
                        text_color=("gray10", "gray90")
                    )
                    ext_label.pack(side="left", padx=(0, 10))

                    # Progress bar as visual representation
                    bar_width = int((count / max_count) * 400)
                    bar = ctk.CTkFrame(
                        row_frame,
                        width=bar_width,
                        height=30,
                        fg_color=bar_colors[idx % len(bar_colors)],
                        corner_radius=6
                    )
                    bar.pack(side="left", padx=(0, 10))
                    bar.pack_propagate(False)

                    # Count label on bar
                    count_label = ctk.CTkLabel(
                        bar,
                        text=f"{count}",
                        font=("Arial", 13, "bold"),
                        text_color="white"
                    )
                    count_label.place(relx=0.5, rely=0.5, anchor="center")

            # Per-user statistics section
            if user_stats:
                users_section = ctk.CTkFrame(
                    self.statistics_frame,
                    fg_color=("gray90", "gray20"),
                    corner_radius=12
                )
                users_section.pack(pady=20, padx=20, fill="both")

                users_title = ctk.CTkLabel(
                    users_section,
                    text="👥 Per-User Statistics",
                    font=("Arial", 20, "bold"),
                    text_color=("gray10", "gray90")
                )
                users_title.pack(pady=(15, 10))

                users_grid = ctk.CTkFrame(
                    users_section, fg_color="transparent")
                users_grid.pack(pady=10, padx=20, fill="both")

                for idx, (user, stats) in enumerate(sorted(user_stats.items(), key=lambda x: x[1]['count'], reverse=True)):
                    user_card = ctk.CTkFrame(
                        users_grid,
                        fg_color=("gray85", "gray25"),
                        corner_radius=10
                    )
                    user_card.pack(pady=8, padx=10, fill="x")

                    # User name with emoji
                    user_label = ctk.CTkLabel(
                        user_card,
                        text=f"👤 {user}",
                        font=("Arial", 16, "bold"),
                        text_color=("gray10", "gray90")
                    )
                    user_label.pack(pady=(12, 8), padx=15, anchor="w")

                    # Stats in columns
                    stats_row = ctk.CTkFrame(user_card, fg_color="transparent")
                    stats_row.pack(pady=(0, 12), padx=15, fill="x")

                    sent_mb = stats['sent'] / (1024 * 1024)
                    received_mb = stats['received'] / (1024 * 1024)

                    # Transfers count
                    transfers_frame = ctk.CTkFrame(
                        stats_row, fg_color="#3498db", corner_radius=8)
                    transfers_frame.pack(
                        side="left", padx=(0, 10), ipadx=15, ipady=8)
                    ctk.CTkLabel(
                        transfers_frame,
                        text=f"📊 {stats['count']} transfers",
                        font=("Arial", 12, "bold"),
                        text_color="white"
                    ).pack()

                    # Sent data
                    sent_frame = ctk.CTkFrame(
                        stats_row, fg_color="#e74c3c", corner_radius=8)
                    sent_frame.pack(side="left", padx=(
                        0, 10), ipadx=15, ipady=8)
                    ctk.CTkLabel(
                        sent_frame,
                        text=f"� Sent: {sent_mb:.1f} MB",
                        font=("Arial", 12, "bold"),
                        text_color="white"
                    ).pack()

                    # Received data
                    received_frame = ctk.CTkFrame(
                        stats_row, fg_color="#2ecc71", corner_radius=8)
                    received_frame.pack(
                        side="left", padx=(0, 10), ipadx=15, ipady=8)
                    ctk.CTkLabel(
                        received_frame,
                        text=f"📥 Received: {received_mb:.1f} MB",
                        font=("Arial", 12, "bold"),
                        text_color="white"
                    ).pack()

        except Exception as e:
            print(f"⚠️  Failed to load statistics: {e}")

    def _remove_file(self, file_path):
        """Remove a file from the gallery"""
        if file_path in self.shared_files:
            self.shared_files.remove(file_path)
        self._load_file_gallery()

    def _send_file(self, file_path):
        """Send a file to the connected peer"""
        if not self.is_connected:
            print("⚠️  Not connected to any peer")
            return

        if not Path(file_path).exists():
            print(f"⚠️  File not found: {file_path}")
            return

        try:
            # Get peer and sender info
            peer_name = self.peer_profile_var.get()
            my_name = self.my_profile_var.get()

            # Create transfer using transfer protocol
            transfer = self.network_manager.transfer_protocol.create_transfer(
                file_path=file_path,
                sender=my_name,
                receiver=peer_name
            )

            if transfer:
                print(f"📤 Sending file: {Path(file_path).name}")

                # Send file in background thread
                def send_async():
                    if self.network_manager.peer_socket:
                        success = self.network_manager.transfer_protocol.send_file(
                            self.network_manager.peer_socket,
                            transfer.transfer_id
                        )
                        if success:
                            print(
                                f"✅ File sent successfully: {Path(file_path).name}")
                            # Add to history with proper metadata
                            file_info = self.file_manager.get_file_info(
                                file_path)
                            if file_info:
                                self.file_manager.add_to_history(
                                    file_id=transfer.transfer_id,
                                    metadata={
                                        'filename': file_info['name'],
                                        'file_path': file_path,
                                        'file_size': file_info['size'],
                                        'direction': 'sent',
                                        'peer': peer_name,
                                        'sender': my_name
                                    }
                                )
                        else:
                            print(
                                f"❌ Failed to send file: {Path(file_path).name}")
                    else:
                        print("⚠️  No peer socket available")

                threading = __import__('threading')
                send_thread = threading.Thread(target=send_async, daemon=True)
                send_thread.start()

                print(f"✅ File queued for transfer: {Path(file_path).name}")
            else:
                print(
                    f"❌ Failed to create transfer for: {Path(file_path).name}")
        except Exception as e:
            print(f"❌ Failed to send file: {e}")

    def _toggle_connection(self):
        """Toggle connection to peer"""
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Connect to peer"""
        try:
            peer_name = self.peer_profile_var.get()
            my_name = self.my_profile_var.get()

            if not peer_name or peer_name not in self.profiles:
                print(f"⚠️  Unknown profile: {peer_name}")
                return

            if not my_name or my_name not in self.profiles:
                print(f"⚠️  Please select your profile first")
                return

            peer_info = self.profiles[peer_name]
            peer_ip = peer_info.get("ip")
            peer_port = peer_info.get("port", 5000)

            if not peer_ip:
                print(f"⚠️  No IP address for profile: {peer_name}")
                return

            # Update LED to connecting state
            self.status_led.configure(text_color="yellow")
            self.led_status = "connecting"
            self.connect_btn.configure(state="disabled")

            # Initiate connection via network_manager
            success = self.network_manager.connect(peer_ip, peer_name, my_name)
            if not success:
                self.status_led.configure(text_color="red")
                self.led_status = "idle"
                self.connect_btn.configure(state="normal")

        except Exception as e:
            print(f"⚠️  Failed to connect: {e}")
            self.status_led.configure(text_color="red")
            self.led_status = "idle"
            self.connect_btn.configure(state="normal")

    def _on_connecting(self):
        """Callback when connection is being established"""
        def update_ui():
            self.status_led.configure(text_color="yellow")
            self.led_status = "connecting"
        self.after(0, update_ui)

    def _on_connected(self):
        """Callback when connection is established"""
        def update_ui():
            self.is_connected = True
            self.status_led.configure(text_color="green")
            self.led_status = "connected"
            self.connect_btn.configure(text="Disconnect", state="normal")
            peer_name = self.network_manager.peer_name or "peer"
            print(f"✅ Connected to {peer_name}")
            # Show notification
            self._show_notification(
                "Connected",
                f"Successfully connected to {peer_name}"
            )
            # Refresh gallery to make files clickable
            if self.gallery_visible:
                self._load_file_gallery()
        self.after(0, update_ui)

    def _on_disconnected(self):
        """Callback when connection is lost"""
        def update_ui():
            self.is_connected = False
            self.status_led.configure(text_color="red")
            self.led_status = "idle"
            self.connect_btn.configure(text="Connect", state="normal")
            print(f"❌ Disconnected from peer")
            # Show notification
            self._show_notification(
                "Disconnected",
                "Connection to peer was lost"
            )
            # Refresh gallery to remove clickable state
            if self.gallery_visible:
                self._load_file_gallery()
        self.after(0, update_ui)

    def _on_connection_error(self, error_message):
        """Callback when connection error occurs"""
        def update_ui():
            self.status_led.configure(text_color="red")
            self.led_status = "idle"
            self.connect_btn.configure(text="Connect", state="normal")
            print(f"❌ Connection error: {error_message}")
            # Show notification
            self._show_notification(
                "Connection Failed",
                f"Failed to connect: {error_message}"
            )
        self.after(0, update_ui)

    def _connection_success(self):
        """Handle successful connection"""
        self.is_connected = True
        self.status_led.configure(text_color="green")
        self.led_status = "connected"
        self.connect_btn.configure(text="Disconnect")

    def _disconnect(self):
        """Disconnect from peer"""
        try:
            self.network_manager.disconnect()
            self.is_connected = False
            # Red when disconnected
            self.status_led.configure(text_color="red")
            self.led_status = "idle"
            self.connect_btn.configure(text="Connect")
        except Exception as e:
            print(f"⚠️  Disconnect error: {e}")

    def _update_scrollable_frame_backgrounds(self):
        """Update internal backgrounds of scrollable frames based on current theme"""
        try:
            tm_name = getattr(self.theme_manager, 'current_theme_name', None)
            if tm_name and str(tm_name).lower().startswith('light'):
                bg_color = '#ffffff'
            else:
                bg_color = self.theme_manager.current_theme.bg_primary

            # Update content frame
            if hasattr(self, 'content_frame'):
                try:
                    self.content_frame.configure(fg_color=bg_color)
                except Exception as e:
                    print(f"⚠️  Failed to update content frame: {e}")

            # Update statistics frame
            if hasattr(self, 'statistics_frame'):
                try:
                    self.statistics_frame.configure(fg_color=bg_color)
                except Exception as e:
                    print(f"⚠️  Failed to update statistics frame: {e}")

            # Update settings frame
            if hasattr(self, 'settings_frame'):
                try:
                    self.settings_frame.configure(fg_color=bg_color)
                except Exception as e:
                    print(f"⚠️  Failed to update settings frame: {e}")

            # Update profile manager frame
            if hasattr(self, 'profile_manager_frame'):
                try:
                    self.profile_manager_frame.configure(fg_color=bg_color)
                except Exception as e:
                    print(f"⚠️  Failed to update profile manager frame: {e}")

            # Reload profile manager if visible to update colors
            if hasattr(self, 'profile_manager_visible') and self.profile_manager_visible:
                try:
                    self._load_profile_manager_page()
                except Exception as e:
                    print(f"⚠️  Failed to update profile manager: {e}")
        except Exception as e:
            print(f"⚠️  Failed to update scrollable frame backgrounds: {e}")

    def _toggle_theme(self):
        """Toggle between light and dark theme with smooth transition"""
        # Fade out effect
        steps = 10
        for i in range(steps, 0, -1):
            alpha = i / steps
            try:
                self.attributes('-alpha', alpha)
            except:
                pass
            self.update()
            self.after(15)

        # Toggle theme
        self.theme_manager.toggle_theme()
        ctk.set_appearance_mode(self.theme_manager.get_ctk_theme_mode())

        # Update scrollable frame backgrounds for new theme
        self._update_scrollable_frame_backgrounds()

        # Keep the app icon static (blackp2p.ico) regardless of theme
        try:
            icon_path = self.assets_path / "blackp2p.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"⚠️  Failed to update window icon: {e}")

        # Update theme button icon
        try:
            icon_name = "sun.png" if self.theme_manager.current_theme_name == "dark" else "moon.png"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                icon_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(24, 24)
                )
                self.theme_btn.configure(image=icon_image)
            else:
                theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
                self.theme_btn.configure(text=theme_icon)
        except Exception as e:
            print(f"⚠️  Failed to update theme icon: {e}")
            theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
            self.theme_btn.configure(text=theme_icon)

        # Update upload icon based on theme
        try:
            icon_name = "whiteupload.png" if self.theme_manager.current_theme_name == "dark" else "blackupload.png"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                upload_image = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(64, 64)
                )
                self.drop_icon.configure(image=upload_image)
        except Exception as e:
            print(f"⚠️  Failed to update upload icon: {e}")

        # Update top/bottom bar colors
        try:
            self._update_top_bar_theme()
        except Exception as e:
            print(f"⚠️  Failed to update top bar theme on toggle: {e}")

        # Update root window and container backgrounds to match new theme
        try:
            # Get the proper theme background from ThemeManager
            new_bg = self.theme_manager.current_theme.bg_primary

            # Update root window background
            self.configure(bg=new_bg)

            # Update main_frame and content_frame backgrounds
            if hasattr(self, 'main_frame'):
                self.main_frame.configure(fg_color=new_bg)
            if hasattr(self, 'content_frame'):
                self.content_frame.configure(fg_color=new_bg)

            # Update gallery frame background
            if hasattr(self, 'gallery_frame'):
                self.gallery_frame.configure(fg_color=new_bg)

            # Update container (root container frame)
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    widget.configure(fg_color=new_bg)
        except Exception as e:
            # Fade in effect
            print(f"⚠️  Failed to update background on theme toggle: {e}")
        for i in range(1, steps + 1):
            alpha = i / steps
            try:
                self.attributes('-alpha', alpha)
            except:
                pass
            self.update()
            self.after(15)

        # Store new original fg color
        self.content_frame_original_fg = self.content_frame.cget("fg_color")

    def _show_notification(self, title, message, duration=5):
        """Show a Windows toast notification"""
        if self.toaster:
            try:
                import threading
                # Run in background thread to avoid blocking UI

                def show():
                    self.toaster.show_toast(
                        title,
                        message,
                        duration=duration,
                        icon_path=None,
                        threaded=True
                    )
                threading.Thread(target=show, daemon=True).start()
            except Exception as e:
                print(f"⚠️  Failed to show notification: {e}")

    # Transfer protocol callbacks
    def _on_transfer_start(self, transfer):
        """Handle transfer start"""
        def update_ui():
            print(
                f"📤 Transfer started: {transfer.filename} ({transfer.file_size} bytes)")
            # Store transfer for progress tracking
            self.active_transfers[transfer.transfer_id] = transfer

            # Show progress bar in gallery item
            if transfer.file_path in self.file_widgets:
                widgets = self.file_widgets[transfer.file_path]
                # Show and reset progress bar
                widgets["progress"].set(0)
                widgets["progress"].pack(pady=2)
                # Show status label
                widgets["status"].configure(text="Uploading... 0%")
                widgets["status"].pack(pady=2)
                # Change icon to uploading
                widgets["icon"].configure(text="📤")

            # Show notification
            self._show_notification(
                "File Transfer Started",
                f"Sending {transfer.filename}..."
            )
        self.after(0, update_ui)

    def _on_transfer_progress(self, transfer):
        """Handle transfer progress"""
        def update_ui():
            progress = transfer.progress_percent
            speed = transfer.transfer_speed / 1024  # KB/s
            eta = transfer.eta_seconds

            # Update progress bar in gallery item
            if transfer.file_path in self.file_widgets:
                widgets = self.file_widgets[transfer.file_path]
                widgets["progress"].set(progress / 100)
                widgets["status"].configure(
                    text=f"Uploading... {progress:.0f}% ({speed:.1f} KB/s)"
                )

            print(
                f"📊 Progress: {transfer.filename} - {progress:.1f}% ({speed:.1f} KB/s, ETA: {eta:.0f}s)")
        self.after(0, update_ui)

    def _on_transfer_complete(self, transfer):
        """Handle transfer complete"""
        def update_ui():
            print(f"✅ Transfer complete: {transfer.filename}")
            # Remove from active transfers
            if transfer.transfer_id in self.active_transfers:
                del self.active_transfers[transfer.transfer_id]

            # Update gallery item to show completion
            if transfer.file_path in self.file_widgets:
                widgets = self.file_widgets[transfer.file_path]
                widgets["progress"].set(1.0)
                widgets["status"].configure(text="✅ Sent!", text_color="green")
                widgets["icon"].configure(text="✅")

                # Hide progress bar after 3 seconds
                def hide_progress():
                    if transfer.file_path in self.file_widgets:
                        widgets["progress"].pack_forget()
                        widgets["status"].pack_forget()
                        widgets["icon"].configure(text="📄")
                self.after(3000, hide_progress)

            # Show notification
            self._show_notification(
                "File Transfer Complete",
                f"Successfully sent {transfer.filename}"
            )
        self.after(0, update_ui)

    def _on_transfer_error(self, transfer, error_msg):
        """Handle transfer error"""
        def update_ui():
            print(f"❌ Transfer error: {transfer.filename} - {error_msg}")
            # Remove from active transfers
            if transfer.transfer_id in self.active_transfers:
                del self.active_transfers[transfer.transfer_id]

            # Update gallery item to show error
            if transfer.file_path in self.file_widgets:
                widgets = self.file_widgets[transfer.file_path]
                widgets["progress"].pack_forget()
                widgets["status"].configure(text="❌ Failed", text_color="red")
                widgets["icon"].configure(text="❌")

                # Reset after 3 seconds
                def reset_display():
                    if transfer.file_path in self.file_widgets:
                        widgets["status"].pack_forget()
                        widgets["icon"].configure(text="📄")
                self.after(3000, reset_display)

            # Show notification
            self._show_notification(
                "File Transfer Failed",
                f"Failed to send {transfer.filename}: {error_msg}"
            )
        self.after(0, update_ui)


def main():
    """Main entry point"""
    import os
    from pathlib import Path
    from ui.theme_manager import ThemeManager
    from core.network_manager import NetworkManager
    from core.file_manager import FileManager

    # Initialize managers
    app_data_dir = Path(os.getenv('APPDATA')) / 'SyncStream'
    app_data_dir.mkdir(parents=True, exist_ok=True)

    theme_manager = ThemeManager()
    network_manager = NetworkManager()
    file_manager = FileManager(app_data_dir)

    # Create and run app
    app = MainWindow(theme_manager, network_manager, file_manager)
    app.mainloop()


if __name__ == "__main__":
    main()
