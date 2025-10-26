# SyncStream Quick Start Guide

Welcome to SyncStream! This guide will help you get up and running in minutes.

---

## 📋 Prerequisites

Before you begin, make sure you have:

1. **Python 3.8 or higher** installed

   - Check: `python --version`
   - Download from: https://python.org

2. **Tailscale** installed and running

   - Download from: https://tailscale.com/download
   - Make sure you're logged in and connected

3. **Git** (optional, for cloning the repository)

---

## 🚀 Installation Steps

### Step 1: Get SyncStream

**Option A: Clone with Git**

```bash
git clone https://github.com/umfhero/SyncStream.git
cd SyncStream
```

**Option B: Download ZIP**

1. Download the repository as ZIP
2. Extract to your preferred location
3. Open terminal/PowerShell in the SyncStream folder

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:

- CustomTkinter (modern UI)
- TkinterDnD2 (drag-and-drop)
- Pillow (image thumbnails)
- pystray (system tray)
- win10toast (notifications)
- and more...

### Step 3: Configure Your Profiles

#### Find Your Tailscale IP

**Windows (PowerShell):**

```powershell
tailscale ip
```

**Linux/Mac (Terminal):**

```bash
tailscale ip
```

You should see something like: `100.x.x.x`

#### Create profiles.json

1. Copy the template:

```bash
# Windows PowerShell
Copy-Item config\profiles.json.template config\profiles.json

# Linux/Mac
cp config/profiles.json.template config/profiles.json
```

2. Edit `config/profiles.json`:

```json
{
  "profiles": [
    {
      "name": "Your Name",
      "ip": "100.x.x.x",
      "port": 12345,
      "description": "Your computer"
    },
    {
      "name": "Friend's Name",
      "ip": "100.y.y.y",
      "port": 12345,
      "description": "Friend's computer"
    }
  ],
  "last_profile": null,
  "last_peer": null
}
```

3. **Important:** Replace:

   - `"Your Name"` with your actual name
   - `"100.x.x.x"` with your Tailscale IP
   - `"Friend's Name"` with your peer's name
   - `"100.y.y.y"` with your peer's Tailscale IP

4. Save the file

### Step 4: Run SyncStream

```bash
python src/syncstream.py
```

**Note:** First time running will create necessary folders in `%APPDATA%\SyncStream\`

---

## 🎮 First Use

### For Both Users:

1. **Launch SyncStream** on both computers
2. **Select your profile** from the "My Profile" dropdown
3. **Select your peer** from the "Connect to" dropdown
4. **Click "Connect"**
5. Wait for the LED to turn 🟢 **green**

### Sending Your First File:

**Method 1: Drag and Drop** (easiest)

- Simply drag any file into the SyncStream window
- Watch the progress bar
- File appears in gallery when complete

**Method 2: File Browser**

- Click the "Send File" button
- Browse and select your file
- Click "Open"

---

## 🎨 Customization

### Change Theme

- Click the theme toggle button (☀️/🌙)
- Switches between light and dark instantly

### Change Download Location

1. Settings → Download Location
2. Browse to your preferred folder
3. All future files will save there

### Enable Compression

1. Settings → Enable Compression
2. Files will be compressed before sending
3. Saves bandwidth and transfer time

---

## 🔧 Troubleshooting

### "Connection Failed"

- ✅ Check Tailscale is running: `tailscale status`
- ✅ Verify IP addresses are correct in profiles.json
- ✅ Make sure both users are on the same Tailscale network
- ✅ Check firewall isn't blocking port 12345

### "profiles.json not found"

- ❌ You forgot to copy profiles.json.template
- ✅ Run: `copy config\profiles.json.template config\profiles.json`
- ✅ Edit the new file with your details

### Can't Find Tailscale IP

- ✅ Run: `tailscale ip`
- ✅ Or check: https://login.tailscale.com/admin/machines
- ✅ Look for "100.x.x.x" format addresses

### File Not Sending

- ✅ Check connection LED is 🟢 green
- ✅ Click "Try Connecting" to retry
- ✅ Check file isn't locked by another program

---

## 🆘 Getting Help

- **Check TODO.md** for known issues
- **Review full README.md** for detailed features
- **Open an issue** on GitHub
- **Check Tailscale status**: `tailscale status`

---

## 🎉 You're All Set!

SyncStream is now ready to use. Happy file sharing!

**Pro Tips:**

- 💡 Minimize to system tray for quick access
- 💡 Use search to find files quickly
- 💡 Right-click files for more options
- 💡 SyncStream remembers your last connection

---

**Need more help?** Check the full documentation in the `docs/` folder.
