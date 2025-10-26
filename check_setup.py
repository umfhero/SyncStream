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

    optional = [
        'tkinterdnd2',
    ]

    all_ok = True

    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - REQUIRED")
            all_ok = False

    for package in optional:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ⚠️  {package} - optional (drag-and-drop disabled)")

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

        profiles = data.get('profiles', [])
        if not profiles:
            print("   ❌ No profiles defined in profiles.json")
            return False

        print(f"   ✅ Found {len(profiles)} profile(s)")

        # Check if IPs look like examples
        for profile in profiles:
            ip = profile.get('ip', '')
            name = profile.get('name', '')
            if '100.' in ip:
                print(f"      • {name}: {ip}")
            else:
                print(f"      ⚠️  {name}: {ip} - Not a Tailscale IP?")

        return True

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
