"""
Test System Tray Icon functionality
"""
import sys
from pathlib import Path

# Test imports
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_icon_creation():
    """Test creating a basic system tray icon"""
    try:
        # Create a simple icon
        icon_path = Path(__file__).parent / "Assets" / "blackp2p.ico"

        if icon_path.exists():
            icon_image = Image.open(icon_path)
            print(f"✅ Loaded icon from: {icon_path}")
        else:
            # Create a simple colored square
            icon_image = Image.new('RGB', (64, 64), color='blue')
            print("⚠️  Icon file not found, using fallback")

        # Create menu
        menu = pystray.Menu(
            item('Test Item', lambda: print("Clicked!")),
        )

        # Create icon
        tray_icon = pystray.Icon(
            "TestIcon",
            icon_image,
            "Test System Tray",
            menu
        )

        print("✅ System tray icon created successfully")
        print("   Name: TestIcon")
        print("   Menu items: 1")

        return True

    except Exception as e:
        print(f"❌ Failed to create system tray icon: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing System Tray Icon Creation")
    print("=" * 60)
    print()

    success = test_icon_creation()

    print()
    print("=" * 60)
    if success:
        print("✅ System Tray Test PASSED")
        print()
        print("The system tray icon can be created successfully.")
        print("If it's not showing in SyncStream, check the logs when")
        print("starting the app for any error messages.")
    else:
        print("❌ System Tray Test FAILED")
        print()
        print("There's an issue with system tray icon creation.")
    print("=" * 60)
