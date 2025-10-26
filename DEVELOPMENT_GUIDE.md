# SyncStream Development Guide

This guide will help you continue building SyncStream effectively.

---

## 🏗️ Architecture Overview

### Module Dependencies

```
syncstream.py (main entry point)
    ├── config_manager.py (settings, profiles)
    ├── network_manager.py (TCP sockets, connections)
    ├── file_manager.py (file operations, thumbnails)
    ├── transfer_protocol.py (file transfer logic)
    ├── theme_manager.py (UI themes)
    ├── main_window.py (main UI)
    │   ├── file_gallery.py (file grid display)
    │   ├── transfer_progress.py (progress bars)
    │   └── compact_view.py (minimal UI)
    ├── tray_icon.py (system tray)
    ├── notifications.py (system notifications)
    └── statistics.py (usage tracking)
```

### Data Flow

```
User Action → UI Component → Manager → Network/File System → UI Update
```

Example: Sending a file

1. User drags file → `main_window.py` detects drop
2. `file_manager.py` validates and prepares file
3. `transfer_protocol.py` creates transfer job
4. `network_manager.py` sends data over socket
5. `transfer_progress.py` updates progress bar
6. `notifications.py` shows completion notification

---

## 📝 Coding Standards

### File Structure

```python
"""
Module Name - Brief Description

Detailed explanation of what this module does.
"""

# Standard library imports
import os
import json

# Third-party imports
import customtkinter as ctk

# Local imports
from .config_manager import ConfigManager

# Constants
DEFAULT_TIMEOUT = 180

# Classes
class MyClass:
    """Class description"""
    pass

# Main execution (for testing)
if __name__ == "__main__":
    # Test code here
    pass
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `NetworkManager`)
- **Functions/Methods**: `snake_case` (e.g., `send_file`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
- **Private methods**: `_leading_underscore` (e.g., `_internal_method`)

### Type Hints

```python
def send_file(self, file_path: str, peer_ip: str) -> bool:
    """Send a file to a peer"""
    pass

def get_profiles(self) -> List[Profile]:
    """Get all profiles"""
    pass
```

---

## 🔧 Building Core Modules

### Network Manager Template

```python
"""
SyncStream - Network Manager
Handles TCP socket connections and auto-reconnect logic
"""

import socket
import threading
from enum import Enum
from typing import Callable, Optional

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"

class NetworkManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.state = ConnectionState.DISCONNECTED
        self.socket: Optional[socket.socket] = None
        self.callbacks = {
            'on_connected': [],
            'on_disconnected': [],
            'on_data_received': []
        }

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for network events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def connect(self, peer_ip: str, port: int):
        """Connect to a peer"""
        pass

    def disconnect(self):
        """Disconnect from current peer"""
        pass

    def send_data(self, data: bytes) -> bool:
        """Send data over the connection"""
        pass

    def _receive_loop(self):
        """Background thread for receiving data"""
        pass

    def _auto_reconnect(self):
        """Auto-reconnect logic with timeout"""
        pass
```

### File Manager Template

```python
"""
SyncStream - File Manager
Handles file operations, thumbnails, and history
"""

from pathlib import Path
from PIL import Image
from typing import Optional, Dict
import json

class FileManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.download_dir = config_manager.get_download_location()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.transfer_history: Dict = {}

    def prepare_file(self, file_path: str) -> Optional[Dict]:
        """Prepare a file for transfer"""
        pass

    def generate_thumbnail(self, file_path: str) -> Optional[Image.Image]:
        """Generate thumbnail for image files"""
        pass

    def save_received_file(self, data: bytes, filename: str) -> Path:
        """Save a received file"""
        pass

    def auto_zip_folder(self, folder_path: str) -> str:
        """Auto-zip a folder for transfer"""
        pass

    def add_to_history(self, file_id: str, metadata: Dict):
        """Add transfer to history"""
        pass

    def load_history(self) -> Dict:
        """Load transfer history"""
        pass
```

---

## 🎨 UI Development Tips

### CustomTkinter Basics

```python
import customtkinter as ctk

# Create window
app = ctk.CTk()
app.title("SyncStream")
app.geometry("1200x800")

# Set theme
ctk.set_appearance_mode("dark")  # or "light"
ctk.set_default_color_theme("blue")

# Create widgets
button = ctk.CTkButton(app, text="Connect", command=on_connect)
button.pack(pady=10)

label = ctk.CTkLabel(app, text="Status: Disconnected")
label.pack()

# Grid layout
frame = ctk.CTkFrame(app)
frame.grid(row=0, column=0, padx=10, pady=10)

app.mainloop()
```

### Connection LED Indicator

```python
class ConnectionLED(ctk.CTkLabel):
    def __init__(self, master):
        super().__init__(master, text="●", font=("Arial", 24))
        self.set_disconnected()

    def set_disconnected(self):
        self.configure(text_color="red")

    def set_connecting(self):
        self.configure(text_color="orange")

    def set_connected(self):
        self.configure(text_color="green")
```

### File Gallery Grid

```python
class FileGallery(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, label_text="File Gallery")
        self.files = []
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def add_file(self, file_data: Dict):
        """Add a file card to the gallery"""
        row = len(self.files) // 4
        col = len(self.files) % 4

        card = FileCard(self, file_data)
        card.grid(row=row, column=col, padx=10, pady=10)

        self.files.append(card)
```

---

## 🧪 Testing Strategy

### Unit Tests

Create `tests/` directory with test files:

```python
# tests/test_config_manager.py
import unittest
from src.core.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def test_load_profiles(self):
        config = ConfigManager()
        self.assertIsNotNone(config.profiles)

    def test_theme_toggle(self):
        config = ConfigManager()
        original = config.settings.theme
        new_theme = config.toggle_theme()
        self.assertNotEqual(original, new_theme)

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

Test the complete flow:

1. Start both apps
2. Connect
3. Send file
4. Verify receipt
5. Check history

### Manual Testing Checklist

- [ ] Connection establishment
- [ ] Auto-reconnect after disconnect
- [ ] File drag and drop
- [ ] Multiple file transfers
- [ ] Theme switching
- [ ] Window resizing
- [ ] Compact mode
- [ ] System tray minimize/restore
- [ ] Notifications
- [ ] Search and filters

---

## 🐛 Debugging Tips

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("This is a debug message")
```

### Network Debugging

```python
# Check Tailscale connectivity
import subprocess
result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True)
print(result.stdout)

# Test socket connection
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('100.x.x.x', 12345))
if result == 0:
    print("Port is open")
else:
    print("Port is closed")
sock.close()
```

### Common Issues

1. **Can't connect**: Check Tailscale is running, IPs are correct
2. **Files not sending**: Check file permissions, disk space
3. **UI not updating**: Ensure updates happen on main thread
4. **Slow performance**: Profile the code, optimize file I/O

---

## 📦 Packaging for Distribution

### Using PyInstaller

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --name=SyncStream \
            --icon=Assets/p2p.ico \
            --windowed \
            --onefile \
            src/syncstream.py

# Output will be in dist/SyncStream.exe
```

### Include Data Files

```python
# In .spec file, add:
datas=[
    ('Assets', 'Assets'),
    ('config/*.template', 'config')
]
```

---

## 🚀 Development Workflow

### Daily Workflow

1. Pull latest changes (if working with others)
2. Create feature branch: `git checkout -b feature/network-manager`
3. Implement feature following TODO.md
4. Test thoroughly
5. Commit with clear message
6. Push and create PR (if applicable)

### Commit Messages

```
feat: Add auto-reconnect logic to NetworkManager
fix: Correct thumbnail generation for PNG files
docs: Update README with installation instructions
refactor: Simplify file transfer protocol
test: Add unit tests for ConfigManager
```

---

## 📚 Useful Resources

### CustomTkinter

- [Documentation](https://customtkinter.tomschimansky.com/)
- [GitHub](https://github.com/TomSchimansky/CustomTkinter)
- [Examples](https://github.com/TomSchimansky/CustomTkinter/tree/master/examples)

### Networking

- [Python Socket Programming](https://docs.python.org/3/library/socket.html)
- [TCP Protocol Guide](https://docs.python.org/3/howto/sockets.html)

### File Handling

- [Pillow Documentation](https://pillow.readthedocs.io/)
- [zipfile Module](https://docs.python.org/3/library/zipfile.html)

---

## ✅ Before Committing

- [ ] Code follows style guide
- [ ] Added docstrings to new functions
- [ ] Tested manually
- [ ] No hardcoded IPs or sensitive data
- [ ] Updated TODO.md if needed
- [ ] Added comments for complex logic

---

## 🎯 Priority Order for Development

Based on dependencies, build in this order:

1. **config_manager.py** ✅ (Done!)
2. **theme_manager.py** (needed for UI)
3. **network_manager.py** (core functionality)
4. **transfer_protocol.py** (file transfer logic)
5. **file_manager.py** (file operations)
6. **main_window.py** (basic UI)
7. **file_gallery.py** (gallery display)
8. **transfer_progress.py** (progress tracking)
9. **tray_icon.py** (system tray)
10. **notifications.py** (notifications)

---

**Good luck with development! 🚀**

Remember: Start small, test often, commit frequently!
