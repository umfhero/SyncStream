"""
Main window for SyncStream application
"""

import customtkinter as ctk
from pathlib import Path
from PIL import Image
import json
import os
from typing import Optional

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


class MainWindow(ctk.CTk if not DRAG_DROP_AVAILABLE else TkinterDnD.Tk):
    """Main application window"""

    def __init__(self, theme_manager, network_manager, file_manager):
        super().__init__()

        # Store managers
        self.theme_manager = theme_manager
        self.network_manager = network_manager
        self.file_manager = file_manager

        # Clear old thumbnails to regenerate with transparency
        self._clear_thumbnail_cache()

        # Configure window
        self.title("SyncStream")
        self.geometry("900x700")

        # Set theme to green and appearance mode
        ctk.set_default_color_theme("green")
        ctk.set_appearance_mode(self.theme_manager.get_ctk_theme_mode())

        # Fix theme background by setting background color to match CTk container
        if DRAG_DROP_AVAILABLE:
            # For TkinterDnD.Tk, set the background color to match the container frame
            if self.theme_manager.current_theme_name == "dark":
                # gray14 - matches dark theme container
                self.configure(bg="#242424")
            else:
                # gray92 - matches light theme container
                self.configure(bg="#ebebeb")

        # Set window icon based on theme (BLACK icon for dark mode, WHITE icon for light mode)
        try:
            icon_name = "blackp2p.ico" if self.theme_manager.current_theme_name == "dark" else "whitep2p.ico"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
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

        # Track active transfers
        self.active_transfers = {}

        # Track file widgets for progress updates
        self.file_widgets = {}  # {file_path: {"frame": frame, "progress": progress_bar}}

        # Track drag-drop state
        self.is_dragging = False
        self.original_window_fg = None

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

        # Build UI
        self._build_ui()

        # Setup drag and drop if available
        if DRAG_DROP_AVAILABLE:
            self._setup_drag_drop()

    def _load_profiles(self):
        """Load profile information from config"""
        try:
            config_path = Path(__file__).parent.parent.parent / \
                "config" / "settings.json"
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

        # If system tray is enabled and running, minimize to tray instead of closing
        if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.is_running:
            self.withdraw()  # Hide window
        else:
            # Shutdown network manager
            if self.network_manager:
                self.network_manager.shutdown()
            self.destroy()

    def _build_ui(self):
        """Build the main UI"""
        # Create a container frame that covers the entire window
        # This ensures consistent background in drag-drop mode
        container = ctk.CTkFrame(self, fg_color=(
            "gray92", "gray14"), corner_radius=0)
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
        top_frame = ctk.CTkFrame(parent, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Configure columns - add weight to push right elements to the right
        top_frame.grid_columnconfigure(0, weight=0)  # My Profile label
        top_frame.grid_columnconfigure(1, weight=0)  # My Profile selector
        top_frame.grid_columnconfigure(2, weight=0)  # Pipe
        top_frame.grid_columnconfigure(3, weight=0)  # Connect to label
        top_frame.grid_columnconfigure(4, weight=1)  # Peer selector - expands
        top_frame.grid_columnconfigure(5, weight=0)  # Connect button
        top_frame.grid_columnconfigure(6, weight=0)  # LED

        # My Profile label
        my_profile_label = ctk.CTkLabel(
            top_frame,
            text="My Profile:",
            font=("Arial", 13, "bold")
        )
        my_profile_label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        # My Profile selector
        profile_names = list(self.profiles.keys())
        my_profile_width = max(
            [len(name) for name in profile_names]) * 10 if profile_names else 100

        self.my_profile_var = ctk.StringVar(
            value=profile_names[0] if profile_names else "")
        self.my_profile_selector = ctk.CTkOptionMenu(
            top_frame,
            variable=self.my_profile_var,
            values=profile_names if profile_names else ["No profiles"],
            width=my_profile_width,
            font=("Arial", 12),
            dynamic_resizing=False
        )
        self.my_profile_selector.grid(
            row=0, column=1, padx=(0, 10), sticky="w")

        # Pipe separator
        pipe_label = ctk.CTkLabel(
            top_frame,
            text="|",
            font=("Arial", 16, "bold")
        )
        pipe_label.grid(row=0, column=2, padx=10)

        # Connect to label
        connect_label = ctk.CTkLabel(
            top_frame,
            text="Connect to:",
            font=("Arial", 13, "bold")
        )
        connect_label.grid(row=0, column=3, padx=(0, 5), sticky="w")

        # Peer Profile selector
        peer_profile_width = max(
            [len(name) for name in profile_names]) * 10 if profile_names else 100

        self.peer_profile_var = ctk.StringVar(value=profile_names[1] if len(
            profile_names) > 1 else (profile_names[0] if profile_names else ""))
        self.peer_profile_selector = ctk.CTkOptionMenu(
            top_frame,
            variable=self.peer_profile_var,
            values=profile_names if profile_names else ["No profiles"],
            width=peer_profile_width,
            font=("Arial", 12),
            dynamic_resizing=False
        )
        self.peer_profile_selector.grid(
            row=0, column=4, padx=(0, 10), sticky="w")

        # Connect button
        self.connect_btn = ctk.CTkButton(
            top_frame,
            text="Connect",
            command=self._toggle_connection,
            width=100,
            font=("Arial", 12, "bold")
        )
        self.connect_btn.grid(row=0, column=5, padx=(0, 10), sticky="e")

        # Status LED
        self.status_led = ctk.CTkLabel(
            top_frame,
            text="●",
            font=("Arial", 20),
            text_color="red"  # Default to red when not connected
        )
        self.status_led.grid(row=0, column=6, sticky="e")

    def _build_main_content(self, parent):
        """Build the main content area"""
        main_frame = ctk.CTkFrame(parent)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Configure grid
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)

        # Content frame (drag & drop area)
        self.content_frame = ctk.CTkFrame(main_frame)
        self.content_frame.grid(
            row=0, column=0, sticky="nsew", padx=10, pady=10)

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
            width=150,
            font=("Arial", 12, "bold")
        )
        self.browse_btn.grid(row=2, column=0, pady=(5, 40))

        # File gallery (hidden by default)
        self.gallery_visible = False
        self.current_filter = "All"  # All, Images, Documents, Videos, Archives
        self.gallery_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text=""
        )
        # Don't grid it yet - will be shown on toggle

        # Configure gallery grid
        for i in range(4):
            self.gallery_frame.grid_columnconfigure(i, weight=1)

        # Bottom bar
        bottom_bar = ctk.CTkFrame(main_frame)
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        bottom_bar.grid_columnconfigure(0, weight=0)  # Gallery toggle button
        bottom_bar.grid_columnconfigure(1, weight=0)  # Search box
        bottom_bar.grid_columnconfigure(2, weight=0)  # Filter button
        bottom_bar.grid_columnconfigure(3, weight=1)  # Spacer
        bottom_bar.grid_columnconfigure(4, weight=0)  # Theme button

        # Store bottom_bar reference for later use
        self.bottom_bar = bottom_bar

        # Gallery toggle button
        self.gallery_btn = ctk.CTkButton(
            bottom_bar,
            text="Show Gallery",
            width=120,
            command=self._toggle_gallery,
            font=("Arial", 11, "bold")
        )
        self.gallery_btn.grid(row=0, column=0, padx=5, pady=5)

        # Search box (hidden by default, shown when gallery is visible)
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self._filter_gallery())
        self.search_entry = ctk.CTkEntry(
            bottom_bar,
            placeholder_text="Search files...",
            width=200,
            textvariable=self.search_var,
            font=("Arial", 11)
        )
        # Don't grid it yet - will be shown when gallery is visible

        # Filter button (hidden by default, shown when gallery is visible)
        self.filter_btn = ctk.CTkButton(
            bottom_bar,
            text="Filter: All",
            width=100,
            command=self._cycle_filter,
            font=("Arial", 11, "bold")
        )
        # Don't grid it yet - will be shown when gallery is visible

        # Theme toggle button
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
                self.theme_btn = ctk.CTkButton(
                    bottom_bar,
                    text="",
                    image=icon_image,
                    command=self._toggle_theme,
                    width=50,
                    height=40,
                    fg_color="transparent",
                    hover_color=("gray85", "gray25")
                )
            else:
                theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
                self.theme_btn = ctk.CTkButton(
                    bottom_bar,
                    text=theme_icon,
                    command=self._toggle_theme,
                    width=50,
                    height=40,
                    font=("Arial", 18),
                    fg_color="transparent",
                    hover_color=("gray85", "gray25")
                )
        except Exception as e:
            theme_icon = "☀️" if self.theme_manager.current_theme_name == "dark" else "🌙"
            self.theme_btn = ctk.CTkButton(
                bottom_bar,
                text=theme_icon,
                command=self._toggle_theme,
                width=50,
                height=40,
                font=("Arial", 18),
                fg_color="transparent",
                hover_color=("gray85", "gray25")
            )

        self.theme_btn.grid(row=0, column=4, padx=5, pady=5)

        # Load file gallery
        self._load_file_gallery()

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
            # Load icon image
            icon_name = "blackp2p.ico"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name

            if icon_path.exists():
                icon_image = Image.open(icon_path)
            else:
                # Create a simple default icon if file not found
                icon_image = Image.new('RGB', (64, 64), color='blue')

            # Create system tray icon
            menu = pystray.Menu(
                item('Show', self._show_window, default=True),
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
        """Show the main window"""
        self.after(0, lambda: self.deiconify())

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
            # Show gallery
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()
            self.gallery_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.gallery_btn.configure(text="Hide Gallery")
            self.gallery_visible = True

            # Show search and filter
            self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            self.filter_btn.grid(row=0, column=2, padx=5, pady=5)

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
            no_files_label = ctk.CTkLabel(
                self.gallery_frame,
                text="No files found" if (
                    search_filter or self.current_filter != "All") else "No files shared yet",
                font=("Arial", 14),
                text_color="gray"
            )
            no_files_label.grid(row=0, column=0, columnspan=4, pady=20)
            return

        # Display files in grid
        for idx, file_path in enumerate(files):
            row = idx // 4
            col = idx % 4

            file_name = Path(file_path).name

            # Clean container with better styling - thinner borders visible in both themes
            file_frame = ctk.CTkFrame(
                self.gallery_frame,
                corner_radius=10,
                border_width=1,
                border_color=("gray70", "gray40")
            )
            file_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            # Generate thumbnail or use icon
            thumbnail = self._get_file_thumbnail(file_path)

            if thumbnail:
                # Use thumbnail image with transparent background
                file_icon = ctk.CTkLabel(
                    file_frame,
                    image=thumbnail,
                    text="",
                    fg_color="transparent"
                )
                file_icon.image = thumbnail  # Keep reference
            else:
                # Use emoji icon based on file type
                icon_emoji = self._get_file_icon(file_path)
                file_icon = ctk.CTkLabel(
                    file_frame,
                    text=icon_emoji,
                    font=("Arial", 32),
                    fg_color="transparent"
                )

            file_icon.pack(pady=(10, 5))

            # File name
            name_label = ctk.CTkLabel(
                file_frame,
                text=file_name if len(
                    file_name) < 20 else file_name[:17] + "...",
                font=("Arial", 10, "bold")
            )
            name_label.pack(pady=2)

            # Progress bar (initially hidden)
            progress_bar = ctk.CTkProgressBar(
                file_frame,
                width=120,
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
                width=70,
                height=28,
                command=lambda fp=file_path: self._open_file(fp),
                font=("Arial", 11, "bold"),
                fg_color="#28a745",  # Lighter green
                hover_color="#218838"  # Medium green
            )
            open_btn.pack(side="left", padx=3)

            # Send button (only if connected)
            if self.is_connected:
                send_btn = ctk.CTkButton(
                    btn_container,
                    text="📤",
                    width=35,
                    height=28,
                    command=lambda fp=file_path: self._send_file(fp),
                    font=("Arial", 13),
                    fg_color="#28a745",  # Lighter green
                    hover_color="#218838"  # Medium green
                )
                send_btn.pack(side="left", padx=3)

            # Remove button
            remove_btn = ctk.CTkButton(
                btn_container,
                text="×",
                width=35,
                height=28,
                command=lambda fp=file_path: self._remove_file(fp),
                font=("Arial", 16, "bold"),
                fg_color="red",
                hover_color="darkred"
            )
            remove_btn.pack(side="left", padx=3)

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
                "remove_btn": remove_btn
            }

    def _get_file_thumbnail(self, file_path):
        """Generate thumbnail for image files"""
        try:
            path = Path(file_path)
            if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico']:
                # Use file_manager to generate thumbnail
                thumb_path = self.file_manager.generate_thumbnail(
                    str(file_path), size=(80, 80))
                if thumb_path and Path(thumb_path).exists():
                    # Load thumbnail as CTkImage
                    pil_image = Image.open(thumb_path)
                    ctk_image = ctk.CTkImage(
                        light_image=pil_image,
                        dark_image=pil_image,
                        size=(80, 80)
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

            # Set icon based on theme (BLACK for dark, WHITE for light)
            icon_name = "blackp2p.ico" if ctk.get_appearance_mode() == "Dark" else "whitep2p.ico"
            icon_path = self.assets_path / icon_name
            if icon_path.exists():
                dialog.iconbitmap(str(icon_path))

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

            # Close button
            close_btn = ctk.CTkButton(
                dialog,
                text="Close",
                command=dialog.destroy,
                width=100
            )
            close_btn.pack(pady=20)

        except Exception as e:
            print(f"⚠️  Failed to show file details: {e}")

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

        # Update window icon based on theme
        try:
            icon_name = "whitep2p.ico" if self.theme_manager.current_theme_name == "dark" else "blackp2p.ico"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name
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

        # Fade in effect
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
