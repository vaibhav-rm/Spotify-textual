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
from textual.message import Message

# Optional Spotify imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    spotipy = None
    SpotifyOAuth = None

# Optional PIL imports
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

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
    if Image is None:
        return generate_fallback_art()
    # Convert to grayscale
    img = img.convert('L')
    
    # Resize
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # ASCII characters from dark to light (for dark terminal)
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
    if not PIL_AVAILABLE or not Image:
        return generate_fallback_art()
    try:
        response = requests.get(image_url)
        img = Image.open(requests.compat.BytesIO(response.content))
        return generate_ascii_art_from_image(img, width, height)
    except Exception:
        return generate_fallback_art()

def generate_fallback_art() -> str:
    """Generate fallback ASCII art from local file or text"""
    if PIL_AVAILABLE and Image:
        try:
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
        old_volume = self.volume
        self.volume = max(0, min(100, volume))
        
        # If playing via ffplay, send volume control commands to stdin
        if self.process and self.process.poll() is None:
            old_step = old_volume // 10
            new_step = self.volume // 10
            diff = new_step - old_step
            if diff > 0:
                try:
                    self.process.stdin.write(b'0' * diff)
                    self.process.stdin.flush()
                except Exception:
                    pass
            elif diff < 0:
                try:
                    self.process.stdin.write(b'9' * abs(diff))
                    self.process.stdin.flush()
                except Exception:
                    pass
        
    def play(self, preview_url: str) -> bool:
        """Play audio from URL using system player"""
        try:
            self.stop()  # Stop any currently playing audio
            
            ffplay_vol = str(self.volume)
            vlc_vol = str(int(self.volume * 2.56))
            
            # Check for synthetic audio
            if preview_url.startswith("sine="):
                cmd = ['ffplay', '-f', 'lavfi', '-i', preview_url, '-autoexit', '-nodisp', '-loglevel', 'quiet', '-volume', ffplay_vol]
                try:
                    self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.is_playing = True
                    return True
                except FileNotFoundError:
                    pass

            # Try different methods to play audio
            players = [
                (['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-volume', ffplay_vol, preview_url], True),
                (['cvlc', '--play-and-exit', '--no-video', '--volume', vlc_vol, preview_url], False),
                (['mpg123', '-q', preview_url], False),
                (['play', '-q', '-v', str(self.volume/100.0), preview_url], False),
            ]
            
            for player_cmd, support_stdin in players:
                try:
                    stdin_val = subprocess.PIPE if support_stdin else None
                    self.process = subprocess.Popen(
                        player_cmd,
                        stdin=stdin_val,
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
            self.is_playing = False
            return False
    
    def pause(self) -> bool:
        """Pause playback"""
        if self.process and self.process.poll() is None and self.is_playing:
            try:
                self.process.stdin.write(b'p')
                self.process.stdin.flush()
                self.is_playing = False
                return True
            except Exception:
                pass
        return False
        
    def resume(self) -> bool:
        """Resume playback"""
        if self.process and self.process.poll() is None and not self.is_playing:
            try:
                self.process.stdin.write(b'p')
                self.process.stdin.flush()
                self.is_playing = True
                return True
            except Exception:
                pass
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
            return self.pause()
        else:
            return self.resume() or self.play(preview_url)

# Visual helpers
def gradient_color(pos: float, start=(29, 185, 84), end=(0, 255, 128)) -> str:
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
            ascii_art = generate_ascii_art_from_url(url, width=40, height=20)
            self.art_content = ascii_art
        except Exception:
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
    
    class TrackEnded(Message):
        """Sent when the track ends"""
        pass
        
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
            
            if self.current_position >= self.duration:
                self.playing = False
                self.current_position = 0
                self.progress = 0
                self.refresh()
                self.post_message(self.TrackEnded())
            else:
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
            return "\n[dim]--:-- / --:--[/dim]"
            
        width = max(10, (self.size.width - 14) if self.size else 35)
        filled_width = int(self.progress * width)
        bar = "█" * filled_width + "─" * (width - filled_width)
        
        elapsed = int(self.current_position)
        total = self.duration
        elapsed_str = format_duration(elapsed)
        total_str = format_duration(total)
        
        controls = "⏮   ▶   ⏭" if self.playing else "⏮   ⏸   ⏭"
        total_line_w = width + 12
        
        return f"[bold white]{controls:^{total_line_w}}[/bold white]\n\n{elapsed_str} [#1db954]{bar}[/] {total_str}"

# Track list widget
class TrackList(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracks = []
        self.selected_index = 0
        self.can_focus = True
        
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
            
        width = self.size.width if self.size else 60
        num_w = 4
        dur_w = 6
        remaining = width - num_w - dur_w - 6
        if remaining < 10:
            remaining = 10
        title_w = int(remaining * 0.6)
        artist_w = remaining - title_w
        
        header = f"[dim]{'#'.ljust(num_w)} {'Title'.ljust(title_w)} {'Artist'.ljust(artist_w)} {'Duration'.rjust(dur_w)}[/dim]"
        divider = f"[dim]{'─' * width}[/dim]"
        
        lines = [header, divider]
        for idx, track in enumerate(self.tracks):
            track_num = f"{idx + 1}"
            track_name = track.name
            artists = ', '.join(track.artists)
            duration = format_duration(track.duration)
            
            t_name = track_name[:title_w].ljust(title_w)
            t_artists = artists[:artist_w].ljust(artist_w)
            
            if idx == self.selected_index:
                lines.append(f"[bold #1db954]▶   {t_name} {t_artists} {duration.rjust(dur_w)}[/bold #1db954]")
            else:
                lines.append(f"[dim]{track_num.ljust(num_w)}[/dim] [white]{t_name}[/white] [dim]{t_artists}[/dim] [dim]{duration.rjust(dur_w)}[/dim]")
                
        return "\n".join(lines)

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self.select_previous()
            event.prevent_default()
        elif event.key == "down":
            self.select_next()
            event.prevent_default()
        elif event.key == "enter":
            track = self.get_selected_track()
            if track:
                self.app._play_track(track)
            event.prevent_default()

    def on_click(self, event: events.Click) -> None:
        """Handle click events to play tracks"""
        if not self.tracks:
            return
            
        index = event.y - 2
        if 0 <= index < len(self.tracks):
            self.selected_index = index
            self.refresh()
            track = self.tracks[index]
            self.app._play_track(track)

# Playlist sidebar widget
class PlaylistSidebar(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.playlists = []
        self.selected_index = 0
        self.can_focus = True
        
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
            
        lines = []
        for idx, playlist in enumerate(self.playlists):
            name = playlist['name']
            track_count = len(playlist.get('items', []))
            
            if idx == self.selected_index:
                lines.append(f"[bold #1db954]▶ 🎧 {name} ({track_count})[/bold #1db954]")
            else:
                lines.append(f"   🎧 {name}")
                
        return "\n".join(lines)

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self.select_previous()
            self.app._update_track_list()
            self.app._stop_track()
            event.prevent_default()
        elif event.key == "down":
            self.select_next()
            self.app._update_track_list()
            self.app._stop_track()
            event.prevent_default()

    def on_click(self, event: events.Click) -> None:
        """Handle click events to select playlists"""
        if not self.playlists:
            return
            
        index = event.y
        if 0 <= index < len(self.playlists):
            self.selected_index = index
            self.refresh()
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
            return "[dim]No track playing[/dim]\n\n[dim]Select a track and press Space/s to play[/dim]"
            
        track_name = self.current_track.name
        artists = ', '.join(self.current_track.artists)
        
        if self.current_track.preview_url:
            if self.current_track.preview_url.startswith("sine="):
                audio_info = "🔊 [cyan]Local Synth[/cyan]"
            else:
                audio_info = "🔊 [green]Spotify Preview[/green]"
        else:
            audio_info = "🔇 [dim]No Audio[/dim]"
            
        return f"[bold white]{track_name}[/bold white]\n[#b3b3b3]by {artists}[/#b3b3b3]\n\n{audio_info}"

# Volume & Control Widget
class VolumeWidget(Static):
    volume = reactive(100)
    shuffle = reactive(False)
    repeat = reactive("off")
    
    def render(self) -> str:
        vol_width = 10
        filled = int((self.volume / 100.0) * vol_width)
        vol_bar = "█" * filled + "─" * (vol_width - filled)
        
        vol_color = gradient_color(self.volume / 100.0)
        vol_line = f"🔊 [{vol_color}]{vol_bar}[/] {self.volume}%"
        
        shuf_status = "[bold #1db954]SHUF[/]" if self.shuffle else "[dim]SHUF[/]"
        rep_status = "[bold #1db954]REP[/]" if self.repeat == "track" else "[dim]REP[/]"
        
        return f"\n{vol_line}\n\n{shuf_status}   {rep_status}"

# Main App
class RetroSpotifyApp(App):
    TITLE = "RetroSpotify - Terminal Music Player"
    CSS = """
    Screen {
        background: #121212;
        color: #b3b3b3;
    }
    
    #header {
        height: 3;
        background: #000000;
        border: none;
        margin: 0;
        padding: 0 1;
        color: #ffffff;
    }
    
    #main-layout {
        height: 1fr;
        margin: 1 1 0 1;
    }
    
    #top-row {
        height: 65%;
        layout: horizontal;
    }
    
    #bottom-row {
        height: 35%;
        layout: horizontal;
        margin-top: 1;
    }
    
    #playlist-sidebar {
        width: 25%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #playlist-sidebar:focus-within {
        border: round #1db954;
    }
    
    #track-list-container {
        width: 50%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #track-list-container:focus-within {
        border: round #1db954;
    }
    
    #album-art-container {
        width: 25%;
        border: round #282828;
        background: #181818;
        padding: 1;
        align: center middle;
    }
    #album-art-container:focus-within {
        border: round #1db954;
    }
    
    #now-playing-container {
        width: 30%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #now-playing-container:focus-within {
        border: round #1db954;
    }
    
    #progress-container {
        width: 45%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #progress-container:focus-within {
        border: round #1db954;
    }
    
    #volume-container {
        width: 25%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #volume-container:focus-within {
        border: round #1db954;
    }
    
    #status-bar {
        height: 3;
        background: #000000;
        border: none;
        margin: 0;
        padding: 0 1;
        color: #b3b3b3;
    }
    
    #search_input {
        margin-bottom: 1;
        border: solid #282828;
        background: #121212;
        color: #ffffff;
    }
    #search_input:focus {
        border: solid #1db954;
    }
    
    .hidden {
        display: none;
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
        ("S", "toggle_shuffle", "Shuffle"),
        ("R", "toggle_repeat", "Repeat"),
        ("a", "authenticate", "Auth Spotify"),
        ("space", "toggle_play", "Play/Pause"),
        ("?", "help", "Help"),
    ]

    def __init__(self, force_mock: bool = False):
        super().__init__()
        self.force_mock = force_mock
        self.playlists: List[Dict] = MOCK_PLAYLISTS.copy()
        self.is_playing = False
        self.sp = None
        self.current_track = None
        self.compact_mode = False
        self.music_player = MusicPlayer()
        self.shuffle_state = False
        self.repeat_state = "off"

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main-layout") as main_layout:
            main_layout.can_focus = False
            
            with Horizontal(id="top-row"):
                sidebar_container = ScrollableContainer(id="playlist-sidebar")
                sidebar_container.border_title = "LIBRARY"
                with sidebar_container:
                    yield PlaylistSidebar(id="sidebar")
                
                track_container = ScrollableContainer(id="track-list-container")
                track_container.border_title = "TRACKS"
                with track_container:
                    yield Input(placeholder="🔍 Search tracks (Esc to close)...", id="search_input", classes="hidden")
                    yield TrackList(id="track_list")
                
                art_container = Vertical(id="album-art-container")
                art_container.border_title = "ALBUM ART"
                with art_container:
                    yield AlbumArt(id="album_art")
            
            with Horizontal(id="bottom-row"):
                np_container = Vertical(id="now-playing-container")
                np_container.border_title = "NOW PLAYING"
                with np_container:
                    yield NowPlaying(id="now_playing_info")
                
                prog_container = Vertical(id="progress-container")
                prog_container.border_title = "PROGRESS"
                with prog_container:
                    yield MusicProgressBar(id="music_progress")

                vol_container = Vertical(id="volume-container")
                vol_container.border_title = "CONTROLS"
                with vol_container:
                    yield VolumeWidget(id="volume_widget")
        
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
        self.connection_status = self.query_one("#connection_status", Static)
        self.search_input = self.query_one("#search_input", Input)
        self.volume_widget = self.query_one("#volume_widget", VolumeWidget)
        
        # Check initial terminal size
        if self.size and self.size.width < 100:
            main_layout = self.query_one("#main-layout")
            main_layout.add_class("compact")
            self.compact_mode = True
        
        # Initialize UI
        self.sidebar.set_playlists(self.playlists)
        self._update_track_list()
        
        # Sync volume widget
        self.volume_widget.volume = self.music_player.volume
        self.volume_widget.shuffle = self.shuffle_state
        self.volume_widget.repeat = self.repeat_state
        
        # Spotify authentication
        if not self.force_mock and SPOTIPY_AVAILABLE and all([
            os.getenv("SPOTIPY_CLIENT_ID"),
            os.getenv("SPOTIPY_CLIENT_SECRET"),
            os.getenv("SPOTIPY_REDIRECT_URI")
        ]):
            self.connection_status.update("🔗 Connecting to Spotify...")
            asyncio.create_task(self._authenticate_spotify())
        else:
            self.connection_status.update("🎵 Mock Mode")
            self.status_message.update("RetroSpotify (Mock Mode) • Press 'a' to set up Spotify login")

    async def _authenticate_spotify(self):
        try:
            scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private"
            auth_manager = SpotifyOAuth(scope=scope, cache_path=".spotify_cache")
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Check cached token or attempt check
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
            
            # 1. Fetch Liked Songs
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
                track_results = self.sp.playlist_tracks(item['id'], limit=50)
                
                for track_item in track_results['items']:
                    track_data = track_item['track']
                    if track_data:
                        album_images = track_data['album']['images']
                        album_art_url = album_images[0]['url'] if album_images else None
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
        # If we are resuming the same track
        if self.current_track == track and not self.is_playing:
            self._resume_track()
            return
            
        self.current_track = track
        self.now_playing_info.set_track(track)
        
        # Update album art
        if track.album_art_url:
            self.album_art.set_art_from_url(track.album_art_url)
        else:
            self.album_art.set_fallback_art()
        
        # Start progress bar
        self.music_progress.stop()
        self.music_progress.play(track.duration)
        self.is_playing = True
        
        # Try Spotify Connect first if authenticated
        if self.sp and track.id:
            try:
                def start_playback():
                    try:
                        self.sp.start_playback(uris=[f"spotify:track:{track.id}"])
                        return True
                    except Exception:
                        return False

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

    def _resume_track(self):
        """Resume current track"""
        if self.current_track:
            # Try Spotify Connect resume
            if self.sp and self.current_track.id:
                try:
                    def start_playback():
                        try:
                            self.sp.start_playback()
                            return True
                        except Exception:
                            return False
                    import threading
                    t = threading.Thread(target=start_playback)
                    t.start()
                    self.status_message.update(f"▶️ Spotify Connect: {self.current_track.name}")
                    self.music_progress.play(self.current_track.duration)
                    self.is_playing = True
                    return
                except Exception:
                    pass
            
            # Local player resume
            success = self.music_player.resume()
            if success:
                self.status_message.update(f"▶️ Playing: {self.current_track.name}")
                self.music_progress.play(self.current_track.duration)
                self.is_playing = True
            else:
                self._play_track(self.current_track)

    def _pause_track(self):
        """Pause current track"""
        self.music_progress.pause()
        if self.sp and self.current_track and self.current_track.id:
            try:
                def pause_playback():
                    try:
                        self.sp.pause_playback()
                        return True
                    except Exception:
                        return False
                import threading
                t = threading.Thread(target=pause_playback)
                t.start()
            except Exception:
                pass
        
        self.music_player.pause()
        self.is_playing = False
        self.status_message.update("⏸️ Paused")

    def _stop_track(self):
        """Stop current track completely"""
        self.music_progress.stop()
        self.music_player.stop()
        self.is_playing = False
        self.current_track = None
        self.status_message.update("⏹️ Stopped")

    def on_music_progress_track_ended(self, message: MusicProgressBar.TrackEnded) -> None:
        """Handle track ending by playing the next track (taking repeat/shuffle into account)"""
        if self.repeat_state == 'track':
            if self.current_track:
                self._play_track(self.current_track)
        else:
            self.action_next_track()

    # Actions
    def action_toggle_play(self):
        current_track = self.track_list.get_selected_track()
        if current_track:
            if self.is_playing and self.current_track == current_track:
                self._pause_track()
            elif not self.is_playing and self.current_track == current_track:
                self._resume_track()
            else:
                self._play_track(current_track)

    def action_next_track(self):
        if self.shuffle_state:
            current_playlist = self.sidebar.get_selected_playlist()
            if current_playlist:
                tracks = current_playlist.get('items', [])
                if tracks:
                    rand_idx = random.randint(0, len(tracks) - 1)
                    self.track_list.selected_index = rand_idx
                    self.track_list.refresh()
                    if self.is_playing:
                        self._play_track(tracks[rand_idx])
                    return
        
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
            self._stop_track()

    def action_previous_playlist(self):
        if self.sidebar.select_previous():
            self._update_track_list()
            self._stop_track()

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

    def on_input_changed(self, event: Input.Changed):
        """If search input is cleared, restore the original playlist tracks"""
        if event.input.id == "search_input" and not event.value:
            self._update_track_list()

    def on_key(self, event: events.Key) -> None:
        """Handle global escape key for search input"""
        if event.key == "escape":
            if not self.search_input.has_class("hidden"):
                self.search_input.value = ""
                self.search_input.add_class("hidden")
                self._update_track_list()
                self.track_list.focus()

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
            results = await asyncio.to_thread(self.sp.search, query, limit=20, type='track')
            
            tracks = []
            for track_item in results['tracks']['items']:
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
        self.volume_widget.volume = self.music_player.volume
        self.notify(f"Volume: {self.music_player.volume}%")
        
    def action_volume_down(self):
        self.music_player.set_volume(self.music_player.volume - 10)
        self.volume_widget.volume = self.music_player.volume
        self.notify(f"Volume: {self.music_player.volume}%")

    def action_toggle_shuffle(self):
        self.shuffle_state = not self.shuffle_state
        self.volume_widget.shuffle = self.shuffle_state
        
        if self.sp:
            def set_shuffle():
                try:
                    self.sp.shuffle(state=self.shuffle_state)
                except Exception:
                    pass
            import threading
            threading.Thread(target=set_shuffle).start()
            
        self.notify(f"Shuffle: {'ON' if self.shuffle_state else 'OFF'}")

    def action_toggle_repeat(self):
        if self.repeat_state == "off":
            self.repeat_state = "track"
        else:
            self.repeat_state = "off"
            
        self.volume_widget.repeat = self.repeat_state
        
        if self.sp:
            def set_repeat():
                try:
                    self.sp.repeat(state=self.repeat_state)
                except Exception:
                    pass
            import threading
            threading.Thread(target=set_repeat).start()
            
        self.notify(f"Repeat: {self.repeat_state.upper()}")

    async def action_authenticate(self):
        """Suspend TUI and configure/authenticate Spotify in the terminal"""
        self.status_message.update("Suspended to authenticate...")
        self.music_player.stop()
        
        with self.suspend():
            print("\n=== Spotify Configuration & Authentication ===")
            print("To connect to Spotify, you need a Spotify Client ID and Client Secret.")
            print("Get them from: https://developer.spotify.com/dashboard/")
            print("Set redirect URI to: http://127.0.0.1:8888/callback\n")
            
            client_id = input(f"Enter Spotify Client ID [{os.getenv('SPOTIPY_CLIENT_ID', 'None')}]: ").strip()
            client_secret = input(f"Enter Spotify Client Secret [{os.getenv('SPOTIPY_CLIENT_SECRET', 'None')}]: ").strip()
            redirect_uri = input(f"Enter Redirect URI [{os.getenv('SPOTIPY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')}]: ").strip()
            
            if client_id:
                os.environ["SPOTIPY_CLIENT_ID"] = client_id
            if client_secret:
                os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
            if redirect_uri:
                os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri
                
            with open(".env", "w") as f:
                f.write(f"SPOTIPY_CLIENT_ID={os.environ.get('SPOTIPY_CLIENT_ID', '')}\n")
                f.write(f"SPOTIPY_CLIENT_SECRET={os.environ.get('SPOTIPY_CLIENT_SECRET', '')}\n")
                f.write(f"SPOTIPY_REDIRECT_URI={os.environ.get('SPOTIPY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')}\n")
                
            print("\nCredentials saved to .env!")
            print("Starting authentication flow... A browser window should open.")
            
            try:
                scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private"
                auth_manager = SpotifyOAuth(scope=scope, cache_path=".spotify_cache")
                token = auth_manager.get_access_token(as_dict=False)
                if token:
                    print("🎉 Success! Authenticated successfully.")
                else:
                    print("⚠️ Could not retrieve access token.")
            except Exception as e:
                print(f"❌ Error during authentication: {e}")
                
            input("\nPress Enter to return to RetroSpotify...")
            
        self.force_mock = False
        asyncio.create_task(self._authenticate_spotify())

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

[bold]Spotify Settings:[/bold]
a - Connect/Auth Spotify
S - Toggle Shuffle
R - Toggle Repeat

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
    
    import argparse
    parser = argparse.ArgumentParser(description="RetroSpotify - Terminal Music Player")
    parser.add_argument("--mock", action="store_true", help="Force mock mode (no Spotify connection)")
    args = parser.parse_args()
    
    if SPOTIPY_AVAILABLE:
        required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars or args.mock:
            print("🎵 RetroSpotify - Running in mock mode")
            if missing_vars and not args.mock:
                print("💡 To use Spotify, set these environment variables:")
                for var in missing_vars:
                    print(f"   {var}=your_value_here")
    
    app = RetroSpotifyApp(force_mock=args.mock)
    app.run()