import shutil
import requests
import sys
import os

def check_dependencies():
    print("Checking dependencies...")
    tools = ['ffplay', 'mpg123', 'play', 'vlc']
    found = []
    for tool in tools:
        path = shutil.which(tool)
        if path:
            print(f"✅ Found {tool} at {path}")
            found.append(tool)
        else:
            print(f"❌ {tool} not found")
    return found

def check_url(url):
    print(f"Checking URL: {url}")
    try:
        response = requests.head(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ URL is accessible")
            return True
        else:
            print("❌ URL returned non-200 status")
            return False
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

if __name__ == "__main__":
    found_tools = check_dependencies()
    if not found_tools:
        print("⚠️ No audio players found! This is likely why you can't hear anything.")
        print("Please install ffmpeg (which provides ffplay) or mpg123.")
    
    url = "https://www.soundjay.com/misc/sounds/fail-buzzer-02.wav"
    check_url(url)
