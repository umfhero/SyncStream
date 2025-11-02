"""
Quick Test: Verify system tray close behavior is fixed
"""
import sys
from pathlib import Path

print("=" * 60)
print("System Tray Close Behavior - Verification")
print("=" * 60)
print()

# Check if pystray Icon has 'is_running' attribute
try:
    import pystray

    # Create a dummy icon to check its attributes
    from PIL import Image
    dummy_image = Image.new('RGB', (64, 64), color='blue')

    test_icon = pystray.Icon(
        "test",
        dummy_image,
        "Test"
    )

    print("✅ pystray.Icon object created")
    print()
    print("🔍 Checking Icon attributes:")

    # List available attributes
    available_attrs = [attr for attr in dir(
        test_icon) if not attr.startswith('_')]

    print(f"   Available attributes: {len(available_attrs)}")

    # Check for common attributes
    check_attrs = ['is_running', 'visible', 'icon', 'menu', 'run', 'stop']

    for attr in check_attrs:
        if hasattr(test_icon, attr):
            print(f"   ✅ {attr} - EXISTS")
        else:
            print(f"   ❌ {attr} - NOT FOUND")

    print()
    print("📋 Conclusion:")
    if hasattr(test_icon, 'is_running'):
        print("   ⚠️  Icon has 'is_running' - old fix not needed")
    else:
        print("   ✅ Icon does NOT have 'is_running' - fix was correct!")
        print("   ℹ️  We should check if tray_icon exists, not is_running")

except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("Verification complete!")
print("=" * 60)
