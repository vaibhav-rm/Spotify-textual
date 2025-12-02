import asyncio
import os
import random
import time
import subprocess
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from aiohttp import web
import requests

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Static, Footer, Input, Header, Button, Label, ProgressBar as TextualProgressBar
from textual import events, log
from textual.reactive import reactive
from textual.geometry import Size

# Optional Spotify imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    spotipy = None
    SpotifyOAuth = None

load_dotenv()

ASCII_LOGO = r"""
  _____             _   _ _   _  _   _     _
 / ____|           | | (_) | | || \ | |   | |
| (___   ___  _ __ | |_ _| |_| ||  \| | __| | ___ _ __
 \___ \ / _ \| '_ \| __| | __| || . ` |/ _` |/ _ \ '__|
 ____) | (_) | | | | |_| | |_| || |\  | (_| |  __/ |
|_____/ \___/|_| |_|\__|_|\__|_||_| \_|\__,_|\___|_|
"""

# ASCII Art Generator for album art
def generate_ascii_art_from_image(img, width: int = 40, height: int = 20) -> str:
    """Generate ASCII art from PIL Image object"""
    # Convert to grayscale
    img = img.convert('L')
    
    # Resize
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # ASCII characters from dark to light (for dark terminal)
    # 0 (Black) -> Background (Dark) -> " " or "."
    # 255 (White) -> Foreground (Bright) -> "@" or "#"
    ascii_chars = " .:-=+*#%@"
    
    ascii_art = []
    for y in range(height):
        line = ""
        for x in range(width):
            pixel = img.getpixel((x, y))
            # Map pixel value (0-255) to ASCII character
            char_index = int((pixel / 255) * (len(ascii_chars) - 1))
            line += ascii_chars[char_index]
        ascii_art.append(line)
    
    return "\n".join(ascii_art)

def generate_ascii_art_from_url(image_url: str, width: int = 40, height: int = 20) -> str:
    """Generate ASCII art from image URL"""
    try:
        from PIL import Image
        import requests
        from io import BytesIO
        
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        
        return generate_ascii_art_from_image(img, width, height)
    except Exception as e:
        # Fallback ASCII art
        return generate_fallback_art()

def generate_fallback_art() -> str:
    """Generate fallback ASCII art from local file or text"""
    try:
        from PIL import Image
        # Try to load default_cover.png
        if os.path.exists("default_cover.png"):
            img = Image.open("default_cover.png")
            return generate_ascii_art_from_image(img, width=40, height=20)
    except Exception:
        pass

    art = [
        "    .-=-=-=-=-=-=-=-=-=-=-=-=-=-.",
        "   / .-=-=-=-=-=-=-=-=-=-=-=-=-. \\",
        "  / / .-=-=-=-=-=-=-=-=-=-=-=-. \\ \\",
        " / / / .-=-=-=-=-=-=-=-=-=-=-. \\ \\ \\",
        "| | | |                     | | | |",
        "| | | |       MUSIC         | | | |",
        "| | | |                     | | | |",
        " \\ \\ \\ \\ .-=-=-=-=-=-=-=-=-. / / /",
        "  \\ \\ \\ .-=-=-=-=-=-=-=-=-=-. / /",
        "   \\ \\ .-=-=-=-=-=-=-=-=-=-=-. /",
        "    '-=-=-=-=-=-=-=-=-=-=-=-=-=-'"
    ]
    return "\n".join(art)
    """Generate fallback ASCII art when image processing fails"""
    art = [
        "    .-=-=-=-=-=-=-=-=-=-=-=-=-=-.",
        "   / .-=-=-=-=-=-=-=-=-=-=-=-=-. \\",
        "  / / .-=-=-=-=-=-=-=-=-=-=-=-. \\ \\",
        " / / / .-=-=-=-=-=-=-=-=-=-=-. \\ \\ \\",
        "| | | |                     | | | |",
        "| | | |       MUSIC         | | | |",
        "| | | |                     | | | |",
        " \\ \\ \\ \\ .-=-=-=-=-=-=-=-=-. / / /",
        "  \\ \\ \\ .-=-=-=-=-=-=-=-=-=-. / /",
        "   \\ \\ .-=-=-=-=-=-=-=-=-=-=-. /",
        "    '-=-=-=-=-=-=-=-=-=-=-=-=-=-'"
    ]
    return "\n".join(art)

@dataclass
class Track:
    name: str
    artists: List[str]
    duration: int
    id: Optional[str] = None
    album_art_url: Optional[str] = None
    preview_url: Optional[str] = None

# Mock fallback data with preview URLs
MOCK_PLAYLISTS = [
    {
        "name": "Made For You", 
        "id": None, 
        "items": [
            Track("Your Top Song", ["Various Artists"], 180, 
                  album_art_url="https://picsum.photos/300/300?random=1",
                  preview_url="sine=f=440:d=30"),
            Track("Winter 2022", ["Seasonal Mix"], 240,
                  album_art_url="https://picsum.photos/300/300?random=2",
                  preview_url="sine=f=523:d=30"),
            Track("孤独の発明", ["Tokyo Dream"], 210,
                  album_art_url="https://picsum.photos/300/300?random=3",
                  preview_url="sine=f=659:d=30")
        ]
    },
    {
        "name": "Chill Vibes", 
        "id": None, 
        "items": [
            Track("a sad yeehaw", ["Cowboy Blues"], 195,
                  album_art_url="https://picsum.photos/300/300?random=4",
                  preview_url="sine=f=330:d=30"),
            Track("Disc 1", ["Ambient Collective"], 220,
                  album_art_url="https://picsum.photos/300/300?random=5",
                  preview_url="sine=f=392:d=30"),
            Track("Disc 2", ["Ambient Collective"], 215,
                  album_art_url="https://picsum.photos/300/300?random=6",
                  preview_url="sine=f=494:d=30")
        ]
    },
]

# Music Player using system audio
class MusicPlayer:
    def __init__(self):
        self.process = None
        self.is_playing = False
        self.current_track = None
        self.volume = 100  # 0-100
        
    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        # If playing, we would ideally adjust volume, but for subprocess 
        # we might need to restart. For now, just save for next track.
        
    def play(self, preview_url: str) -> bool:
        """Play audio from URL using system player"""
        try:
            self.stop()  # Stop any currently playing audio
            
            # Calculate volume parameters
            # ffplay: 0-100
            # cvlc: 0-512 (approx 2.56 * percent) or --gain 0-2.0
            # mpg123: -f <factor> (32768 is max)
            
            ffplay_vol = str(self.volume)
            # vlc volume: 0-256 is 100%. Let's map 0-100 to 0-256
            vlc_vol = str(int(self.volume * 2.56))
            
            # Check for synthetic audio
            if preview_url.startswith("sine="):
                # Use ffplay with lavfi filter
                cmd = ['ffplay', '-f', 'lavfi', '-i', preview_url, '-autoexit', '-nodisp', '-loglevel', 'quiet', '-volume', ffplay_vol]
                try:
                    self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.is_playing = True
                    return True
                except FileNotFoundError:
                    # Fallback to other players if ffplay missing (unlikely if we are here)
                    pass

            # Try different methods to play audio
            players = [
                ['cvlc', '--play-and-exit', '--no-video', '--volume', vlc_vol, preview_url], # VLC
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-volume', ffplay_vol, preview_url],  # ffmpeg
                ['mpg123', '-q', preview_url],  # mpg123 (no easy volume flag without scale factor math)
                ['play', '-q', '-v', str(self.volume/100.0), preview_url],    # sox
            ]
            
            for player_cmd in players:
                try:
                    self.process = subprocess.Popen(
                        player_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    self.is_playing = True
                    return True
                except FileNotFoundError:
                    continue
            
            # If no audio player found, simulate playback
            self.is_playing = True
            return False
            
        except Exception as e:
            print(f"Audio playback error: {e}")
            self.is_playing = False
            return False
    
    def stop(self):
        """Stop currently playing audio"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        self.is_playing = False
        self.process = None
    
    def toggle(self, preview_url: str) -> bool:
        """Toggle play/pause"""
        if self.is_playing:
            self.stop()
            return False
        else:
            return self.play(preview_url)

# Visual helpers
def gradient_color(pos: float, start=(0, 255, 100), end=(100, 200, 255)) -> str:
    r = int(start[0] + (end[0] - start[0]) * pos)
    g = int(start[1] + (end[1] - start[1]) * pos)
    b = int(start[2] + (end[2] - start[2]) * pos)
    return f"#{r:02x}{g:02x}{b:02x}"

def format_duration(seconds: int) -> str:
    """Convert seconds to MM:SS format"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

# ASCII Album Art Widget
class AlbumArt(Static):
    art_content = reactive("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.styles.height = "auto"
        self.styles.width = "auto"
        
    def set_art_from_url(self, url: str) -> None:
        """Set album art from URL"""
        try:
            # Use 40x20 for better aspect ratio (characters are usually 1:2)
            ascii_art = generate_ascii_art_from_url(url, width=40, height=20)
            self.art_content = ascii_art
        except Exception as e:
            self.art_content = generate_fallback_art()
        
    def set_fallback_art(self) -> None:
        """Set fallback album art"""
        self.art_content = generate_fallback_art()
        
    def render(self) -> str:
        if not self.art_content:
            return "[dim]No album art[/dim]"
            
        art_lines = self.art_content.splitlines()
        colored_art = []
        for i, line in enumerate(art_lines):
            color = gradient_color(i / len(art_lines))
            colored_art.append(f"[{color}]{line}[/{color}]")
        return "\n".join(colored_art)

# Enhanced Progress Bar
class MusicProgressBar(Static):
    progress = reactive(0.0)
    duration = reactive(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.playing = False
        self.start_time = 0
        self.current_position = 0
        
    def on_mount(self) -> None:
        self.set_interval(0.2, self.update_progress)
        
    def update_progress(self) -> None:
        if self.playing and self.duration > 0:
            elapsed = time.time() - self.start_time
            self.current_position = min(self.duration, elapsed)
            self.progress = self.current_position / self.duration
            self.refresh()
            
    def play(self, duration: int) -> None:
        self.duration = duration
        self.start_time = time.time() - self.current_position
        self.playing = True
        self.refresh()
        
    def pause(self) -> None:
        self.playing = False
        
    def stop(self) -> None:
        self.playing = False
        self.current_position = 0
        self.progress = 0
        self.refresh()
        
    def render(self) -> str:
        if self.duration == 0:
            return "[dim]--:-- / --:--[/dim]"
            
        width = max(20, (self.size.width - 10) if self.size else 50)
        filled_width = int(self.progress * width)
        
        # Create progress bar with different characters for visual effect
        bar = "█" * filled_width + "░" * (width - filled_width)
        
        elapsed = int(self.current_position)
        total = self.duration
        elapsed_str = format_duration(elapsed)
        total_str = format_duration(total)
        
        # Add playing indicator
        indicator = "▶" if self.playing else "⏸"
        
        return f"{indicator} [{gradient_color(self.progress)}]{bar}[/] {elapsed_str} / {total_str}"

# Track list widget
class TrackList(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracks = []
        self.selected_index = 0
        
    def set_tracks(self, tracks: List[Track]) -> None:
        self.tracks = tracks
        self.selected_index = 0 if tracks else -1
        self.refresh()
        
    def select_next(self) -> bool:
        if self.tracks and self.selected_index < len(self.tracks) - 1:
            self.selected_index += 1
            self.refresh()
            return True
        return False
        
    def select_previous(self) -> bool:
        if self.tracks and self.selected_index > 0:
            self.selected_index -= 1
            self.refresh()
            return True
        return False
        
    def get_selected_track(self) -> Optional[Track]:
        if self.tracks and 0 <= self.selected_index < len(self.tracks):
            return self.tracks[self.selected_index]
        return None
        
    def render(self) -> str:
        if not self.tracks:
            return "[dim]No tracks available[/dim]"
            
        lines = []
        for idx, track in enumerate(self.tracks):
            track_name = track.name[:35]
            artists = ', '.join(track.artists)[:30]
            duration = format_duration(track.duration)
            
            if idx == self.selected_index:
                lines.append(f"[reverse]▶ {track_name} • {artists} [{duration}][/reverse]")
            else:
                lines.append(f"  {track_name} • {artists} [{duration}]")
                
        return "\n".join(lines)

    def on_click(self, event: events.Click) -> None:
        """Handle click events to play tracks"""
        if not self.tracks:
            return
            
        # Map y-coordinate to track index
        # Account for potential scrolling or padding if any, but Static usually renders from 0
        # In this simple case, y corresponds to the line number
        index = event.y
        
        if 0 <= index < len(self.tracks):
            self.selected_index = index
            self.refresh()
            
            # Trigger playback
            track = self.tracks[index]
            # Access the app instance to play the track
            self.app._play_track(track)

# Playlist sidebar widget
class PlaylistSidebar(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.playlists = []
        self.selected_index = 0
        
    def set_playlists(self, playlists: List[Dict]) -> None:
        self.playlists = playlists
        self.selected_index = 0 if playlists else -1
        self.refresh()
        
    def select_next(self) -> bool:
        if self.playlists and self.selected_index < len(self.playlists) - 1:
            self.selected_index += 1
            self.refresh()
            return True
        return False
        
    def select_previous(self) -> bool:
        if self.playlists and self.selected_index > 0:
            self.selected_index -= 1
            self.refresh()
            return True
        return False
        
    def get_selected_playlist(self) -> Optional[Dict]:
        if self.playlists and 0 <= self.selected_index < len(self.playlists):
            return self.playlists[self.selected_index]
        return None
        
    def render(self) -> str:
        if not self.playlists:
            return "[dim]No playlists[/dim]"
            
        lines = ["┌" + "─" * 32 + "┐"]
        lines.append("│ [bold cyan]🎵 YOUR PLAYLISTS[/bold cyan] │")
        lines.append("├" + "─" * 32 + "┤")
        
        for idx, playlist in enumerate(self.playlists):
            prefix = "🎧 " if idx == self.selected_index else "  "
            name = playlist['name'][:26]
            track_count = len(playlist.get('items', []))
            
            if idx == self.selected_index:
                lines.append(f"│[reverse {gradient_color(idx/len(self.playlists))}] {prefix}{name} ({track_count})[/] │")
            else:
                lines.append(f"│ {prefix}{name.ljust(28)}│")
                
        lines.append("└" + "─" * 32 + "┘")
        return "\n".join(lines)

    def on_click(self, event: events.Click) -> None:
        """Handle click events to select playlists"""
        if not self.playlists:
            return
            
        # Account for header (3 lines)
        # Line 0: ┌──...
        # Line 1: │ 🎵 ...
        # Line 2: ├──...
        # Line 3: First playlist
        
        header_height = 3
        index = event.y - header_height
        
        if 0 <= index < len(self.playlists):
            self.selected_index = index
            self.refresh()
            
            # Update track list in the app
            self.app._update_track_list()
            self.app._stop_track()

# Now Playing Widget
class NowPlaying(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_track = None
        
    def set_track(self, track: Optional[Track]) -> None:
        self.current_track = track
        self.refresh()
        
    def render(self) -> str:
        if not self.current_track:
            return "[dim]No track playing[/dim]"
            
        track_name = self.current_track.name
        artists = ', '.join(self.current_track.artists)
        audio_info = "🔊 Audio Available" if self.current_track.preview_url else "🔇 No Preview"
        
        return f"[bold]{track_name}[/bold]\n[dim]by {artists}[/dim]\n{audio_info}"

# Main App
class RetroSpotifyApp(App):
    TITLE = "RetroSpotify - Terminal Music Player"
    CSS = """
    Screen {
        background: #000011;
        color: #00ff88;
    }
    
    #header {
        height: 3;
        background: #001122;
        border: solid #00ff88;
        margin: 1;
        padding: 0 1;
    }
    
    #main-layout {
        height: 1fr;
        margin: 1;
    }
    
    #top-row {
        height: 60%;
        layout: horizontal;
    }
    
    #bottom-row {
        height: 40%;
        layout: horizontal;
        margin-top: 1;
    }
    
    #playlist-sidebar {
        width: 30%;
        border: solid #00ff88;
        padding: 1;
        background: #001133;
    }
    
    #track-list-container {
        width: 40%;
        border: solid #00ff88;
        padding: 1;
        background: #001133;
    }
    
    #album-art-container {
        width: 30%;
        border: solid #00ff88;
        padding: 1;
        background: #001133;
    }
    
    #now-playing-container {
        width: 50%;
        border: solid #00ff88;
        padding: 1;
        background: #001133;
    }
    
    #progress-container {
        width: 50%;
        border: solid #00ff88;
        padding: 1;
        background: #001133;
    }
    
    #status-bar {
        height: 3;
        background: #001122;
        border: solid #00ff88;
        margin: 1;
        padding: 0 1;
    }
    
    .title {
        text-style: bold;
        color: #00ffcc;
        margin-bottom: 1;
    }
    
    /* Compact layout for smaller terminals */
    #main-layout.compact {
        layout: vertical;
    }
    
    #main-layout.compact #top-row {
        height: auto;
        layout: vertical;
    }
    
    #main-layout.compact #bottom-row {
        height: auto;
        layout: vertical;
    }
    
    #main-layout.compact #playlist-sidebar,
    #main-layout.compact #track-list-container,
    #main-layout.compact #album-art-container,
    #main-layout.compact #now-playing-container,
    #main-layout.compact #progress-container {
        width: 100%;
        height: auto;
        min-height: 8;
    }
    
    .hidden {
        display: none;
    }
    
    #search_input {
        margin-bottom: 1;
        border: solid #00ff88;
        background: #001133;
        color: #00ffcc;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_play", "Play/Pause"),
        ("n", "next_track", "Next Track"),
        ("p", "previous_track", "Previous Track"),
        ("l", "next_playlist", "Next Playlist"),
        ("h", "previous_playlist", "Previous Playlist"),
        ("r", "refresh", "Refresh"),
        ("/", "search", "Search"),
        ("+", "volume_up", "Vol +"),
        ("-", "volume_down", "Vol -"),
        ("space", "toggle_play", "Play/Pause"),
        ("?", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.playlists: List[Dict] = MOCK_PLAYLISTS.copy()
        self.is_playing = False
        self.sp = None
        self.current_track = None
        self.compact_mode = False
        self.music_player = MusicPlayer()

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main-layout") as main_layout:
            main_layout.can_focus = False
            
            # Top Row: Playlists, Track List, Album Art
            with Horizontal(id="top-row"):
                # Playlist Sidebar
                with Vertical(id="playlist-sidebar"):
                    yield Static("[bold]Playlists[/bold]", classes="title")
                    yield PlaylistSidebar(id="sidebar")
                
                # Track List
                with ScrollableContainer(id="track-list-container"):
                    yield Static("[bold]Tracks[/bold]", classes="title")
                    yield Input(placeholder="Search tracks...", id="search_input", classes="hidden")
                    yield TrackList(id="track_list")
                
                # Album Art
                with Vertical(id="album-art-container"):
                    yield Static("[bold]Album Art[/bold]", classes="title")
                    yield AlbumArt(id="album_art")
            
            # Bottom Row: Now Playing & Progress
            with Horizontal(id="bottom-row"):
                # Now Playing Info
                with Vertical(id="now-playing-container"):
                    yield Static("[bold]Now Playing[/bold]", classes="title")
                    yield NowPlaying(id="now_playing_info")
                
                # Progress Container
                with Vertical(id="progress-container"):
                    yield Static("[bold]Progress[/bold]", classes="title")
                    yield MusicProgressBar(id="music_progress")
        
        # Status Bar
        with Horizontal(id="status-bar"):
            yield Static("RetroSpotify • Press ? for help", id="status_message")
            yield Static("", id="connection_status")
        
        yield Footer()

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize and switch to compact mode if needed"""
        main_layout = self.query_one("#main-layout")
        if event.size.width < 100:
            if not self.compact_mode:
                main_layout.add_class("compact")
                self.compact_mode = True
        else:
            if self.compact_mode:
                main_layout.remove_class("compact")
                self.compact_mode = False

    async def on_mount(self) -> None:
        self.sidebar = self.query_one("#sidebar", PlaylistSidebar)
        self.track_list = self.query_one("#track_list", TrackList)
        self.album_art = self.query_one("#album_art", AlbumArt)
        self.now_playing_info = self.query_one("#now_playing_info", NowPlaying)
        self.music_progress = self.query_one("#music_progress", MusicProgressBar)
        self.status_message = self.query_one("#status_message", Static)
        self.music_progress = self.query_one("#music_progress", MusicProgressBar)
        self.status_message = self.query_one("#status_message", Static)
        self.connection_status = self.query_one("#connection_status", Static)
        self.search_input = self.query_one("#search_input", Input)
        
        # Check initial terminal size
        if self.size and self.size.width < 100:
            main_layout = self.query_one("#main-layout")
            main_layout.add_class("compact")
            self.compact_mode = True
        
        # Initialize UI
        self.sidebar.set_playlists(self.playlists)
        self._update_track_list()
        
        # Spotify authentication
        if SPOTIPY_AVAILABLE and all([
            os.getenv("SPOTIPY_CLIENT_ID"),
            os.getenv("SPOTIPY_CLIENT_SECRET"),
            os.getenv("SPOTIPY_REDIRECT_URI")
        ]):
            self.connection_status.update("🔗 Connecting to Spotify...")
            asyncio.create_task(self._authenticate_spotify())
        else:
            self.connection_status.update("🎵 Mock Mode")
            self.status_message.update("RetroSpotify (Mock Mode) • Install ffplay/mpg123 for audio")

    async def _authenticate_spotify(self):
        try:
            scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private"
            auth_manager = SpotifyOAuth(scope=scope, cache_path=".spotify_cache")
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            current_user = self.sp.current_user()
            if current_user:
                self.connection_status.update(f"🔗 {current_user['display_name']}")
                await self._load_spotify_playlists()
        except Exception as e:
            self.connection_status.update("❌ Spotify Failed")
            self.notify(f"Spotify auth failed: {e}")

    async def _load_spotify_playlists(self):
        try:
            if not self.sp:
                return
                
            playlists = []
            
            # 1. Fetch Liked Songs (Saved Tracks)
            try:
                saved_tracks_results = self.sp.current_user_saved_tracks(limit=50)
                liked_tracks = []
                for item in saved_tracks_results['items']:
                    track_data = item['track']
                    if track_data:
                        album_images = track_data['album']['images']
                        album_art_url = album_images[0]['url'] if album_images else None
                        
                        liked_tracks.append(Track(
                            name=track_data['name'],
                            artists=[artist['name'] for artist in track_data['artists']],
                            duration=track_data['duration_ms'] // 1000,
                            id=track_data['id'],
                            album_art_url=album_art_url,
                            preview_url=track_data.get('preview_url')
                        ))
                
                if liked_tracks:
                    playlists.append({
                        'name': 'Liked Songs',
                        'id': 'liked_songs',
                        'items': liked_tracks
                    })
            except Exception as e:
                self.notify(f"Failed to load Liked Songs: {e}")

            # 2. Fetch User Playlists
            results = self.sp.current_user_playlists(limit=20)
            
            for item in results['items']:
                tracks = []
                # ... (rest of playlist loading logic)
                track_results = self.sp.playlist_tracks(item['id'], limit=50)
                
                for track_item in track_results['items']:
                    track_data = track_item['track']
                    if track_data:
                        # Get album art URL
                        album_images = track_data['album']['images']
                        album_art_url = album_images[0]['url'] if album_images else None
                        
                        # Get preview URL
                        preview_url = track_data.get('preview_url')
                        
                        tracks.append(Track(
                            name=track_data['name'],
                            artists=[artist['name'] for artist in track_data['artists']],
                            duration=track_data['duration_ms'] // 1000,
                            id=track_data['id'],
                            album_art_url=album_art_url,
                            preview_url=preview_url
                        ))
                
                playlists.append({
                    'name': item['name'],
                    'id': item['id'],
                    'items': tracks
                })
            
            if playlists:
                self.playlists = playlists
                self.sidebar.set_playlists(self.playlists)
                self._update_track_list()
                self.notify(f"Loaded {len(playlists)} playlists from Spotify")
                
        except Exception as e:
            self.notify(f"Failed to load playlists: {e}")

    def _update_track_list(self):
        current_playlist = self.sidebar.get_selected_playlist()
        if current_playlist:
            tracks = current_playlist.get('items', [])
            self.track_list.set_tracks(tracks)

    def _play_track(self, track: Track):
        """Play a track with real audio"""
        self.current_track = track
        self.now_playing_info.set_track(track)
        
        # Update album art
        if track.album_art_url:
            self.album_art.set_art_from_url(track.album_art_url)
        else:
            self.album_art.set_fallback_art()
        
        # Start progress bar
        self.music_progress.play(track.duration)
        self.is_playing = True
        
        # Try Spotify Connect first if authenticated
        if self.sp and track.id:
            try:
                # Run in thread to avoid blocking UI
                def start_playback():
                    try:
                        self.sp.start_playback(uris=[f"spotify:track:{track.id}"])
                        return True
                    except Exception as e:
                        return False

                # We can't easily await in this sync method without restructuring, 
                # but we can fire-and-forget or use a quick check.
                # For responsiveness, let's try to start it.
                # NOTE: In a real async TUI, we should await this.
                # Since _play_track is called from sync context, we'll use a thread.
                import threading
                t = threading.Thread(target=start_playback)
                t.start()
                
                self.status_message.update(f"▶️ Spotify Connect: {track.name}")
                return
            except Exception:
                pass

        # Fallback to local audio if available
        if track.preview_url:
            success = self.music_player.play(track.preview_url)
            if success:
                self.status_message.update(f"▶️ Playing Preview: {track.name}")
            else:
                self.status_message.update(f"⏸️ Simulating: {track.name} (no audio player)")
        else:
            self.status_message.update(f"❌ No active Spotify device & no preview")
            self.music_player.stop()

    def _pause_track(self):
        """Pause current track"""
        self.music_progress.pause()
        self.music_player.stop()
        self.is_playing = False
        self.status_message.update("⏸️ Paused")

    def _stop_track(self):
        """Stop current track completely"""
        self.music_progress.stop()
        self.music_player.stop()
        self.is_playing = False
        self.current_track = None
        self.status_message.update("⏹️ Stopped")

    # Actions
    def action_toggle_play(self):
        current_track = self.track_list.get_selected_track()
        if current_track:
            if self.is_playing and self.current_track == current_track:
                self._pause_track()
            else:
                # If different track or not playing, start playing
                self._play_track(current_track)

    def action_next_track(self):
        if self.track_list.select_next():
            if self.is_playing:
                current_track = self.track_list.get_selected_track()
                if current_track:
                    self._play_track(current_track)

    def action_previous_track(self):
        if self.track_list.select_previous():
            if self.is_playing:
                current_track = self.track_list.get_selected_track()
                if current_track:
                    self._play_track(current_track)

    def action_next_playlist(self):
        if self.sidebar.select_next():
            self._update_track_list()
            self._stop_track()  # Stop playback when changing playlists

    def action_previous_playlist(self):
        if self.sidebar.select_previous():
            self._update_track_list()
            self._stop_track()  # Stop playback when changing playlists

    def action_refresh(self):
        if self.sp:
            asyncio.create_task(self._load_spotify_playlists())
        else:
            self.notify("Refreshed local data")

    def action_search(self):
        """Toggle search input"""
        self.search_input.toggle_class("hidden")
        if not self.search_input.has_class("hidden"):
            self.search_input.focus()

    def on_input_submitted(self, event: Input.Submitted):
        """Handle search submission"""
        query = event.value
        if not query:
            return
            
        if self.sp:
            asyncio.create_task(self._perform_search(query))
        else:
            # Mock Search
            self.status_message.update(f"🔍 Searching locally for '{query}'...")
            query_lower = query.lower()
            found_tracks = []
            
            for playlist in self.playlists:
                for track in playlist.get('items', []):
                    if query_lower in track.name.lower() or any(query_lower in a.lower() for a in track.artists):
                        found_tracks.append(track)
            
            if found_tracks:
                self.track_list.set_tracks(found_tracks)
                self.status_message.update(f"✅ Found {len(found_tracks)} results")
            else:
                self.status_message.update("❌ No results found")
            
    async def _perform_search(self, query: str):
        try:
            self.status_message.update(f"🔍 Searching for '{query}'...")
            # Run search in thread to not block UI
            results = await asyncio.to_thread(self.sp.search, query, limit=20, type='track')
            
            tracks = []
            for track_item in results['tracks']['items']:
                # Get album art URL
                album_images = track_item['album']['images']
                album_art_url = album_images[0]['url'] if album_images else None
                
                tracks.append(Track(
                    name=track_item['name'],
                    artists=[artist['name'] for artist in track_item['artists']],
                    duration=track_item['duration_ms'] // 1000,
                    id=track_item['id'],
                    album_art_url=album_art_url,
                    preview_url=track_item.get('preview_url')
                ))
            
            if tracks:
                self.track_list.set_tracks(tracks)
                self.status_message.update(f"✅ Found {len(tracks)} results")
            else:
                self.status_message.update("❌ No results found")
                
        except Exception as e:
            self.status_message.update("❌ Search failed")
            self.notify(f"Search error: {e}")

    def action_volume_up(self):
        self.music_player.set_volume(self.music_player.volume + 10)
        self.notify(f"Volume: {self.music_player.volume}%")
        
    def action_volume_down(self):
        self.music_player.set_volume(self.music_player.volume - 10)
        self.notify(f"Volume: {self.music_player.volume}%")

    def action_help(self):
        help_text = """
🎵 RetroSpotify Controls 🎵

[bold]Playback:[/bold]
Space/s - Play/Pause
n - Next Track
p - Previous Track

[bold]Navigation:[/bold]
l - Next Playlist
h - Previous Playlist
r - Refresh Data

[bold]Audio Requirements:[/bold]
Install one of these for real audio:
• ffmpeg (ffplay) - Recommended
• mpg123
• sox

[bold]General:[/bold]
? - This help
q - Quit
"""
        self.notify(help_text)

    def action_quit(self):
        self.music_player.stop()
        self.exit()

if __name__ == "__main__":
    # Check for audio players
    audio_players = ['ffplay', 'cvlc', 'vlc', 'mpg123', 'play']
    available_players = []
    
    for player in audio_players:
        try:
            subprocess.run([player, '--version'], capture_output=True)
            available_players.append(player)
        except FileNotFoundError:
            continue
    
    if available_players:
        print(f"🎵 Audio players available: {', '.join(available_players)}")
    else:
        print("🔇 No audio players found. Install ffmpeg for best experience:")
        print("   Ubuntu: sudo apt install ffmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/")
    
    if SPOTIPY_AVAILABLE:
        required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print("🎵 RetroSpotify - Running in mock mode")
            print("💡 To use Spotify, set these environment variables:")
            for var in missing_vars:
                print(f"   {var}=your_value_here")
    
    app = RetroSpotifyApp()
    app.run()