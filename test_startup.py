"""
Test script to verify Windows startup registry functionality
"""
from core.config_manager import ConfigManager
import winreg
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_startup_status():
    """Check if SyncStream is currently in Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             key_path, 0, winreg.KEY_READ)

        try:
            value, _ = winreg.QueryValueEx(key, "SyncStream")
            print(f"✅ SyncStream IS in Windows startup:")
            print(f"   Path: {value}")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            print("❌ SyncStream is NOT in Windows startup")
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"⚠️  Error checking startup status: {e}")
        return False


def main():
    print("=" * 60)
    print("Testing Windows Startup Functionality")
    print("=" * 60)
    print()

    # Check current status
    print("1. Current Status:")
    is_enabled = check_startup_status()
    print()

    # Load config
    print("2. Loading Config Manager...")
    config = ConfigManager()
    print(
        f"   Config setting run_on_startup: {config.settings.run_on_startup}")
    print()

    # Test enabling
    print("3. Testing ENABLE startup...")
    try:
        config.set_run_on_startup(True)
        check_startup_status()
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()

    # Test disabling
    print("4. Testing DISABLE startup...")
    try:
        config.set_run_on_startup(False)
        check_startup_status()
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()

    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
