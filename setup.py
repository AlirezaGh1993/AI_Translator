# setup.py

import subprocess
import sys
import os

def install_requirements():
    """Install packages from requirements.txt."""
    print("Installing required Python libraries...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("All libraries installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        print("Please try installing the libraries manually using: pip install -r requirements.txt")
        sys.exit(1)

def create_directories():
    """Create necessary directories for uploads and downloads."""
    print("Creating 'uploads' and 'downloads' directories...")
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    print("Directories are ready.")

if __name__ == "__main__":
    install_requirements()
    create_directories()
    print("\nSetup is complete!")
    print("You can now run the main application using: python app.py")
