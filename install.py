"""
SyncStream - Installation Script

Run this script to install all dependencies and set up SyncStream.
"""

import subprocess
import sys
from pathlib import Path


def print_header(text):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def install_dependencies():
    """Install Python dependencies"""
    print_header("Installing Dependencies")

    requirements_file = Path(__file__).parent / "requirements.txt"

    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False

    print("📦 Installing packages from requirements.txt...")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(
                requirements_file)
        ])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_config():
    """Set up configuration files"""
    print_header("Setting Up Configuration")

    config_dir = Path(__file__).parent / "config"
    template_file = config_dir / "profiles.json.template"
    config_file = config_dir / "profiles.json"

    if config_file.exists():
        print("✅ profiles.json already exists")
        return True

    if not template_file.exists():
        print("❌ profiles.json.template not found!")
        return False

    print("📋 Copying profiles.json.template to profiles.json...")

    try:
        import shutil
        shutil.copy(template_file, config_file)
        print("✅ profiles.json created!")
        print("\n⚠️  IMPORTANT: Edit config/profiles.json with your Tailscale IPs!")
        print("   Run 'tailscale ip' to find your IP address")
        return True
    except Exception as e:
        print(f"❌ Failed to create profiles.json: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")

    app_data_dir = Path.home() / "AppData" / "Roaming" / "SyncStream"

    directories = [
        app_data_dir,
        app_data_dir / "Downloads",
        app_data_dir / "Thumbnails"
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

    return True


def main():
    """Main installation process"""
    print("\n" + "=" * 60)
    print("  🚀 SyncStream Installation")
    print("=" * 60)
    print("\nThis script will:")
    print("  1. Install Python dependencies")
    print("  2. Set up configuration files")
    print("  3. Create necessary directories")
    print("\n" + "=" * 60)

    input("\nPress Enter to continue...")

    # Run installation steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Setting up configuration", setup_config),
        ("Creating directories", create_directories)
    ]

    all_success = True
    for step_name, step_func in steps:
        if not step_func():
            all_success = False
            print(f"\n❌ {step_name} failed!")

    # Final message
    print("\n" + "=" * 60)
    if all_success:
        print("  ✅ Installation Complete!")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("  1. Edit config/profiles.json with your Tailscale IPs")
        print("  2. Run: python src/syncstream.py")
        print("  3. Start sharing files!")
        print("\n💡 Tip: Run 'tailscale ip' to find your Tailscale IP address")
    else:
        print("  ❌ Installation Failed")
        print("=" * 60)
        print("\nPlease fix the errors above and try again.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
