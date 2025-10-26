"""
Build script for SyncStream V2
Creates executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Version info
VERSION = "2.0.0"
APP_NAME = "SyncStream"


def clean_build_dirs():
    """Remove old build directories"""
    print("🧹 Cleaning old build directories...")
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed {dir_name}/")

    # Clean .spec file
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"   Removed {spec_file}")


def check_dependencies():
    """Check if PyInstaller is installed"""
    print("\n📦 Checking dependencies...")
    try:
        import PyInstaller
        print(f"   ✅ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("   ❌ PyInstaller not found")
        print("   Installing PyInstaller...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("   ✅ PyInstaller installed")
        return True


def create_version_file():
    """Create version info file for Windows executable"""
    # Parse version to integers
    v_parts = VERSION.split('.')
    v_major, v_minor, v_patch = int(
        v_parts[0]), int(v_parts[1]), int(v_parts[2])

    version_info = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({v_major}, {v_minor}, {v_patch}, 0),
    prodvers=({v_major}, {v_minor}, {v_patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'SyncStream'),
        StringStruct(u'FileDescription', u'Peer-to-peer file sharing application'),
        StringStruct(u'FileVersion', u'{VERSION}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'Copyright © 2025'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{VERSION}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("   ✅ Created version_info.txt")


def build_executable():
    """Build the executable using PyInstaller"""
    print("\n🔨 Building executable...")

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',  # Single executable file
        # Show console for debugging (change to --windowed for release)
        '--console',
        '--icon', 'Assets/blackp2p.ico',
        '--add-data', 'Assets;Assets',
        '--add-data', 'config;config',
        '--paths', 'src',  # Add src to Python path
        '--hidden-import', 'ui',
        '--hidden-import', 'ui.main_window',
        '--hidden-import', 'ui.theme_manager',
        '--hidden-import', 'core',
        '--hidden-import', 'core.network_manager',
        '--hidden-import', 'core.file_manager',
        '--hidden-import', 'core.transfer_protocol',
        '--hidden-import', 'PIL._tkinter_finder',  # PIL/Pillow for thumbnails
        '--collect-all', 'customtkinter',  # Collect all CustomTkinter files
        '--collect-all', 'tkinterdnd2',  # Collect all drag-drop files
        '--clean',  # Clean cache before building
        '--noconfirm',  # Overwrite without asking
        'syncstream_launcher.py'  # Use launcher instead of src/syncstream.py
    ]

    # Add version info on Windows
    if sys.platform == 'win32' and os.path.exists('version_info.txt'):
        cmd.extend(['--version-file', 'version_info.txt'])

    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Build failed!")
        print(e.stderr)
        return False


def create_release_package():
    """Create release package with executable and necessary files"""
    print("\n📦 Creating release package...")

    release_dir = Path('release') / f'{APP_NAME}_V{VERSION}'
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy executable
    exe_name = f'{APP_NAME}.exe' if sys.platform == 'win32' else APP_NAME
    exe_path = Path('dist') / exe_name
    if exe_path.exists():
        shutil.copy2(exe_path, release_dir / exe_name)
        print(f"   ✅ Copied {exe_name}")
    else:
        print(f"   ❌ Executable not found: {exe_path}")
        return False

    # Copy assets
    if os.path.exists('Assets'):
        shutil.copytree('Assets', release_dir / 'Assets', dirs_exist_ok=True)
        print("   ✅ Copied Assets/")

    # Copy config
    if os.path.exists('config'):
        shutil.copytree('config', release_dir / 'config', dirs_exist_ok=True)
        print("   ✅ Copied config/")

    # Copy documentation
    files_to_copy = ['README.md', 'requirements.txt']
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, release_dir / file)
            print(f"   ✅ Copied {file}")

    # Create quick start guide
    quick_start = f"""
# {APP_NAME} V{VERSION} - Quick Start

## Installation
1. Extract this folder to your desired location
2. Run {exe_name}

## First Time Setup
1. Configure your profile in config/settings.json
2. Add peer profiles with Tailscale IPs
3. Start sharing files!

## Usage
- **Drag & Drop**: Drop files anywhere on the window
- **Gallery**: Click files to send to connected peer
- **Theme**: Click 🌓 button to toggle light/dark mode
- **Connect**: Select peer profile and click Connect

## Features
✨ Unlimited file sizes
🚀 Real-time progress tracking
🎨 Modern dual-theme UI
🔒 Secure Tailscale VPN connection
💾 Persistent file history
🖼️ Image thumbnails
🔍 Search and filter files

## Support
For issues or questions, check README.md

Enjoy sharing files! 🎉
"""

    with open(release_dir / 'QUICK_START.txt', 'w', encoding='utf-8') as f:
        f.write(quick_start)
    print("   ✅ Created QUICK_START.txt")

    # Create version file
    with open(release_dir / 'VERSION.txt', 'w') as f:
        f.write(f"{APP_NAME} Version {VERSION}\n")
        f.write(
            f"Build Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("   ✅ Created VERSION.txt")

    print(f"\n✅ Release package created: {release_dir}")
    return True


def main():
    """Main build process"""
    print("=" * 60)
    print(f"   Building {APP_NAME} V{VERSION}")
    print("=" * 60)

    # Check we're in the right directory
    if not os.path.exists('src/syncstream.py'):
        print("❌ Error: Must run from SyncStream root directory")
        sys.exit(1)

    # Clean old builds
    clean_build_dirs()

    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Create version info
    create_version_file()

    # Build executable
    if not build_executable():
        print("\n❌ Build failed!")
        sys.exit(1)

    # Create release package
    if not create_release_package():
        print("\n❌ Failed to create release package")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(f"   ✅ {APP_NAME} V{VERSION} built successfully!")
    print("=" * 60)
    print(f"\n📍 Release location: release/{APP_NAME}_V{VERSION}/")
    print(f"🚀 Ready to distribute!\n")


if __name__ == "__main__":
    main()
