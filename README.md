# 🎵 RetroSpotify

**RetroSpotify** is a terminal-based Spotify client built with Python and Textual. It brings your music to the command line with a retro aesthetic, ASCII album art, and native playback control.

![RetroSpotify Screenshot](./screenshots/image.png)

## ✨ Features

- **Terminal UI**: A beautiful, responsive TUI (Text User Interface) powered by Textual.
- **Integrated Spotify Connect Daemon**: Auto-provisions and manages a local `spotifyd` background daemon so you can stream live audio directly without having any other Spotify app open.
- **Responsive Layout**: Dynamically restructures grid panels (collapsing sidebars, volume, or album art) on resize events to fit narrow/short terminals without clipping or crashing.
- **Virtual Viewport Scrolling**: Efficiently slices lists of tracks and playlists, allowing you to scroll seamlessly through massive music libraries.
- **Liked Songs**: Automatic integration and pagination support to browse your full "Liked Songs" library instantly.
- **Search**: Search for tracks directly from the app.
- **Volume Control**: Adjust playback volume with keyboard shortcuts.
- **Mock Mode**: Works offline with synthetic chiptune audio for testing UI without Spotify credentials.

## 🚀 Installation

### Prerequisites

- Python 3.8+
- A Spotify Account (Premium recommended for full playback control).
- **Audio Player** (Optional, for local preview playback): `vlc` (recommended), `ffmpeg`, or `mpg123`.

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/vaibhav-rm/Spotify-textual.git
   cd Spotify-textual
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Spotify Configuration**:
   RetroSpotify features a built-in **Welcome & Authentication Screen** that guides you through connection:
   1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
   2. Create a new app. Set the **Redirect URI** to `http://127.0.0.1:8888/callback` and `http://127.0.0.1:8001/callback`.
   3. Launch RetroSpotify (`python main.py`).
   4. Select **Quick Login (PKCE)**. You will only need your **Client ID** (no client secret required!).
   5. The app will open your web browser to authorize access. Once approved, you will be automatically logged in and your details will be saved locally.

   *Alternatively, you can populate a `.env` file manually:*
   ```env
   SPOTIPY_CLIENT_ID=your_client_id_here
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

## 🎮 Usage

Run the application:

```bash
source venv/bin/activate
python main.py
```

### Controls

| Key | Action |
| :--- | :--- |
| `Space` / `s` | Play / Pause |
| `n` | Next Track |
| `p` | Previous Track |
| `S` | Toggle Shuffle |
| `R` | Toggle Repeat |
| `/` | Search Tracks |
| `+` / `-` | Volume Up / Down |
| `l` | Next Playlist |
| `h` | Previous Playlist |
| `a` | Go to Authentication Screen |
| `r` | Refresh Data |
| `q` | Quit |
| `?` | Help |

## 🖱️ Mouse & Scroll Support

- **Click** on a track to play it.
- **Click** on a playlist to select it.
- **Mouse Wheel Scroll** up/down on the Track list or Playlist sidebar to scroll through lists.

## 📦 Compiling to Standalone Executable

You can compile RetroSpotify into a single, standalone binary for easy distribution across Linux/macOS and Windows:

```bash
python compile.py
```

The compiled binary will be placed inside the `dist/` directory.

## 🛠️ Troubleshooting

- **"No active Spotify device"**: RetroSpotify will automatically download and start the `spotifyd` Connect daemon. If playback does not start, make sure to complete the "Local Connect setup" link from the Welcome Screen.
- **"No audio" (Mock Mode)**: Ensure you have `ffplay` (ffmpeg) installed to hear synthetic tones.
- **Album Art not showing**: Ensure `Pillow` is installed (`pip install Pillow`).

## 📜 License

MIT
