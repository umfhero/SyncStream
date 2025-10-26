"""
SyncStream - File Manager

Handles file operations, thumbnails, and transfer history.
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from PIL import Image
import io


class FileManager:
    """Manages file operations and history"""

    def __init__(self, app_data_dir: Path, download_dir: Optional[Path] = None):
        """
        Initialize file manager

        Args:
            app_data_dir: Application data directory
            download_dir: Custom download directory (optional)
        """
        self.app_data_dir = Path(app_data_dir)
        self.app_data_dir.mkdir(parents=True, exist_ok=True)

        # Set download directory
        if download_dir:
            self.download_dir = Path(download_dir)
        else:
            self.download_dir = self.app_data_dir / "Downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Thumbnails directory
        self.thumbnails_dir = self.app_data_dir / "Thumbnails"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

        # History file
        self.history_file = self.app_data_dir / "transfer_history.json"
        self.history: Dict[str, Dict] = {}
        self._load_history()

        # Supported image formats for thumbnails
        self.image_formats = {'.png', '.jpg',
                              '.jpeg', '.gif', '.bmp', '.ico', '.webp'}

    def _load_history(self) -> None:
        """Load transfer history from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                print(f"📜 Loaded {len(self.history)} items from history")
            except Exception as e:
                print(f"❌ Error loading history: {e}")
                self.history = {}

    def _save_history(self) -> None:
        """Save transfer history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving history: {e}")

    def add_to_history(self, file_id: str, metadata: Dict) -> None:
        """
        Add a file transfer to history

        Args:
            file_id: Unique file identifier
            metadata: File metadata (name, size, sender, etc.)
        """
        self.history[file_id] = {
            **metadata,
            'timestamp': datetime.now().isoformat()
        }
        self._save_history()

    def get_history(self) -> Dict[str, Dict]:
        """Get complete transfer history"""
        return self.history

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """
        Get information about a file

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file info or None
        """
        path = Path(file_path)

        if not path.exists():
            return None

        stat = path.stat()

        return {
            'name': path.name,
            'path': str(path.absolute()),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'extension': path.suffix.lower(),
            'is_image': path.suffix.lower() in self.image_formats,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    def generate_thumbnail(self, file_path: str, size: tuple = (128, 128)) -> Optional[Path]:
        """
        Generate thumbnail for an image file

        Args:
            file_path: Path to image file
            size: Thumbnail size (width, height)

        Returns:
            Path to thumbnail or None
        """
        path = Path(file_path)

        if not path.exists() or path.suffix.lower() not in self.image_formats:
            return None

        try:
            # Create thumbnail filename
            thumb_name = f"{path.stem}_thumb{path.suffix}"
            thumb_path = self.thumbnails_dir / thumb_name

            # Check if thumbnail already exists
            if thumb_path.exists():
                return thumb_path

            # Generate thumbnail
            with Image.open(path) as img:
                # Preserve transparency for RGBA/LA/P images
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Convert P mode to RGBA to preserve transparency
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    # Keep RGBA format to preserve transparency
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    # Save as PNG to preserve alpha channel
                    img.save(thumb_path, 'PNG')
                else:
                    # For non-transparent images, convert to RGB
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    img.save(thumb_path, quality=85)

            return thumb_path

        except Exception as e:
            print(f"❌ Error generating thumbnail: {e}")
            return None

    def zip_folder(self, folder_path: str, output_name: Optional[str] = None) -> Optional[Path]:
        """
        Zip a folder for transfer

        Args:
            folder_path: Path to folder
            output_name: Custom output name (optional)

        Returns:
            Path to zip file or None
        """
        folder = Path(folder_path)

        if not folder.exists() or not folder.is_dir():
            return None

        try:
            # Create zip filename
            if output_name:
                zip_name = output_name if output_name.endswith(
                    '.zip') else f"{output_name}.zip"
            else:
                zip_name = f"{folder.name}.zip"

            zip_path = self.download_dir / zip_name

            # Create zip file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(folder.parent)
                        zipf.write(file_path, arcname)

            print(f"📦 Created zip: {zip_path}")
            return zip_path

        except Exception as e:
            print(f"❌ Error zipping folder: {e}")
            return None

    def unzip_file(self, zip_path: str, output_dir: Optional[str] = None) -> Optional[Path]:
        """
        Unzip a file

        Args:
            zip_path: Path to zip file
            output_dir: Output directory (optional)

        Returns:
            Path to extracted directory or None
        """
        zip_file = Path(zip_path)

        if not zip_file.exists() or zip_file.suffix.lower() != '.zip':
            return None

        try:
            # Set output directory
            if output_dir:
                extract_dir = Path(output_dir)
            else:
                extract_dir = self.download_dir / zip_file.stem

            extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                zipf.extractall(extract_dir)

            print(f"📂 Extracted to: {extract_dir}")
            return extract_dir

        except Exception as e:
            print(f"❌ Error unzipping file: {e}")
            return None

    def save_received_file(self, data: bytes, filename: str) -> Optional[Path]:
        """
        Save received file data

        Args:
            data: File data bytes
            filename: Name for the file

        Returns:
            Path to saved file or None
        """
        try:
            file_path = self.download_dir / filename

            # Handle duplicate filenames
            counter = 1
            while file_path.exists():
                name, ext = os.path.splitext(filename)
                file_path = self.download_dir / f"{name}_{counter}{ext}"
                counter += 1

            # Save file
            with open(file_path, 'wb') as f:
                f.write(data)

            print(f"💾 Saved file: {file_path}")
            return file_path

        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file

        Args:
            file_path: Path to file

        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                print(f"🗑️  Deleted: {file_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error deleting file: {e}")
            return False

    def copy_file(self, source: str, destination: str) -> bool:
        """
        Copy a file

        Args:
            source: Source file path
            destination: Destination path

        Returns:
            True if copied successfully
        """
        try:
            shutil.copy2(source, destination)
            print(f"📋 Copied: {source} → {destination}")
            return True
        except Exception as e:
            print(f"❌ Error copying file: {e}")
            return False

    def get_file_icon_emoji(self, extension: str) -> str:
        """
        Get emoji icon for file type

        Args:
            extension: File extension (e.g., '.txt')

        Returns:
            Emoji string
        """
        ext = extension.lower()

        # Images
        if ext in self.image_formats:
            return "🖼️"

        # Videos
        if ext in {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}:
            return "🎥"

        # Audio
        if ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}:
            return "🎵"

        # Documents
        if ext in {'.pdf', '.doc', '.docx', '.txt', '.rtf'}:
            return "📄"

        # Archives
        if ext in {'.zip', '.rar', '.7z', '.tar', '.gz'}:
            return "📦"

        # Code
        if ext in {'.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h'}:
            return "💻"

        # Default
        return "📁"


if __name__ == "__main__":
    # Test the file manager
    print("🧪 Testing FileManager...")

    app_data = Path.home() / "AppData" / "Roaming" / "SyncStream"
    manager = FileManager(app_data)

    print(f"📁 Download directory: {manager.download_dir}")
    print(f"📜 History items: {len(manager.history)}")
