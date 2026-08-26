# 🎵 RetroSpotify

**RetroSpotify** is a premium, feature-rich terminal-based Spotify client built with Python and Textual. It brings your music to the command line with a retro aesthetic, animated ASCII equalizer, dynamic colored borders, and native/Connect audio controls.

![RetroSpotify Screenshot](./screenshots/image.png)

## ✨ Features

- **Responsive Terminal UI**: A gorgeous retro-themed TUI (Text User Interface) powered by Textual. Panels auto-collapse (hiding sidebar, volume, or cover art) to fit narrow/short terminals gracefully without clipping or crashing.
- **Dynamic Active Border Titles**: Panels like Library, Tracks, Controls, and Now Playing feature custom borders that highlight in bold Spotify-green (`#1ed760`) when focused, and dim to subtle grey when inactive.
- **Decoupled Playback & Navigation**: Browse and search other playlists, album tracks, or queues completely uninterrupted without stopping the active playback session.
- **Track-Specific Playback Context**: Smart navigation knows your active queue context. Using `Next Track` or `Previous Track` hotkeys moves correctly within the playing playlist, rather than the list you are currently browsing.
- **Dynamic Play/Pause Indicators**: The tracks panel shows active playback symbols (`🔊` for playing, `⏸` for paused) beside the playing track on all screens.
- **Vertical ASCII Equalizer**: A beautiful, 6-channel animated vertical ASCII equalizer in the Now Playing panel that dances to your tunes when active and rests cleanly when paused.
- **Integrated Spotify Connect Daemon (`spotifyd`)**: Automatically downloads, provisions, and runs a background `spotifyd` instance. Stream full high-bitrate audio directly on your machine without needing the official Spotify desktop client open.
- **Interactive Mouse Controls**: Click on tracks or playlists to play and select them. Click the Volume slider directly to snap to 10% volume increments, or click the `SHUF` / `REP` buttons to toggle playback states.
- **Mock Mode**: Offline test mode with synthetic audio generation to demo and test UI layouts without a Spotify account.

---

## 🚀 Installation & Setup

### Prerequisites

1. **Python 3.8+**
2. **A Spotify Premium Account** (Required for Spotify Connect playback control).
3. **System Audio Engine** (Optional, for local preview playback fallback): `ffmpeg` / `ffplay` or `vlc` installed on your system path.

### 1. Clone & Set Up Virtual Environment

Clone the repository and set up a Python virtual environment to avoid dependency conflicts:

```bash
# Clone the repository
git clone https://github.com/vaibhav-rm/Spotify-textual.git
cd Spotify-textual

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 2. Configure Spotify API Application

RetroSpotify communicates with Spotify securely using the Web API. To authorize the client:

1. Visit the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in.
2. Click **Create App**. Name the app `RetroSpotify`.
3. **CRITICAL Redirect URI**: In the Redirect URIs field, add:
   `http://127.0.0.1:8888/callback`
   *(Ensure this matches exactly, including port and path. This allows the local authentication listener to capture your token).*
4. Save the app, go to Settings, and copy your **Client ID**.

### 3. Launch and Log In

Run the application:

```bash
python main.py
```

The application will launch directly into the **Welcome & Authentication Screen**. Follow these simple login steps:

#### Method A: Quick Login (PKCE) - *Recommended*
1. Press the **Quick Login (PKCE)** button in the UI.
2. Enter your Spotify **Client ID** when prompted.
3. RetroSpotify will launch a secure background server and open your web browser.
4. Log in to Spotify in your browser and authorize the application.
5. Upon authorization, the app will log in automatically, spin up the local `spotifyd` daemon, and cache your token for future sessions.

#### Method B: Configuration File (Optional)
If you prefer not to enter details in the TUI, create a `.env` file in the root of the project:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

---

## 🎮 Keyboard & Mouse Controls

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Space` / `s` | Toggle Play / Pause of active track |
| `n` | Next Track (in active playback context) |
| `p` | Previous Track (in active playback context) |
| `S` | Toggle Shuffle |
| `R` | Cycle Repeat (Off ➔ Repeat Track ➔ Repeat Playlist) |
| `/` | Open Search Bar |
| `Esc` | Close Search Bar / Clear Query |
| `+` / `-` | Increase / Decrease Volume by 10% |
| `l` / `h` | Move Down / Up in Playlist sidebar |
| `b` | Toggle Library Sidebar visibility |
| `d` | Open Spotify Connect Devices menu |
| `r` | Refresh playlists and tracks |
| `?` | Open Help Menu |
| `q` | Quit client safely |

### Mouse Actions

- **Double Click** or **Press Enter** on a track to start playback.
- **Scroll Wheel** to scroll through tracks or playlist lists.
- **Click** volume progress bar to adjust volume to that level.
- **Click** the `SHUF` or `REP` indicators on the control bar to toggle shuffle or cycle repeat modes.

---

## 🛠️ Standalone Compilation

You can compile RetroSpotify into a single executable binary that runs independently without requiring Python:

```bash
python compile.py
```

The compiled standalone executable will be located in the `dist/` directory.

---

## 📜 License

MIT License. Open source for terminal lovers.
