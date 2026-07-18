#!/usr/bin/env python3
import sys
import subprocess
import os
import shutil

def main():
    print("🚀 Starting RetroSpotify Compilation...")
    
    # 1. Install pyinstaller if not already installed
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed.")
    except ImportError:
        print("⏳ PyInstaller not found. Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 2. Determine OS-specific separator for PyInstaller --add-data
    # Windows uses ';', Linux/macOS uses ':'
    sep = ";" if os.name == "nt" else ":"
    
    # 3. Clean up previous build directories if they exist
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"🧹 Cleaning up existing {folder} directory...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"⚠️ Warning: Could not remove {folder}: {e}")
                
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name", "retrospotify",
        "--add-data", f"default_cover.png{sep}.",
        "main.py"
    ]
    
    print(f"📦 Running PyInstaller command: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\n🎉 Compilation finished successfully!")
        
        exe_name = "retrospotify.exe" if os.name == "nt" else "retrospotify"
        dist_path = os.path.join("dist", exe_name)
        if os.path.exists(dist_path):
            print(f"💾 Executable created at: {os.path.abspath(dist_path)}")
        else:
            print("⚠️ Warning: Compilation command completed but executable could not be found.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during compilation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
