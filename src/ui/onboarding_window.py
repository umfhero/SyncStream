"""
Onboarding Window for SyncStream

Guides new users through initial setup of their Tailscale profiles.
"""

import customtkinter as ctk
from pathlib import Path
from PIL import Image
import webbrowser


class OnboardingWindow(ctk.CTkToplevel):
    """Onboarding window for first-time setup"""

    def __init__(self, parent, config_manager, theme_manager, callback=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.callback = callback

        # Window setup
        self.title("Welcome to SyncStream")
        self.geometry("600x500")
        self.resizable(False, False)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"600x500+{x}+{y}")

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        """Build the onboarding UI"""
        theme = self.theme_manager.current_theme

        # Main container
        container = ctk.CTkFrame(self, fg_color=theme.bg_primary)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            container,
            text="Welcome to SyncStream!",
            font=("Segoe UI", 28, "bold"),
            text_color=theme.text_primary
        )
        title.pack(pady=(0, 10))

        # Subtitle
        subtitle = ctk.CTkLabel(
            container,
            text="Fast, secure P2P file sharing over Tailscale",
            font=("Segoe UI", 14),
            text_color=theme.text_secondary
        )
        subtitle.pack(pady=(0, 30))

        # Info section
        info_frame = ctk.CTkFrame(
            container, fg_color=theme.bg_secondary, corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 20))

        info_text = (
            "To get started, you'll need:\n\n"
            "1. Tailscale installed and running\n"
            "2. Your Tailscale device name or IP address\n"
            "3. The Tailscale address of the person you want to share files with"
        )

        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Segoe UI", 12),
            text_color=theme.text_primary,
            justify="left"
        )
        info_label.pack(padx=20, pady=15)

        # Tailscale setup button
        tailscale_btn = ctk.CTkButton(
            container,
            text="Open Tailscale Setup Guide",
            font=("Segoe UI", 12),
            fg_color=theme.info,
            hover_color="#2980B9",
            command=self._open_tailscale_guide,
            height=40
        )
        tailscale_btn.pack(pady=(0, 30))

        # Profile setup section
        setup_label = ctk.CTkLabel(
            container,
            text="Create Your First Profile",
            font=("Segoe UI", 16, "bold"),
            text_color=theme.text_primary
        )
        setup_label.pack(pady=(0, 15))

        # Profile name input
        name_frame = ctk.CTkFrame(container, fg_color="transparent")
        name_frame.pack(fill="x", pady=(0, 10))

        name_label = ctk.CTkLabel(
            name_frame,
            text="Profile Name:",
            font=("Segoe UI", 12),
            text_color=theme.text_primary,
            width=120,
            anchor="w"
        )
        name_label.pack(side="left", padx=(0, 10))

        self.name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="e.g., My Laptop",
            font=("Segoe UI", 12),
            height=35
        )
        self.name_entry.pack(side="left", fill="x", expand=True)

        # Tailscale address input
        address_frame = ctk.CTkFrame(container, fg_color="transparent")
        address_frame.pack(fill="x", pady=(0, 20))

        address_label = ctk.CTkLabel(
            address_frame,
            text="Your Tailscale IP:",
            font=("Segoe UI", 12),
            text_color=theme.text_primary,
            width=120,
            anchor="w"
        )
        address_label.pack(side="left", padx=(0, 10))

        self.address_entry = ctk.CTkEntry(
            address_frame,
            placeholder_text="e.g., 100.64.0.1",
            font=("Segoe UI", 12),
            height=35
        )
        self.address_entry.pack(side="left", fill="x", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))

        skip_btn = ctk.CTkButton(
            button_frame,
            text="Skip for Now",
            font=("Segoe UI", 12),
            fg_color="transparent",
            border_width=2,
            border_color=theme.border,
            text_color=theme.text_secondary,
            hover_color=theme.bg_secondary,
            command=self._skip_setup,
            height=40,
            width=120
        )
        skip_btn.pack(side="left", padx=(0, 5))

        import_btn = ctk.CTkButton(
            button_frame,
            text="📂 Import",
            font=("Segoe UI", 12),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._import_profiles,
            height=40,
            width=120
        )
        import_btn.pack(side="left", padx=(0, 5))

        create_btn = ctk.CTkButton(
            button_frame,
            text="Create Profile",
            font=("Segoe UI", 12),
            fg_color=theme.accent_primary,
            hover_color=theme.accent_hover,
            command=self._create_profile,
            height=40
        )
        create_btn.pack(side="right", fill="x", expand=True)

    def _open_tailscale_guide(self):
        """Open Tailscale setup guide in browser"""
        webbrowser.open("https://tailscale.com/kb/1017/install")

    def _create_profile(self):
        """Create the profile and close onboarding"""
        name = self.name_entry.get().strip()
        address = self.address_entry.get().strip()

        if not name:
            self._show_error("Please enter a profile name")
            return

        if not address:
            self._show_error("Please enter your Tailscale IP address")
            return

        # Basic IP validation
        if not self._validate_ip(address):
            self._show_error(
                "Please enter a valid IP address (e.g., 100.64.0.1)")
            return

        # Create the profile
        try:
            self.config_manager.add_profile(name, address)
            self.config_manager.save_profiles()

            # Call callback if provided
            if self.callback:
                self.callback(name, address)

            # Close window
            self.destroy()
        except Exception as e:
            self._show_error(f"Failed to create profile: {str(e)}")

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
                    continue

                # Add the profile
                self.config_manager.add_profile(name, address)
                imported_count += 1

            # Save profiles
            if imported_count > 0:
                self.config_manager.save_profiles()

            # Show result and close
            messagebox.showinfo(
                "Import Complete",
                f"Successfully imported {imported_count} profile(s)!",
                parent=self
            )

            # Call callback if provided
            if self.callback and imported_count > 0:
                self.callback(None, None)

            # Close window
            self.destroy()

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

    def _skip_setup(self):
        """Skip onboarding setup"""
        # Call callback with None to indicate skip
        if self.callback:
            self.callback(None, None)

        self.destroy()

    def _validate_ip(self, ip):
        """Basic IP address validation"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except ValueError:
            return False

    def _show_error(self, message):
        """Show error message"""
        theme = self.theme_manager.current_theme

        # Create error popup
        error_window = ctk.CTkToplevel(self)
        error_window.title("Input Error")
        error_window.geometry("350x150")
        error_window.resizable(False, False)

        # Center on parent
        error_window.transient(self)
        error_window.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - 175
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        error_window.geometry(f"350x150+{x}+{y}")

        # Error message
        msg_label = ctk.CTkLabel(
            error_window,
            text=message,
            font=("Segoe UI", 12),
            text_color=theme.text_primary,
            wraplength=300
        )
        msg_label.pack(pady=30)

        # OK button
        ok_btn = ctk.CTkButton(
            error_window,
            text="OK",
            font=("Segoe UI", 12),
            fg_color=theme.accent_primary,
            hover_color=theme.accent_hover,
            command=error_window.destroy,
            width=100,
            height=35
        )
        ok_btn.pack(pady=(0, 20))
