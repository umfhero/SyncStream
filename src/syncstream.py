"""
SyncStream - Main Entry Point

Launch the SyncStream application.
"""

from ui.main_window import main
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))


if __name__ == "__main__":
    print("🚀 Starting SyncStream...")
    print("=" * 50)
    main()
