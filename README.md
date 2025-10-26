# SyncStream

**Modern peer-to-peer file sharing with unlimited file sizes**

SyncStream is a complete redesign of Vortext-Tunnel-V3, offering a clean, modern interface for direct file transfers over Tailscale VPN. Built with ease of use and reliability in mind.

---

## Key Features

### **Seamless File Transfers**

- **Unlimited file size** - Share files of any size
- **Multiple simultaneous transfers** - Queue and track multiple files at once
- **Auto-retry on failure** - Smart retry logic with 3 attempts
- **Transfer progress tracking** - Real-time progress bars with speed and ETA
- **Queue management** - Visual checklist of queued, active, and completed transfers
- **Offline queueing** - Files are automatically sent when connection is restored

### **Smart File Handling**

- **Drag-and-drop** - Primary method for quick file sharing
- **File browser** - Alternative method with standard file picker
- **Auto-zip folders** - Automatically compresses folders for transfer
- **Optional compression** - Enable compression for faster transfers (off by default)
- **File history** - Complete history of sent and received files persists across sessions

### **Modern UI/UX**

- **Dual theme support** - Light and dark themes with quick toggle
- **Responsive design** - Scales beautifully from 30% to 100% screen size
- **Compact mode** - Auto-switches to minimal UI when window is small (<30% screen)
- **System tray integration** - Always running, accessible from tray
- **Visual connection status** - Green/orange/red LED indicator
- **Smart notifications** - System notifications for transfers and errors

### **File Gallery**

- **Grid layout with thumbnails** - Visual gallery of all shared files
- **Responsive thumbnails** - Automatically size to window
- **Rich metadata** - Shows filename, size, date, and sender
- **Advanced search** - Search with autocomplete suggestions
- **Smart filters** - Filter by sender, date, and file type (mp4, png, jpg, etc.)
- **Quick actions** - Open, Delete, Re-send, Save As, Download

### **Reliable Networking**

- **Built on Tailscale** - Secure VPN-based peer-to-peer connectivity
- **Auto-reconnect** - Automatically reconnects with 2-3 minute timeout
- **Manual retry** - "Try Connecting" button to restart connection attempts
- **Connection monitoring** - Real-time connection status tracking
- **Intelligent error detection** - Detects and reports Tailscale connection issues

### **Network Statistics**

- **Total data transferred** - Track overall data usage
- **Per-user statistics** - See data transferred per peer
- **Transfer history** - Complete log of all transfers with timestamps
- **Network usage tracking** - Monitor your file sharing activity

---

## Architecture

### Network Infrastructure

- **Tailscale VPN** for secure peer-to-peer connectivity
- **TCP sockets** on port 12345 for file transfers
- **Dual server/client model** - Both users act as server and client
- **Profile-based connections** - Connect to peers via stored profiles

### Profile System

- **JSON-based profiles** stored locally (not tracked in git)
- **Easy customization** - Simple JSON format for adding peers
- **Auto-reconnect** - Remembers last connected peer
- **Example profiles** included in `profiles.json.template`

### Data Persistence

- **AppData storage** - Files stored in `%APPDATA%/SyncStream/` by default
- **Custom save location** - Users can set preferred download folder
- **Transfer logs** - Complete history with metadata
- **Config persistence** - Theme, settings, and connection state saved

---

## Technical Stack

- **Python 3.8+**
- **CustomTkinter** - Modern, customizable UI framework
- **TkinterDnD2** - Drag-and-drop functionality
- **Pillow (PIL)** - Image processing and thumbnails
- **pystray** - System tray integration
- **plyer/win10toast** - Native system notifications
- **Raw TCP sockets** - Direct file transfers without overhead

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Tailscale installed and running
- Windows (tested), Linux/Mac (should work with minor modifications)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/umfhero/SyncStream.git
cd SyncStream

# Install dependencies
pip install -r requirements.txt

# Copy the profile template
copy config\profiles.json.template config\profiles.json

# Edit profiles.json with your Tailscale IPs and peer names

# Run SyncStream
python src/syncstream.py
```

---

## Configuration

### Setting Up Profiles

1. Copy `config/profiles.json.template` to `config/profiles.json`
2. Edit the file with your peer information:

```json
{
  "profiles": [
    {
      "name": "YourName",
      "ip": "100.x.x.x",
      "port": 12345
    },
    {
      "name": "PeerName",
      "ip": "100.y.y.y",
      "port": 12345
    }
  ],
  "last_profile": null,
  "last_peer": null
}
```

3. Save and launch SyncStream

### Application Settings

- **Theme** - Toggle between light and dark themes
- **Download Location** - Set custom default save folder
- **Compression** - Enable/disable file compression (off by default)
- **Auto-reconnect** - Configure timeout duration

---

## Usage

### Sending Files

1. **Drag and drop** files or folders into the window, OR
2. Click the **"Send File"** button to browse
3. Files are automatically queued and sent
4. Monitor progress in the transfer checklist

### Receiving Files

- Files are automatically accepted and saved
- System notification alerts you to incoming files
- Files appear in the gallery immediately
- Access files via Open or Download buttons

### Managing Connections

- Select your profile and target peer from dropdowns
- Click **Connect** to establish connection
- Connection status shown via LED indicator:
  - 🔴 **Red** - Disconnected
  - 🟠 **Orange** - Connecting
  - 🟢 **Green** - Connected
- Auto-reconnects if connection drops
- Click **Try Connecting** to manually retry

### Using the Gallery

- **Search** - Type to search files with autocomplete
- **Filter** - Filter by sender, date, or file type
- **Right-click** file for context menu:
  - **Open** - Open file in default app
  - **Re-send** - Send file again to current peer
  - **Save As** - Save copy to custom location
  - **Download** - Download received file
  - **Delete** - Remove from gallery and disk

---

### Theme Philosophy

SyncStream features a carefully crafted dual-theme system that prioritizes clarity, usability, and modern aesthetics.

---

## 📝 Project Status

**Current Phase:** Initial Development

See [TODO.md](TODO.md) for detailed development roadmap and progress tracking.

---

## 🤝 Contributing

SyncStream is currently in active development. Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

TBC (not sure yet)

---

## 🙏 Acknowledgments

- Built on top of concepts from Vortext-Tunnel-V3
- Useing [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) framework
- Powered by [Tailscale](https://tailscale.com/) for networking

---
1. START.bat          ← Checks everything and launches!
2. Or setup.bat       ← If you need to install first
3. Then run.bat       ← To launch directly

**Made with ❤️ for seamless file sharing**
