# SyncStream v1.0 - Testing Guide

## 🧪 How to Test Version 1.0

This guide will help you test the current functionality of SyncStream v1.0.

---

## ✅ Prerequisites Checklist

Before testing, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] Tailscale installed and running
- [ ] Both test computers on the same Tailscale network
- [ ] Firewall allows port 12345
- [ ] Dependencies installed (`python install.py`)
- [ ] `config/profiles.json` configured with correct IPs

---

## 🚀 Installation Test

### Step 1: Run Installation

```bash
# Option A: Windows
setup.bat

# Option B: Manual
python install.py
```

**Expected Results:**

- ✅ All dependencies install successfully
- ✅ profiles.json created from template
- ✅ AppData directories created
- ✅ No error messages

### Step 2: Configure Profiles

1. Find your Tailscale IP:

   ```bash
   tailscale ip
   ```

2. Edit `config/profiles.json`:

   ```json
   {
     "profiles": [
       {
         "name": "Computer1",
         "ip": "100.x.x.x",
         "port": 12345
       },
       {
         "name": "Computer2",
         "ip": "100.y.y.y",
         "port": 12345
       }
     ]
   }
   ```

3. Save the file

**Expected Results:**

- ✅ File saved without errors
- ✅ JSON is valid
- ✅ IPs are in Tailscale range (100.x.x.x)

---

## 🎨 UI Test

### Launch Application

```bash
# Option A: Windows
run.bat

# Option B: Manual
python src/syncstream.py
```

**Expected Results:**

- ✅ Window opens with SyncStream title
- ✅ No Python errors in console
- ✅ UI elements are visible

### Visual Inspection

Check these UI elements exist:

- [ ] Connection LED (red circle) in top left
- [ ] "My Profile:" dropdown
- [ ] "Connect to:" dropdown
- [ ] "Connect" button
- [ ] Theme toggle button (☀️ or 🌙)
- [ ] Drag-drop zone with "Drag & Drop Files Here"
- [ ] "Browse Files" button
- [ ] "File Gallery" section
- [ ] Search bar with 🔍 icon
- [ ] "Filter: All" button
- [ ] Status bar at bottom showing "Ready"

**Expected Results:**

- ✅ All elements visible
- ✅ Text is readable
- ✅ Layout looks clean
- ✅ No overlapping elements

---

## 🎨 Theme Test

### Test Theme Toggle

1. Note current theme (light or dark)
2. Click theme toggle button (☀️/🌙)
3. Observe theme change
4. Click again to toggle back
5. Close and reopen app

**Expected Results:**

- ✅ Theme toggles instantly
- ✅ All elements update colors
- ✅ Button icon changes
- ✅ Status bar shows "Theme: Light" or "Theme: Dark"
- ✅ Theme persists after restart

### Light Theme Check

- [ ] Background is light/white
- [ ] Text is dark and readable
- [ ] Buttons are blue
- [ ] LED is visible

### Dark Theme Check

- [ ] Background is dark/charcoal
- [ ] Text is light and readable
- [ ] Buttons are blue
- [ ] LED is visible

---

## 🌐 Connection Test

### Test Setup

- Need TWO computers on same Tailscale network
- Both should have SyncStream installed
- Both should have correct profiles.json

### Computer 1: Start Server

1. Launch SyncStream
2. Select your profile from "My Profile:"
3. Select Computer 2 from "Connect to:"
4. Click "Connect"
5. Watch the LED

**Expected Results:**

- ✅ LED turns orange (connecting)
- ✅ Status shows "Connecting to [peer]..."
- ✅ After few seconds, LED turns green
- ✅ Status shows "Connected to [IP]"
- ✅ "Connect" button changes to "Disconnect"
- ✅ Console shows: "✅ Connected to [IP]"

### Computer 2: Connect as Client

1. Launch SyncStream
2. Select your profile
3. Select Computer 1 from "Connect to:"
4. Click "Connect"

**Expected Results:**

- ✅ Same as above
- ✅ Both computers show green LED
- ✅ Both show "Connected" status

### Test Disconnect

1. On either computer, click "Disconnect"
2. Observe LED and status

**Expected Results:**

- ✅ LED turns red immediately
- ✅ Status shows "Disconnected"
- ✅ Button changes back to "Connect"
- ✅ Other computer also shows disconnected

---

## 🔄 Auto-Reconnect Test

### Test Auto-Reconnect

1. Establish connection (green LED)
2. On Computer 1, close SyncStream
3. On Computer 2, watch the reconnection attempts
4. Wait 30 seconds
5. Relaunch Computer 1's SyncStream
6. Connect again

**Expected Results:**

- ✅ Computer 2 shows "Disconnected" when Computer 1 closes
- ✅ Status shows reconnection attempts
- ✅ "Try Again" button appears
- ✅ Reconnects when Computer 1 comes back online

### Test Manual Retry

1. With connection disconnected
2. Click "Try Again" button
3. Observe connection attempt

**Expected Results:**

- ✅ LED turns orange
- ✅ Attempts to connect
- ✅ Either succeeds (green) or fails (red)

---

## 📁 File Browser Test

### Test File Selection

1. Ensure connected (green LED)
2. Click "Browse Files" button
3. Select a file (any file)
4. Click "Open"

**Expected Results:**

- ✅ File dialog opens
- ✅ Can navigate folders
- ✅ Can select file
- ✅ Status shows "Sending: [filename]"
- ✅ Console shows file info
- ⚠️ **Note:** File won't actually transfer yet (v1.0 limitation)

---

## 🖼️ File Gallery Test

### Visual Check

1. Look at the "File Gallery" section
2. If history exists, files should appear as cards
3. Each card should show:
   - [ ] Icon (emoji)
   - [ ] Filename
   - [ ] File size
   - [ ] Status (if applicable)

**Expected Results:**

- ✅ Cards display correctly
- ✅ Grid layout (4 columns)
- ✅ Scrollable if many files

---

## 🪟 Window Test

### Test Resizing

1. Drag window edges to resize
2. Make it smaller
3. Make it larger
4. Close and reopen

**Expected Results:**

- ✅ Window resizes smoothly
- ✅ Elements scale appropriately
- ✅ No elements get cut off
- ✅ Size persists after restart

### Test Window Position

1. Move window to different position
2. Close application
3. Reopen application

**Expected Results:**

- ✅ Window opens in same position
- ✅ Same size as before

---

## ❌ Error Handling Test

### Test Invalid Connection

1. In profiles.json, temporarily change an IP to invalid (e.g., "999.999.999.999")
2. Try to connect
3. Observe behavior

**Expected Results:**

- ✅ Shows error in console
- ✅ LED stays red or returns to red
- ✅ Doesn't crash

### Test Missing Profile

1. Delete profiles.json
2. Launch SyncStream

**Expected Results:**

- ✅ Warning message in console
- ✅ App still opens
- ✅ Profile dropdowns are empty or show error
- ✅ Doesn't crash

---

## 🐛 Known Issues to Verify

Confirm these known limitations exist:

- [ ] Drag-and-drop shows error if tkinterdnd2 not installed
- [ ] Files selected don't actually transfer end-to-end
- [ ] Search box doesn't filter results
- [ ] Filter button doesn't change anything
- [ ] No progress bars appear during "send"
- [ ] No thumbnails appear (only emojis)

**This is expected behavior in v1.0!**

---

## 📊 Test Results Template

```
=== SyncStream v1.0 Test Report ===
Date: _______________
Tester: _______________
OS: _______________
Python Version: _______________

INSTALLATION:           [ ] Pass  [ ] Fail
UI DISPLAY:             [ ] Pass  [ ] Fail
THEME TOGGLE:           [ ] Pass  [ ] Fail
CONNECTION:             [ ] Pass  [ ] Fail
AUTO-RECONNECT:         [ ] Pass  [ ] Fail
FILE BROWSER:           [ ] Pass  [ ] Fail
WINDOW RESIZE:          [ ] Pass  [ ] Fail
PERSISTENCE:            [ ] Pass  [ ] Fail

NOTES:
________________________________
________________________________
________________________________

BUGS FOUND:
________________________________
________________________________
________________________________
```

---

## ✅ Success Criteria

For v1.0 to pass testing:

### Must Work:

- ✅ Application launches without errors
- ✅ UI is visible and usable
- ✅ Theme toggle works
- ✅ Can select profiles
- ✅ Can establish TCP connection
- ✅ LED shows correct status
- ✅ Settings persist

### Can Be Broken (Expected):

- ⚠️ Actual file transfer
- ⚠️ Drag-and-drop
- ⚠️ Progress bars
- ⚠️ Search/filter
- ⚠️ Thumbnails

---

## 🚀 Next Steps After Testing

If v1.0 tests pass:

1. Document any bugs found
2. Move to v1.1 development
3. Focus on completing file transfer protocol
4. Wire up all the "not yet functional" features

If tests fail:

1. Document exact failure
2. Check Python version
3. Check dependency versions
4. Review error messages
5. Fix critical bugs before v1.1

---

## 📞 Reporting Issues

When reporting bugs, include:

- Python version (`python --version`)
- OS version
- Tailscale version (`tailscale version`)
- Exact error message
- Steps to reproduce
- Screenshots if applicable

---

**Happy Testing! 🧪**
