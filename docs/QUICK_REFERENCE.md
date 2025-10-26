# 🚀 SyncStream v1.0 - Quick Reference

## Installation

```bash
# Windows - Double click:
setup.bat

# Or manual:
python install.py
pip install -r requirements.txt
```

## Configuration

```bash
# 1. Find your Tailscale IP
tailscale ip

# 2. Edit config/profiles.json
# Replace IPs with your actual Tailscale IPs
```

## Running

```bash
# Windows - Double click:
run.bat

# Or manual:
python src/syncstream.py
```

---

## 🎮 Quick Controls

| Action               | How To                             |
| -------------------- | ---------------------------------- |
| **Connect**          | Select profiles → Click "Connect"  |
| **Disconnect**       | Click "Disconnect" button          |
| **Retry Connection** | Click "Try Again" button           |
| **Toggle Theme**     | Click ☀️/🌙 button                 |
| **Send File**        | Click "Browse Files"               |
| **Drag File**        | Drag to window (needs tkinterdnd2) |

---

## 🚦 LED Status

| Color         | Meaning       |
| ------------- | ------------- |
| 🔴 **Red**    | Disconnected  |
| 🟠 **Orange** | Connecting... |
| 🟢 **Green**  | Connected     |

---

## 📁 File Locations

| Item          | Location                                     |
| ------------- | -------------------------------------------- |
| **Config**    | `config/profiles.json`                       |
| **Downloads** | `%APPDATA%\SyncStream\Downloads\`            |
| **History**   | `%APPDATA%\SyncStream\transfer_history.json` |
| **Settings**  | `config/settings.json`                       |

---

## 🐛 Troubleshooting

### Can't Connect?

```bash
# Check Tailscale
tailscale status

# Check IP
tailscale ip

# Verify profiles.json has correct IPs
```

### Missing profiles.json?

```bash
copy config\profiles.json.template config\profiles.json
# Then edit with your IPs
```

### Import Errors?

```bash
pip install -r requirements.txt
```

---

## ✨ What Works in v1.0

✅ Connection management  
✅ Theme toggling  
✅ File browsing  
✅ Auto-reconnect  
✅ Settings persistence  
✅ Profile management

## ⚠️ What's Not Ready

❌ Actual file transfer  
❌ Drag-and-drop (needs setup)  
❌ Progress bars  
❌ Search/filter  
❌ Thumbnails

---

## 🆘 Need Help?

📖 Full docs: `README.md`  
🚀 Quick start: `QUICKSTART.md`  
🧪 Testing: `TESTING_GUIDE_v1.0.md`  
💻 Dev guide: `DEVELOPMENT_GUIDE.md`

---

## 🔑 Key Files

```
SyncStream/
├── config/
│   └── profiles.json          ← Edit your IPs here!
├── src/
│   ├── syncstream.py          ← Main entry point
│   ├── core/
│   │   ├── config_manager.py  ← Settings
│   │   ├── network_manager.py ← Connections
│   │   └── file_manager.py    ← Files
│   └── ui/
│       ├── theme_manager.py   ← Themes
│       └── main_window.py     ← UI
├── run.bat                    ← Launch on Windows
└── install.py                 ← Setup script
```

---

**Version:** 1.0.0 | **Released:** Oct 26, 2025
