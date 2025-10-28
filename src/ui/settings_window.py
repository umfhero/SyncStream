"""
Settings Window for SyncStream

Displays app version, update status, and allows updates.
"""

import customtkinter as ctk
from tkinter import messagebox
import webbrowser
from pathlib import Path


class SettingsWindow(ctk.CTkToplevel):
    """Settings window for version info and updates"""
    
    def __init__(self, parent, version_manager, theme_manager):
        super().__init__(parent)
        
        self.version_manager = version_manager
        self.theme_manager = theme_manager
        self.parent = parent
        
        # Configure window
        self.title("Settings - SyncStream")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Center window on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.geometry(f"600x500+{x}+{y}")
        
        # Apply theme
        try:
            theme_bg = theme_manager.current_theme.bg_primary
            self.configure(fg_color=theme_bg)
        except:
            pass
        
        # Set icon
        try:
            icon_path = Path(__file__).parent.parent.parent / "Assets" / "blackp2p.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except:
            pass
        
        # Build UI
        self._build_ui()
        
        # Check for updates on open
        self._check_updates()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        """Build the settings UI"""
        # Main container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            container,
            text="⚙️ Settings",
            font=("Arial", 28, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Version Info Section
        version_frame = ctk.CTkFrame(container)
        version_frame.pack(fill="x", pady=(0, 15))
        
        version_inner = ctk.CTkFrame(version_frame, fg_color="transparent")
        version_inner.pack(padx=20, pady=20)
        
        # App Version
        version_label = ctk.CTkLabel(
            version_inner,
            text="Current Version:",
            font=("Arial", 14, "bold")
        )
        version_label.pack(anchor="w", pady=(0, 5))
        
        self.version_value = ctk.CTkLabel(
            version_inner,
            text=f"v{self.version_manager.get_current_version()}",
            font=("Arial", 18),
            text_color=("green", "lightgreen")
        )
        self.version_value.pack(anchor="w", pady=(0, 15))
        
        # Repository
        repo_label = ctk.CTkLabel(
            version_inner,
            text="Repository:",
            font=("Arial", 14, "bold")
        )
        repo_label.pack(anchor="w", pady=(0, 5))
        
        repo_link = ctk.CTkButton(
            version_inner,
            text=self.version_manager.get_repo_url(),
            font=("Arial", 12, "underline"),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._open_repo,
            anchor="w"
        )
        repo_link.pack(anchor="w", pady=(0, 10))
        
        # Update Status Section
        update_frame = ctk.CTkFrame(container)
        update_frame.pack(fill="x", pady=(0, 15))
        
        update_inner = ctk.CTkFrame(update_frame, fg_color="transparent")
        update_inner.pack(padx=20, pady=20)
        
        # Status indicator
        status_container = ctk.CTkFrame(update_inner, fg_color="transparent")
        status_container.pack(fill="x", pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(
            status_container,
            text="Update Status:",
            font=("Arial", 14, "bold")
        )
        self.status_label.pack(side="left", padx=(0, 10))
        
        self.status_indicator = ctk.CTkLabel(
            status_container,
            text="⟳ Checking...",
            font=("Arial", 14),
            text_color=("gray50", "gray50")
        )
        self.status_indicator.pack(side="left")
        
        # Latest version info (hidden initially)
        self.latest_version_label = ctk.CTkLabel(
            update_inner,
            text="",
            font=("Arial", 12),
            text_color=("gray50", "gray70")
        )
        self.latest_version_label.pack(anchor="w", pady=(0, 10))
        
        # Update button
        self.update_btn = ctk.CTkButton(
            update_inner,
            text="Check for Updates",
            font=("Arial", 14, "bold"),
            height=40,
            command=self._check_updates,
            state="disabled"
        )
        self.update_btn.pack(fill="x", pady=(0, 10))
        
        # Progress bar (hidden initially)
        self.progress_frame = ctk.CTkFrame(update_inner, fg_color="transparent")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=("Arial", 12)
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        # Release Notes Section
        notes_frame = ctk.CTkFrame(container)
        notes_frame.pack(fill="both", expand=True)
        
        notes_label = ctk.CTkLabel(
            notes_frame,
            text="📝 Release Notes",
            font=("Arial", 14, "bold")
        )
        notes_label.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Scrollable text area for release notes
        self.notes_text = ctk.CTkTextbox(
            notes_frame,
            font=("Arial", 11),
            wrap="word",
            height=150
        )
        self.notes_text.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.notes_text.insert("1.0", "Loading release information...")
        self.notes_text.configure(state="disabled")
        
        # Close button
        close_btn = ctk.CTkButton(
            container,
            text="Close",
            font=("Arial", 14),
            height=40,
            command=self.destroy
        )
        close_btn.pack(pady=(15, 0))
    
    def _check_updates(self):
        """Check for available updates"""
        self.status_indicator.configure(text="⟳ Checking...", text_color=("gray50", "gray50"))
        self.update_btn.configure(state="disabled", text="Checking...")
        
        def callback(success, version, error):
            # Update UI on main thread
            self.after(0, lambda: self._update_check_complete(success, version, error))
        
        self.version_manager.check_for_updates(callback)
    
    def _update_check_complete(self, success, version, error):
        """Handle update check completion"""
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
                
                # Show release notes
                self._load_release_notes()
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
                
                # Show current release notes
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
                command=self._check_updates
            )
    
    def _load_release_notes(self):
        """Load release notes from GitHub"""
        try:
            release_info = self.version_manager.latest_release_info
            if release_info:
                notes = release_info.get("body", "No release notes available.")
                release_name = release_info.get("name", "")
                tag_name = release_info.get("tag_name", "")
                
                self.notes_text.configure(state="normal")
                self.notes_text.delete("1.0", "end")
                
                if release_name:
                    self.notes_text.insert("end", f"{release_name}\n", "bold")
                elif tag_name:
                    self.notes_text.insert("end", f"{tag_name}\n", "bold")
                
                self.notes_text.insert("end", "\n" + notes)
                self.notes_text.configure(state="disabled")
            else:
                self.notes_text.configure(state="normal")
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert("1.0", "No release information available.")
                self.notes_text.configure(state="disabled")
        except Exception as e:
            self.notes_text.configure(state="normal")
            self.notes_text.delete("1.0", "end")
            self.notes_text.insert("1.0", f"Failed to load release notes: {str(e)}")
            self.notes_text.configure(state="disabled")
    
    def _install_update(self):
        """Install the available update"""
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
        self.progress_frame.pack(fill="x", pady=(10, 0))
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
        self.progress_label.configure(text=message)
        self.progress_bar.set(percent / 100.0)
    
    def _update_complete(self, success, message):
        """Handle update completion"""
        if success:
            messagebox.showinfo(
                "Update Complete",
                message,
                parent=self
            )
            # Close settings and restart prompt
            self.destroy()
            
            # Prompt to restart
            restart = messagebox.askyesno(
                "Restart Required",
                "Would you like to restart SyncStream now?",
                parent=self.parent
            )
            if restart:
                self.parent.quit()
        else:
            messagebox.showerror(
                "Update Failed",
                message,
                parent=self
            )
            self.update_btn.configure(state="normal")
            self.progress_frame.pack_forget()
    
    def _open_repo(self):
        """Open repository in browser"""
        webbrowser.open(self.version_manager.get_repo_url())
