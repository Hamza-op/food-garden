import os
import subprocess
import sys

def install_requirements():
    print("Checking/Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build():
    print("Building Food Garden Executable...")
    
    # Define the PyInstaller command using python module invocation
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--clean",
        "--name", "Food Garden",
        "--add-data", "ui/styles.qss;ui",
        "--add-data", "ui/styles_light.qss;ui",
        "--add-data", "aura_pos.db;initial_data.db", # Bundle as a renamed file at root of temp dir
        "main.py"
    ]
    
    # Check if assets exist and are not empty
    if os.path.exists("assets") and os.listdir("assets"):
        cmd.extend(["--add-data", "assets;assets"])
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print("\n" + "="*50)
    print("BUILD SUCCESSFUL!")
    print("="*50)
    print(f"Your executable is located at: {os.path.abspath('dist/Food Garden.exe')}")

if __name__ == "__main__":
    try:
        install_requirements()
        build()
    except Exception as e:
        print(f"\nBUILD FAILED: {e}")
        input("Press Enter to exit...")
