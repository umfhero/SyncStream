#!/usr/bin/env python3
"""
SyncStream - First Run Checker

Checks if everything is set up correctly before running SyncStream.
"""

import sys
from pathlib import Path
import json


def check_python_version():
    """Check if Python version is 3.8+"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} - Need 3.8+")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    required = [
        'customtkinter',
        'PIL',  # Pillow
    ]

    recommended = [
        'tkinterdnd2',  # Drag & drop
        'pystray',      # System tray icon
        'win10toast',   # Windows notifications
    ]

    all_ok = True

    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - REQUIRED")
            all_ok = False

    for package in recommended:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            feature = {
                'tkinterdnd2': 'drag-and-drop',
                'pystray': 'system tray icon',
                'win10toast': 'notifications'
            }.get(package, 'feature')
            print(f"   ⚠️  {package} - recommended ({feature} disabled)")

    return all_ok


def check_profiles():
    """Check if profiles.json exists and is valid"""
    print("\n📋 Checking profiles configuration...")

    config_dir = Path(__file__).parent / "config"
    profiles_file = config_dir / "profiles.json"

    if not profiles_file.exists():
        print(f"   ❌ profiles.json not found!")
        print(f"      Expected: {profiles_file}")
        print(f"      Run: copy config\\profiles.json.template config\\profiles.json")
        return False

    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)

        # Check for new format (my_profile + peer_profiles)
        my_profile = data.get('my_profile')
        peer_profiles = data.get('peer_profiles', [])

        # Also support old format (profiles array) for backward compatibility
        old_profiles = data.get('profiles', [])

        if my_profile or old_profiles:
            # Show my profile
            if my_profile:
                my_name = my_profile.get('name', 'Unknown')
                my_ip = my_profile.get('ip', '')
                print(f"   ✅ My Profile: {my_name}")
                if '100.' in my_ip:
                    print(f"      • IP: {my_ip}")
                else:
                    print(f"      ⚠️  IP: {my_ip} - Not a Tailscale IP?")

            # Show peer profiles
            if peer_profiles:
                print(f"   ✅ Found {len(peer_profiles)} peer profile(s)")
                for profile in peer_profiles:
                    ip = profile.get('ip', '')
                    name = profile.get('name', '')
                    if '100.' in ip:
                        print(f"      • {name}: {ip}")
                    else:
                        print(f"      ⚠️  {name}: {ip} - Not a Tailscale IP?")
            elif old_profiles:
                # Old format
                print(f"   ✅ Found {len(old_profiles)} profile(s)")
                for profile in old_profiles:
                    ip = profile.get('ip', '')
                    name = profile.get('name', '')
                    if '100.' in ip:
                        print(f"      • {name}: {ip}")
                    else:
                        print(f"      ⚠️  {name}: {ip} - Not a Tailscale IP?")
            else:
                print(f"   ⚠️  No peer profiles defined (you can still use SyncStream)")

            return True
        else:
            print("   ❌ No profiles defined in profiles.json")
            return False

    except json.JSONDecodeError:
        print("   ❌ profiles.json has invalid JSON")
        return False
    except Exception as e:
        print(f"   ❌ Error reading profiles.json: {e}")
        return False


def check_tailscale():
    """Check if Tailscale is installed"""
    print("\n🌐 Checking Tailscale...")

    import subprocess

    try:
        result = subprocess.run(
            ['tailscale', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print("   ✅ Tailscale is running")
            return True
        else:
            print("   ⚠️  Tailscale command found but not running")
            return False

    except FileNotFoundError:
        print("   ❌ Tailscale not installed or not in PATH")
        print("      Download from: https://tailscale.com/download")
        return False
    except subprocess.TimeoutExpired:
        print("   ⚠️  Tailscale command timed out")
        return False
    except Exception as e:
        print(f"   ⚠️  Could not check Tailscale: {e}")
        return False


def check_directories():
    """Check if app directories exist"""
    print("\n📁 Checking directories...")

    app_data = Path.home() / "AppData" / "Roaming" / "SyncStream"

    directories = [
        app_data,
        app_data / "Downloads",
        app_data / "Thumbnails"
    ]

    all_exist = True
    for directory in directories:
        if directory.exists():
            print(f"   ✅ {directory.name}")
        else:
            print(f"   ⚠️  {directory.name} - will be created")
            all_exist = False

    return all_exist


def main():
    """Run all checks"""
    print("=" * 60)
    print("  🔍 SyncStream Pre-Flight Check")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Profiles Configuration", check_profiles),
        ("Tailscale", check_tailscale),
        ("Directories", check_directories)
    ]

    results = {}
    for name, check_func in checks:
        results[name] = check_func()

    # Summary
    print("\n" + "=" * 60)
    print("  📊 Summary")
    print("=" * 60)

    critical_passed = results["Python Version"] and results["Dependencies"] and results["Profiles Configuration"]

    if critical_passed:
        print("\n✅ READY TO RUN!")
        print("\nStart SyncStream with:")
        print("  python src/syncstream.py")
        print("  or run.bat (Windows)")
    else:
        print("\n❌ NOT READY - Fix the errors above")

        if not results["Dependencies"]:
            print("\n📦 To install dependencies:")
            print("  python install.py")
            print("  or pip install -r requirements.txt")

        if not results["Profiles Configuration"]:
            print("\n📋 To set up profiles:")
            print("  1. copy config\\profiles.json.template config\\profiles.json")
            print("  2. Edit config\\profiles.json with your Tailscale IPs")
            print("  3. Run 'tailscale ip' to find your IP")

    if not results["Tailscale"]:
        print("\n🌐 Tailscale Issues:")
        print("  • Install from: https://tailscale.com/download")
        print("  • Make sure it's running")
        print("  • Run 'tailscale status' to check")

    print("\n" + "=" * 60)

    return 0 if critical_passed else 1


if __name__ == "__main__":
    sys.exit(main())
