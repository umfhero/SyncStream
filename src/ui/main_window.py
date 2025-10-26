"""
Main window for SyncStream application
"""

import customtkinter as ctk
from pathlib import Path
from PIL import Image
import json
from typing import Optional

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("⚠️  tkinterdnd2 not available. Drag & drop will be disabled.")


class MainWindow(ctk.CTk if not DRAG_DROP_AVAILABLE else TkinterDnD.Tk):
    """Main application window"""

    def __init__(self, theme_manager, network_manager, file_manager):
        super().__init__()

        # Store managers
        self.theme_manager = theme_manager
        self.network_manager = network_manager
        self.file_manager = file_manager

        # Configure window
        self.title("SyncStream")
        self.geometry("900x700")

        # Set theme to green and appearance mode
        ctk.set_default_color_theme("green")
        ctk.set_appearance_mode(self.theme_manager.get_ctk_theme_mode())

        # Set window icon based on theme
        try:
            icon_name = "whitep2p.ico" if self.theme_manager.current_theme_name == "dark" else "blackp2p.ico"
            icon_path = Path(__file__).parent.parent.parent / \
                "Assets" / icon_name
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"⚠️  Failed to load icon: {e}")

        # Load profiles
        self._load_profiles()

        # Initialize connection state
        self.is_connected = False
        self.led_status = "idle"  # idle, connecting, connected

        # Initialize shared files list
        self.shared_files = []

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

    def _build_ui(self):
        """Build the main UI"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Top bar
        self.grid_rowconfigure(1, weight=1)  # Main content

        # Build sections
        self._build_top_bar()
        self._build_main_content()

    def _build_top_bar(self):
        """Build the top bar with profiles and connection"""
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
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

    def _build_main_content(self):
        """Build the main content area"""
        main_frame = ctk.CTkFrame(self)
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

        bottom_bar.grid_columnconfigure(0, weight=0)
        bottom_bar.grid_columnconfigure(1, weight=1)
        bottom_bar.grid_columnconfigure(2, weight=0)
        bottom_bar.grid_columnconfigure(3, weight=0)

        # Gallery toggle button
        self.gallery_btn = ctk.CTkButton(
            bottom_bar,
            text="Show Gallery",
            width=120,
            command=self._toggle_gallery,
            font=("Arial", 11, "bold")
        )
        self.gallery_btn.grid(row=0, column=0, padx=5, pady=5)

        # Filter button
        self.filter_btn = ctk.CTkButton(
            bottom_bar,
            text="Filter: All",
            width=100,
            command=self._cycle_filter,
            font=("Arial", 11, "bold")
        )
        self.filter_btn.grid(row=0, column=2, padx=5, pady=5)

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

        self.theme_btn.grid(row=0, column=3, padx=5, pady=5)

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
        except Exception as e:
            print(f"⚠️  Failed to setup drag & drop: {e}")

    def _handle_drag_enter(self, event):
        """Handle drag enter - darken the drop zone"""
        try:
            current_fg = self.content_frame.cget("fg_color")
            if isinstance(current_fg, tuple):
                light, dark = current_fg
                if self.theme_manager.current_theme_name == "dark":
                    darker = self._darken_color(dark)
                    self.content_frame.configure(fg_color=darker)
                else:
                    darker = self._darken_color(light)
                    self.content_frame.configure(fg_color=darker)
            else:
                darker = self._darken_color(current_fg)
                self.content_frame.configure(fg_color=darker)
        except Exception as e:
            print(f"⚠️  Drag enter effect failed: {e}")

    def _handle_drag_leave(self, event):
        """Handle drag leave - restore original color"""
        try:
            self.content_frame.configure(
                fg_color=self.content_frame_original_fg)
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

    def _handle_drop(self, event):
        """Handle file drop"""
        try:
            # Restore original color
            self.content_frame.configure(
                fg_color=self.content_frame_original_fg)

            # Get files
            files = self.tk.splitlist(event.data)
            for file_path in files:
                if Path(file_path).is_file() and file_path not in self.shared_files:
                    self.shared_files.append(file_path)

            # Refresh gallery
            self._load_file_gallery()

            # Show gallery if hidden
            if not self.gallery_visible:
                self._toggle_gallery()
        except Exception as e:
            print(f"⚠️  Failed to handle drop: {e}")

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
        else:
            # Show gallery
            self.drop_icon.grid_forget()
            self.drop_label.grid_forget()
            self.browse_btn.grid_forget()
            self.gallery_frame.grid(
                row=3, column=0, sticky="nsew", padx=10, pady=10)
            self.gallery_btn.configure(text="Hide Gallery")
            self.gallery_visible = True

    def _cycle_filter(self):
        """Cycle through file filters"""
        # Placeholder for filter functionality
        pass

    def _load_file_gallery(self):
        """Load files into gallery"""
        # Clear existing items
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Get files from shared_files list
        files = self.shared_files

        if not files:
            no_files_label = ctk.CTkLabel(
                self.gallery_frame,
                text="No files shared yet",
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
            file_frame = ctk.CTkFrame(self.gallery_frame)
            file_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # File icon
            file_icon = ctk.CTkLabel(
                file_frame,
                text="📄",
                font=("Arial", 32)
            )
            file_icon.pack(pady=5)

            # File name
            name_label = ctk.CTkLabel(
                file_frame,
                text=file_name if len(
                    file_name) < 20 else file_name[:17] + "...",
                font=("Arial", 10)
            )
            name_label.pack(pady=2)

            # Remove button
            remove_btn = ctk.CTkButton(
                file_frame,
                text="×",
                width=30,
                height=25,
                command=lambda fp=file_path: self._remove_file(fp),
                font=("Arial", 14, "bold"),
                fg_color="red",
                hover_color="darkred"
            )
            remove_btn.pack(pady=5)

    def _remove_file(self, file_path):
        """Remove a file from the gallery"""
        if file_path in self.shared_files:
            self.shared_files.remove(file_path)
        self._load_file_gallery()

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
            if peer_name not in self.profiles:
                print(f"⚠️  Unknown profile: {peer_name}")
                return

            peer_info = self.profiles[peer_name]
            self.status_led.configure(text_color="yellow")
            self.led_status = "connecting"

            # TODO: Implement actual connection logic
            # For now, just simulate connection
            self.after(1000, self._connection_success)
        except Exception as e:
            print(f"⚠️  Failed to connect: {e}")
            self.status_led.configure(text_color="red")
            self.led_status = "idle"

    def _connection_success(self):
        """Handle successful connection"""
        self.is_connected = True
        self.status_led.configure(text_color="green")
        self.led_status = "connected"
        self.connect_btn.configure(text="Disconnect")

    def _disconnect(self):
        """Disconnect from peer"""
        # TODO: Implement actual disconnection logic
        self.is_connected = False
        self.status_led.configure(text_color="red")  # Red when disconnected
        self.led_status = "idle"
        self.connect_btn.configure(text="Connect")

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
