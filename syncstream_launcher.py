"""
SyncStream V2 - Launcher Script
This is the entry point for the PyInstaller executable
"""

import sys
import os
from pathlib import Path

# Get the directory where the executable is located
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        application_path = Path(sys._MEIPASS)
    else:
        application_path = Path(sys.executable).parent

    # Add to Python path
    sys.path.insert(0, str(application_path))
    sys.path.insert(0, str(application_path / 'src'))
else:
    # Running as script
    application_path = Path(__file__).parent
    sys.path.insert(0, str(application_path / 'src'))

print("🚀 Starting SyncStream V2.0.0...")
print("=" * 50)

# Now import and run
try:
    from ui.main_window import main
    main()
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Python Path: {sys.path}")
    print(f"Application Path: {application_path}")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)
