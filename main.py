import asyncio
import os
import random
import time
import subprocess
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import sys

from dotenv import load_dotenv
import requests
from io import BytesIO

from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Static, Footer, Input, Header, Button, Label, ProgressBar as TextualProgressBar
from textual import events, log
from textual.reactive import reactive
from textual.geometry import Size
from textual.message import Message

# Optional Spotify imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth, SpotifyPKCE
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    spotipy = None
    SpotifyOAuth = None
    SpotifyPKCE = None

# Optional PIL imports
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

load_dotenv()

ASCII_LOGO = r"""
██████╗ ███████╗████████╗██████╗  ██████╗ 
██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗
██████╔╝█████╗     ██║   ██████╔╝██║   ██║
██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║
██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝
╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ 
███████╗██████╗  ██████╗ ████████╗██╗███████╗██╗   ██╗
██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝██║██╔════╝╚██╗ ██╔╝
███████╗██████╔╝██║   ██║   ██║   ██║█████╗   ╚████╔╝ 
╚════██║██╔═══╝ ██║   ██║   ██║   ██║██╔══╝    ╚██╔╝  
███████║██║     ╚██████╔╝   ██║   ██║██║        ██║   
╚══════╝╚═╝      ╚═════╝    ╚═╝   ╚═╝╚═╝        ╚═╝   
"""

# High-Detail Full-Color ANSI block Art Generator for album art
def generate_ascii_art_from_image(img, width: int = 28, height: int = 14) -> str:
    """Generate high-detail full-color ANSI block art from PIL Image object"""
    if Image is None:
        return generate_fallback_art()
    
    # We want 2 vertical pixels per TUI row, so the resized height should be 2 * height
    target_height = height * 2
    img = img.convert('RGB')
    img = img.resize((width, target_height), Image.Resampling.LANCZOS)
    
    lines = []
    for y in range(0, target_height, 2):
        line_chars = []
        for x in range(width):
            r1, g1, b1 = img.getpixel((x, y))
            if y + 1 < target_height:
                r2, g2, b2 = img.getpixel((x, y + 1))
            else:
                r2, g2, b2 = r1, g1, b1
            
            fg_color = f"#{r2:02x}{g2:02x}{b2:02x}"
            bg_color = f"#{r1:02x}{g1:02x}{b1:02x}"
            line_chars.append(f"[{fg_color} on {bg_color}]▄[/]")
            
        lines.append("".join(line_chars))
        
    return "\n".join(lines)

def generate_ascii_art_from_url(image_url: str, width: int = 28, height: int = 14) -> str:
    """Generate high-detail full-color ANSI block art from image URL"""
    if not PIL_AVAILABLE or not Image:
        return generate_fallback_art()
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        return generate_ascii_art_from_image(img, width, height)
    except Exception:
        return generate_fallback_art()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def generate_fallback_art() -> str:
    """Generate fallback ASCII art from local file or text"""
    if PIL_AVAILABLE and Image:
        try:
            path = resource_path("default_cover.png")
            if os.path.exists(path):
                img = Image.open(path)
                return generate_ascii_art_from_image(img, width=28, height=14)
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

def generate_retro_synth_wav(duration: float = 30.0) -> str:
    """Generate a retro 8-bit chiptune melody and return the filepath to the temporary WAV file."""
    import math
    import struct
    import wave
    import tempfile
    
    sample_rate = 22050
    num_samples = int(duration * sample_rate)
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, "retro_fallback.wav")
    
    # C-maj7, A-min7, F-maj7, G-7 progression
    progression = [
        [261.63, 329.63, 392.00, 493.88], # C4, E4, G4, B4
        [220.00, 261.63, 329.63, 392.00], # A3, C4, E4, G4
        [174.61, 220.00, 261.63, 329.63], # F3, A3, C4, E4
        [196.00, 246.94, 293.66, 349.23]  # G3, B3, D4, F4
    ]
    
    note_duration = 0.15 # seconds per note
    samples_per_note = int(note_duration * sample_rate)
    
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1) # mono
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        
        note_index = 0
        chord_index = 0
        samples_written = 0
        
        while samples_written < num_samples:
            chord = progression[chord_index]
            freq = chord[note_index]
            
            current_note_samples = min(samples_per_note, num_samples - samples_written)
            
            data = []
            for i in range(current_note_samples):
                t = (samples_written + i) / sample_rate
                # Square wave
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
                
                # Apply decay envelope
                envelope = 1.0 - (i / samples_per_note) * 0.4
                sample_val = int(val * envelope * 8000) # Max amplitude ~8000
                data.append(struct.pack('<h', sample_val))
                
            wav_file.writeframes(b"".join(data))
            samples_written += current_note_samples
            
            note_index = (note_index + 1) % 4
            if note_index == 0:
                chord_index = (chord_index + 1) % len(progression)
                
    return filepath

def get_spotify_cache_path() -> str:
    """Get the active Spotify cache file path based on SPOTIPY_USERNAME environment variable"""
    username = os.getenv("SPOTIPY_USERNAME")
    if username:
        return f".spotify_cache-{username}"
    return ".spotify_cache"

def check_cached_token() -> bool:
    """Check if we have a valid cached Spotify token (or can refresh it)"""
    try:
        cache_path = get_spotify_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                data = json.load(f)
                if (data.get("access_token") and data.get("expires_at", 0) > time.time()) or data.get("refresh_token"):
                    return True
    except Exception:
        pass
    return False

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
        "name": "Liked Songs",
        "id": "liked_songs",
        "items": [
            Track("Chiptune Dreams", ["Retro Synth"], 165,
                  album_art_url="https://picsum.photos/300/300?random=10",
                  preview_url="sine=f=330:d=30"),
            Track("Bit-rate Groove", ["Pixelate"], 180,
                  album_art_url="https://picsum.photos/300/300?random=11",
                  preview_url="sine=f=440:d=30")
        ]
    },
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

MOCK_GLOBAL_CATALOG = [
    Track("Never Gonna Give You Up", ["Rick Astley"], 212, album_art_url="https://picsum.photos/300/300?random=20", preview_url="sine=f=440:d=30"),
    Track("Take On Me", ["a-ha"], 225, album_art_url="https://picsum.photos/300/300?random=21", preview_url="sine=f=494:d=30"),
    Track("Billie Jean", ["Michael Jackson"], 294, album_art_url="https://picsum.photos/300/300?random=22", preview_url="sine=f=523:d=30"),
    Track("Bohemian Rhapsody", ["Queen"], 354, album_art_url="https://picsum.photos/300/300?random=23", preview_url="sine=f=587:d=30"),
    Track("Blinding Lights", ["The Weeknd"], 200, album_art_url="https://picsum.photos/300/300?random=24", preview_url="sine=f=659:d=30"),
    Track("Stayin' Alive", ["Bee Gees"], 284, album_art_url="https://picsum.photos/300/300?random=25", preview_url="sine=f=698:d=30"),
    Track("Fly Me to the Moon", ["Frank Sinatra"], 147, album_art_url="https://picsum.photos/300/300?random=26", preview_url="sine=f=784:d=30"),
    Track("Hotel California", ["Eagles"], 390, album_art_url="https://picsum.photos/300/300?random=27", preview_url="sine=f=880:d=30"),
    Track("Stairway to Heaven", ["Led Zeppelin"], 482, album_art_url="https://picsum.photos/300/300?random=28", preview_url="sine=f=987:d=30"),
    Track("Smells Like Teen Spirit", ["Nirvana"], 301, album_art_url="https://picsum.photos/300/300?random=29", preview_url="sine=f=1046:d=30"),
    Track("Imagine", ["John Lennon"], 183, album_art_url="https://picsum.photos/300/300?random=30", preview_url="sine=f=440:d=30"),
    Track("Sweet Child O' Mine", ["Guns N' Roses"], 356, album_art_url="https://picsum.photos/300/300?random=31", preview_url="sine=f=523:d=30"),
    Track("Thriller", ["Michael Jackson"], 357, album_art_url="https://picsum.photos/300/300?random=32", preview_url="sine=f=659:d=30"),
    Track("Hey Jude", ["The Beatles"], 431, album_art_url="https://picsum.photos/300/300?random=33", preview_url="sine=f=784:d=30"),
    Track("Purple Rain", ["Prince"], 500, album_art_url="https://picsum.photos/300/300?random=34", preview_url="sine=f=880:d=30"),
    Track("Wonderwall", ["Oasis"], 258, album_art_url="https://picsum.photos/300/300?random=35", preview_url="sine=f=330:d=30"),
    Track("Shape of You", ["Ed Sheeran"], 233, album_art_url="https://picsum.photos/300/300?random=36", preview_url="sine=f=440:d=30"),
    Track("Bad Guy", ["Billie Eilish"], 194, album_art_url="https://picsum.photos/300/300?random=37", preview_url="sine=f=523:d=30"),
    Track("Dynamite", ["BTS"], 199, album_art_url="https://picsum.photos/300/300?random=38", preview_url="sine=f=659:d=30"),
    Track("Someone Like You", ["Adele"], 285, album_art_url="https://picsum.photos/300/300?random=39", preview_url="sine=f=330:d=30"),
]

MOCK_FEATURED_PLAYLISTS = [
    {
        "name": "✨ Retro Synthwave",
        "id": "mock_featured_synth",
        "items": [
            Track("Resonance", ["Home"], 210, album_art_url="https://picsum.photos/300/300?random=40", preview_url="sine=f=330:d=30"),
            Track("Nightcall", ["Kavinsky"], 258, album_art_url="https://picsum.photos/300/300?random=41", preview_url="sine=f=440:d=30"),
            Track("Turbo Killer", ["Carpenter Brut"], 208, album_art_url="https://picsum.photos/300/300?random=42", preview_url="sine=f=523:d=30"),
        ]
    },
    {
        "name": "✨ Lo-Fi Coding Beats",
        "id": "mock_featured_lofi",
        "items": [
            Track("Coffee Breath", ["Lofi Fruits Music"], 120, album_art_url="https://picsum.photos/300/300?random=43", preview_url="sine=f=330:d=30"),
            Track("Midnight Chill", ["Sleepy Fish"], 150, album_art_url="https://picsum.photos/300/300?random=44", preview_url="sine=f=392:d=30"),
        ]
    },
    {
        "name": "🔥 Top Charts",
        "id": "mock_top_charts",
        "items": [
            Track("Blinding Lights", ["The Weeknd"], 200, album_art_url="https://picsum.photos/300/300?random=24", preview_url="sine=f=659:d=30"),
            Track("Shape of You", ["Ed Sheeran"], 233, album_art_url="https://picsum.photos/300/300?random=36", preview_url="sine=f=440:d=30"),
            Track("Dynamite", ["BTS"], 199, album_art_url="https://picsum.photos/300/300?random=38", preview_url="sine=f=659:d=30"),
            Track("Bad Guy", ["Billie Eilish"], 194, album_art_url="https://picsum.photos/300/300?random=37", preview_url="sine=f=523:d=30"),
            Track("Someone Like You", ["Adele"], 285, album_art_url="https://picsum.photos/300/300?random=39", preview_url="sine=f=330:d=30"),
        ]
    },
    {
        "name": "💡 Recommended For You",
        "id": "mock_recommended",
        "items": [
            Track("Bohemian Rhapsody", ["Queen"], 354, album_art_url="https://picsum.photos/300/300?random=23", preview_url="sine=f=587:d=30"),
            Track("Wonderwall", ["Oasis"], 258, album_art_url="https://picsum.photos/300/300?random=35", preview_url="sine=f=330:d=30"),
            Track("Imagine", ["John Lennon"], 183, album_art_url="https://picsum.photos/300/300?random=30", preview_url="sine=f=440:d=30"),
            Track("Hotel California", ["Eagles"], 390, album_art_url="https://picsum.photos/300/300?random=27", preview_url="sine=f=880:d=30"),
        ]
    },
    {
        "name": "🆕 New Releases",
        "id": "mock_new_releases",
        "items": [
            Track("Die With A Smile", ["Lady Gaga", "Bruno Mars"], 251, album_art_url="https://picsum.photos/300/300?random=50", preview_url="sine=f=523:d=30"),
            Track("APT.", ["ROSÉ", "Bruno Mars"], 173, album_art_url="https://picsum.photos/300/300?random=51", preview_url="sine=f=659:d=30"),
            Track("Please Please Please", ["Sabrina Carpenter"], 185, album_art_url="https://picsum.photos/300/300?random=52", preview_url="sine=f=784:d=30"),
        ]
    },
]

# Podcast episodes modelled as tracks with a special sentinel prefix
MOCK_PODCASTS = [
    {
        "name": "🎙️ Lex Fridman Podcast",
        "id": "mock_podcast_lex",
        "is_podcast": True,
        "items": [
            Track("Elon Musk: SpaceX, Tesla, X, AI", ["Lex Fridman"], 10800, album_art_url="https://picsum.photos/300/300?random=60", preview_url="sine=f=220:d=30"),
            Track("Sam Altman: OpenAI, GPT-5", ["Lex Fridman"], 9000, album_art_url="https://picsum.photos/300/300?random=61", preview_url="sine=f=220:d=30"),
        ]
    },
    {
        "name": "🎙️ How I Built This",
        "id": "mock_podcast_hibt",
        "is_podcast": True,
        "items": [
            Track("Airbnb: Brian Chesky", ["Guy Raz"], 3600, album_art_url="https://picsum.photos/300/300?random=62", preview_url="sine=f=220:d=30"),
            Track("Duolingo: Luis von Ahn", ["Guy Raz"], 2700, album_art_url="https://picsum.photos/300/300?random=63", preview_url="sine=f=220:d=30"),
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
        
    def play(self, preview_url: str, start_offset: float = 0) -> bool:
        """Play audio from URL using system player"""
        try:
            self.stop()
            ffplay_vol = str(self.volume)
            vlc_vol = str(int(self.volume * 2.56))
            
            if preview_url.startswith("sine="):
                cmd = ['ffplay', '-f', 'lavfi', '-i', preview_url, '-autoexit', '-nodisp', '-loglevel', 'quiet', '-volume', ffplay_vol]
                if start_offset > 0:
                    cmd.insert(1, '-ss')
                    cmd.insert(2, str(start_offset))
                try:
                    self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.is_playing = True
                    return True
                except FileNotFoundError:
                    pass

            ffplay_cmd = ['ffplay']
            if start_offset > 0:
                ffplay_cmd += ['-ss', str(start_offset)]
            ffplay_cmd += ['-nodisp', '-autoexit', '-loglevel', 'quiet', '-volume', ffplay_vol, preview_url]

            vlc_cmd = ['cvlc', '--play-and-exit', '--no-video', '--volume', vlc_vol]
            if start_offset > 0:
                vlc_cmd += ['--start-time', str(start_offset)]
            vlc_cmd += [preview_url]

            players = [
                (ffplay_cmd, True),
                (vlc_cmd, False),
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
            
            self.is_playing = True
            return False
            
        except Exception:
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
        async def load_art():
            try:
                def fetch_and_generate():
                    return generate_ascii_art_from_url(url, width=28, height=14)
                ascii_art = await asyncio.to_thread(fetch_and_generate)
                self.art_content = ascii_art
            except Exception:
                self.art_content = generate_fallback_art()
        asyncio.create_task(load_art())
        
    def set_fallback_art(self) -> None:
        self.art_content = generate_fallback_art()
        
    def render(self):
        if not self.art_content:
            return "[dim]No album art[/dim]"
            
        # If it is high-detail ANSI color block art (contains color brackets/on), return Text directly
        if "#" in self.art_content or "on" in self.art_content:
            from rich.text import Text
            return Text.from_markup(self.art_content)
            
        art_lines = self.art_content.splitlines()
        colored_art = []
        for i, line in enumerate(art_lines):
            color = gradient_color(i / len(art_lines))
            colored_art.append(f"[{color}]{line}[/{color}]")
        from rich.text import Text
        return Text.from_markup("\n".join(colored_art))

# Enhanced Progress Bar
class MusicProgressBar(Static):
    progress = reactive(0.0)
    duration = reactive(0)
    
    class TrackEnded(Message):
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
                self.refresh(layout=True)
                self.post_message(self.TrackEnded())
            else:
                self.refresh(layout=True)
            
    def play(self, duration: int) -> None:
        self.duration = duration
        self.start_time = time.time() - self.current_position
        self.playing = True
        self.refresh(layout=True)
        
    def pause(self) -> None:
        self.playing = False
        
    def stop(self) -> None:
        self.playing = False
        self.current_position = 0
        self.progress = 0
        self.refresh(layout=True)
        
    def render(self) -> str:
        if self.duration == 0:
            return "[dim]--:-- / --:--[/dim]"
            
        width = max(10, (self.size.width - 14) if self.size else 35)
        filled_width = int(self.progress * width)
        bar = "█" * filled_width + "─" * (width - filled_width)
        
        elapsed = int(self.current_position)
        total = self.duration
        elapsed_str = format_duration(elapsed)
        total_str = format_duration(total)
        
        controls = "⏮   ▶   ⏭" if self.playing else "⏮   ⏸   ⏭"
        total_line_w = width + 12
        
        return f"[bold white]{controls:^{total_line_w}}[/bold white]\n{elapsed_str} [#1db954]{bar}[/] {total_str}"

    def on_click(self, event: events.Click) -> None:
        if self.duration <= 0 or event.y != 1:
            return
            
        elapsed = int(self.current_position)
        elapsed_str = format_duration(elapsed)
        bar_start = len(elapsed_str) + 1
        width = max(10, (self.size.width - 14) if self.size else 35)
        
        if bar_start <= event.x < bar_start + width:
            click_fraction = (event.x - bar_start) / width
            target_pos = self.duration * click_fraction
            self.app.seek_to_position(target_pos)

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
        height = self.size.height if (self.size and self.size.height > 4) else 15
        
        num_w = 4
        like_w = 3
        dur_w = 6
        remaining = width - num_w - like_w - dur_w - 6
        if remaining < 10:
            remaining = 10
        title_w = int(remaining * 0.6)
        artist_w = remaining - title_w
        
        header = f"[dim]{'#'.ljust(num_w)} {' '.ljust(like_w)} {'Title'.ljust(title_w)} {'Artist'.ljust(artist_w)} {'Duration'.rjust(dur_w)}[/dim]"
        divider = f"[dim]{'─' * width}[/dim]"
        
        # Calculate viewport slice to make it scrollable
        visible_height = height - 2
        if visible_height < 1:
            visible_height = 1
            
        if len(self.tracks) <= visible_height:
            start_idx = 0
            end_idx = len(self.tracks)
        else:
            start_idx = max(0, self.selected_index - visible_height // 2)
            end_idx = start_idx + visible_height
            if end_idx > len(self.tracks):
                end_idx = len(self.tracks)
                start_idx = max(0, end_idx - visible_height)
                
        self.start_idx = start_idx
        
        lines = [header, divider]
        for idx in range(start_idx, end_idx):
            track = self.tracks[idx]
            track_num = f"{idx + 1}"
            track_name = track.name
            artists = ', '.join(track.artists)
            duration = format_duration(track.duration)
            
            t_name = track_name[:title_w].ljust(title_w)
            t_artists = artists[:artist_w].ljust(artist_w)
            
            tid = track.id or track.preview_url or track.name
            is_liked = tid in getattr(self.app, "liked_track_ids", set())
            like_symbol = "[#e91429]♥[/#e91429]" if is_liked else "[dim]♡[/dim]"
            
            is_playing_track = (self.app.current_track is not None and 
                                 (self.app.current_track.id == track.id if (track.id and self.app.current_track.id) else 
                                  (self.app.current_track.preview_url == track.preview_url or self.app.current_track.name == track.name)))
            
            play_indicator = ""
            if is_playing_track:
                play_indicator = "🔊" if self.app.is_playing else "⏸"
            
            if idx == self.selected_index:
                prefix = f"▶ {play_indicator}".ljust(num_w)
                if is_playing_track:
                    lines.append(f"[bold #1db954]{prefix} {like_symbol} {t_name} {t_artists} {duration.rjust(dur_w)}[/bold #1db954]")
                else:
                    lines.append(f"[bold #1db954]▶   {like_symbol} {t_name} {t_artists} {duration.rjust(dur_w)}[/bold #1db954]")
            else:
                if is_playing_track:
                    prefix = f"  {play_indicator}".ljust(num_w)
                    lines.append(f"[bold white]{prefix} {like_symbol} {t_name} {t_artists} {duration.rjust(dur_w)}[/bold white]")
                else:
                    prefix = f"{track_num}".ljust(num_w)
                    lines.append(f"[dim]{prefix}[/dim] {like_symbol} [white]{t_name}[/white] [dim]{t_artists}[/dim] [dim]{duration.rjust(dur_w)}[/dim]")
                
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
        elif event.key == "f":
            track = self.get_selected_track()
            if track:
                self.app.toggle_like_track(track)
            event.stop()
            event.prevent_default()
        elif event.key == "e":
            track = self.get_selected_track()
            if track:
                self.app.enqueue_track(track)
            event.stop()
            event.prevent_default()

    def on_click(self, event: events.Click) -> None:
        if not self.tracks:
            return
            
        start_idx = getattr(self, "start_idx", 0)
        index = start_idx + (event.y - 2)
        if 0 <= index < len(self.tracks):
            self.selected_index = index
            self.refresh()
            track = self.tracks[index]
            self.app._play_track(track)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        if self.select_next():
            event.prevent_default()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.select_previous():
            event.prevent_default()

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
            
        height = self.size.height if (self.size and self.size.height > 0) else 15
        visible_height = height
        if visible_height < 1:
            visible_height = 1
            
        if len(self.playlists) <= visible_height:
            start_idx = 0
            end_idx = len(self.playlists)
        else:
            start_idx = max(0, self.selected_index - visible_height // 2)
            end_idx = start_idx + visible_height
            if end_idx > len(self.playlists):
                end_idx = len(self.playlists)
                start_idx = max(0, end_idx - visible_height)
                
        self.start_idx = start_idx
        
        lines = []
        for idx in range(start_idx, end_idx):
            playlist = self.playlists[idx]
            name = playlist['name']
            track_count = len(playlist.get('items', []))
            
            # Detect special icon from prefix
            icon = "🎧"
            display_name = name
            for emoji in ["✨", "🔥", "💡", "🆕", "🎙️"]:
                if name.startswith(emoji):
                    icon = emoji
                    display_name = name[len(emoji):].strip()
                    break
            
            if idx == self.selected_index:
                lines.append(f"[bold #1db954]▶ {icon} {display_name} ({track_count})[/bold #1db954]")
            else:
                lines.append(f"   {icon} {display_name}")
                
        return "\n".join(lines)

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self.select_previous()
            self.app._update_track_list()
            event.prevent_default()
        elif event.key == "down":
            self.select_next()
            self.app._update_track_list()
            event.prevent_default()

    def on_click(self, event: events.Click) -> None:
        if not self.playlists:
            return
            
        start_idx = getattr(self, "start_idx", 0)
        index = start_idx + event.y
        if 0 <= index < len(self.playlists):
            self.selected_index = index
            self.refresh()
            self.app._update_track_list()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        if self.select_next():
            self.app._update_track_list()
            event.prevent_default()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.select_previous():
            self.app._update_track_list()
            event.prevent_default()

# Now Playing Widget
class NowPlaying(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_track = None
        
    def on_mount(self) -> None:
        self.set_interval(0.15, self.tick_visualizer)
        
    def tick_visualizer(self) -> None:
        if self.app.is_playing:
            self.refresh()
            
    def set_track(self, track: Optional[Track]) -> None:
        self.current_track = track
        self.refresh()
        
    def render(self) -> str:
        if not self.current_track:
            return "[dim]No track playing[/dim]\n\n[dim]Select a track and press Space/s to play[/dim]"
            
        track_name = self.current_track.name
        artists = ', '.join(self.current_track.artists)
        
        source = getattr(self.app, "audio_source", "none")
        if source == "connect":
            audio_info = "🔊 [green]Spotify Connect[/green]"
        elif source == "youtube":
            audio_info = "🔊 [green]YouTube Stream[/green]"
        elif source == "preview":
            audio_info = "🔊 [green]Spotify Preview[/green]"
        elif source == "synth":
            audio_info = "🔊 [cyan]Local Synth[/cyan]"
        else:
            audio_info = "🔇 [dim]No Audio[/dim]"
            
        tid = self.current_track.id or self.current_track.preview_url or self.current_track.name
        is_liked = tid in getattr(self.app, "liked_track_ids", set())
        like_indicator = " [#e91429]♥[/]" if is_liked else ""
        
        # Audio Visualizer section (vertical ASCII equalizer)
        if self.app.is_playing:
            heights = [random.randint(1, 4) for _ in range(6)]
            eq_lines = []
            for r in reversed(range(1, 5)):
                row_chars = []
                for h in heights:
                    if h >= r:
                        row_chars.append("█")
                    elif h + 1 == r:
                        row_chars.append("▄")
                    else:
                        row_chars.append(" ")
                eq_lines.append("[#1db954]" + "  ".join(row_chars) + "[/]")
            visualizer_display = "\n" + "\n".join(eq_lines)
        else:
            visualizer_display = "\n\n\n\n[dim]▄  ▄  ▄  ▄  ▄  ▄[/dim]"
            
        return f"[bold white]{track_name}{like_indicator}[/bold white]\n[#b3b3b3]by {artists}[/#b3b3b3]\n\n{audio_info}\n{visualizer_display}"

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
        if self.repeat == "track":
            rep_status = "[bold #1db954]REP1[/]"
        elif self.repeat == "context":
            rep_status = "[bold #1db954]REP∞[/]"
        else:
            rep_status = "[dim]REP[/]"
        
        return f"\n{vol_line}\n\n{shuf_status}   {rep_status}"

    def on_click(self, event: events.Click) -> None:
        if event.y == 1:
            bar_start = 3
            vol_width = 10
            if bar_start <= event.x < bar_start + vol_width:
                click_fraction = (event.x - bar_start) / vol_width
                target_volume = int(click_fraction * 100)
                target_volume = round(target_volume / 10) * 10
                target_volume = max(0, min(100, target_volume))
                
                self.app.music_player.set_volume(target_volume)
                self.volume = self.app.music_player.volume
                self.app.notify(f"Volume: {self.volume}%")
                if self.app.sp and getattr(self.app, "audio_source", "none") == "connect":
                    def set_spotify_volume():
                        try:
                            self.app.sp.volume(self.volume)
                        except Exception:
                            pass
                    import threading
                    threading.Thread(target=set_spotify_volume, daemon=True).start()
        elif event.y == 3:
            if 0 <= event.x < 4:
                self.app.action_toggle_shuffle()
            elif 7 <= event.x < 12:
                self.app.action_toggle_repeat()

def open_browser_silently(url):
    import os
    import sys
    import subprocess
    try:
        with open(os.devnull, "wb") as devnull:
            subprocess.Popen(["xdg-open", url], stdout=devnull, stderr=devnull)
            return
    except Exception:
        pass
    try:
        import webbrowser
        null_fd = os.open(os.devnull, os.O_RDWR)
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        try:
            os.dup2(null_fd, 1)
            os.dup2(null_fd, 2)
            webbrowser.open(url)
        finally:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(null_fd)
            os.close(old_stdout)
            os.close(old_stderr)
    except Exception:
        pass

def ensure_spotifyd_binary():
    import os
    import urllib.request
    import tarfile
    import platform
    
    if os.path.exists("./spotifyd"):
        try:
            os.chmod("./spotifyd", 0o755)
        except Exception:
            pass
        return True
        
    try:
        arch = platform.machine()
        if arch == "x86_64":
            url = "https://github.com/Spotifyd/spotifyd/releases/download/v0.4.2/spotifyd-linux-x86_64-default.tar.gz"
        elif "arm" in arch or "aarch64" in arch:
            url = "https://github.com/Spotifyd/spotifyd/releases/download/v0.4.2/spotifyd-linux-aarch64-default.tar.gz"
        else:
            return False
            
        urllib.request.urlretrieve(url, "spotifyd.tar.gz")
        with tarfile.open("spotifyd.tar.gz", "r:gz") as tar:
            tar.extractall()
        if os.path.exists("spotifyd.tar.gz"):
            os.remove("spotifyd.tar.gz")
        os.chmod("./spotifyd", 0o755)
        return True
    except Exception:
        return False

class HelpScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container(id="help-modal-container"):
            yield Label("🎵 RetroSpotify Help & Keybindings 🎵", id="help-modal-title")
            yield Static(
                "[bold green]Playback Control:[/bold green]\n"
                "  • [white]Space / s[/] : Play / Pause current track\n"
                "  • [white]n / p[/]       : Next / Previous track\n"
                "  • [white]S[/]           : Toggle Shuffle mode\n"
                "  • [white]R[/]           : Toggle Repeat mode (Off / Track / Playlist)\n"
                "  • [white]+ / -[/]       : Increase / Decrease Volume\n\n"
                "[bold green]Navigation & Playlists:[/bold green]\n"
                "  • [white]l / h[/]       : Next / Previous playlist in Sidebar\n"
                "  • [white]Up / Down[/]   : Move selection in track list or sidebar\n"
                "  • [white]Enter[/]       : Play selected track\n"
                "  • [white]r[/]           : Refresh Spotify playlists / data\n\n"
                "[bold green]Advanced Features:[/bold green]\n"
                "  • [white]/[/]           : Search tracks (Press Esc to close search)\n"
                "  • [white]f[/]           : Favorite (Like/Unlike) current track ♥\n"
                "  • [white]e[/]           : Enqueue selected track to Play Queue\n"
                "  • [white]d[/]           : Switch Spotify playback device (Connect)\n"
                "  • [white]T[/]           : Open Settings (Profile, App settings)\n"
                "  • [white]a[/]           : Go to Authentication screen\n"
                "  • [white]q / Esc[/]     : Quit / Close this help menu\n\n"
                "[bold green]Troubleshooting:[/bold green]\n"
                "  • Make sure Spotify Premium is active for Connect playback.\n"
                "  • Run `spotifyd` locally or link your device if no audio plays.\n"
                "  • Install `ffmpeg` (ffplay) or `vlc` for fallback local audio.",
                id="help-modal-content"
            )
            yield Button("Close", id="btn-close-help", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "question_mark", "enter", "space"):
            self.app.pop_screen()
class SettingsScreen(Screen):
    def __init__(self, *args, **kwargs):
        kwargs["id"] = "settings"
        super().__init__(*args, **kwargs)
        
    def compose(self) -> ComposeResult:
        yield Header()
        
        # Get Spotify current user info if authenticated
        username = "Not Connected"
        email = "Not Connected"
        plan = "None"
        country = "N/A"
        if self.app.sp:
            try:
                user_info = self.app.sp.current_user()
                username = user_info.get("display_name") or user_info.get("id") or username
                email = user_info.get("email") or email
                plan = user_info.get("product", "free")
                country = user_info.get("country") or country
            except Exception:
                pass
                
        profile_header = f"👤 Account: {username} ({email}) • Plan: {plan.upper()} • Country: {country}"
        
        with ScrollableContainer(id="settings-scroll-container"):
            with Container(id="settings-container"):
                yield Static("⚙️ RetroSpotify Settings ⚙️", id="settings-title")
                yield Static(profile_header, id="settings-profile-header")
                
                with Horizontal(id="settings-form"):
                    # Left Column: API Settings
                    with Vertical(classes="settings-col"):
                        yield Static("🔌 Spotify API Credentials", classes="settings-section-title")
                        
                        yield Label("Spotify Client ID:")
                        yield Input(
                            placeholder="Enter Client ID...",
                            id="settings-client-id",
                            value=os.getenv("SPOTIPY_CLIENT_ID") or "906b96c8bfe0473792881c6b128c560b"
                        )
                        
                        yield Label("Spotify Client Secret:")
                        yield Input(
                            placeholder="Enter Client Secret (Optional for PKCE)...",
                            id="settings-client-secret",
                            password=True,
                            value=os.getenv("SPOTIPY_CLIENT_SECRET", "")
                        )
                        
                        yield Label("Redirect URI:")
                        yield Input(
                            placeholder="http://127.0.0.1:8888/callback",
                            id="settings-redirect-uri",
                            value=os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
                        )
                        
                        # App cache settings
                        yield Label("App Cache Size:")
                        cache_size_str = "0 MB"
                        cache_path = get_spotify_cache_path()
                        if os.path.exists(cache_path):
                            try:
                                size = os.path.getsize(cache_path)
                                cache_size_str = f"{size / 1024 / 1024:.2f} MB"
                            except Exception:
                                pass
                        yield Static(f"Web API Cache: {cache_size_str}", id="settings-cache-info")
                        yield Button("Clear Web API Cache", id="btn-settings-clear-app-cache", variant="warning")
                        
                    # Right Column: Daemon & Auth
                    with Vertical(classes="settings-col"):
                        yield Static("🔊 Local Player Daemon (spotifyd)", classes="settings-section-title")
                        
                        yield Label("Spotify Username / Email:", id="settings-username-label")
                        yield Input(
                            placeholder="Enter Spotify email or username...",
                            id="settings-username",
                            value=os.getenv("SPOTIPY_USERNAME", "")
                        )
                        
                        yield Label("Spotify Password (for daemon auto-login):", id="settings-password-label")
                        yield Input(
                            placeholder="Enter Spotify password...",
                            id="settings-password",
                            password=True,
                            value=os.getenv("SPOTIPY_PASSWORD", "")
                        )
                        
                        yield Label("Device Name:")
                        yield Input(
                            placeholder="RetroSpotify",
                            id="settings-device-name",
                            value=os.getenv("SPOTIPY_DEVICE_NAME", "RetroSpotify")
                        )
                        
                        yield Label("Audio Backend:")
                        yield Input(
                            placeholder="pulseaudio",
                            id="settings-backend",
                            value=os.getenv("SPOTIPY_AUDIO_BACKEND", "pulseaudio")
                        )
                        
                        yield Label("Bitrate (96, 160, 320):")
                        yield Input(
                            placeholder="320",
                            id="settings-bitrate",
                            value=os.getenv("SPOTIPY_BITRATE", "320")
                        )
                        
                        yield Button("Clear Player Daemon Cache", id="btn-settings-clear-player-cache", variant="warning")
                        
                yield Static("", id="settings-status-message")
                
                with Horizontal(classes="settings-actions-row"):
                    yield Button("Save & Apply Settings", id="btn-settings-save", variant="success")
                    yield Button("Cancel", id="btn-settings-cancel")
                    yield Button("Log Out / Reset Auth", id="btn-settings-logout", variant="error")
                    
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-settings-cancel":
            self.app.pop_screen()
            
        elif event.button.id == "btn-settings-clear-app-cache":
            cache_path = get_spotify_cache_path()
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    self.notify("Web API cache cleared!")
                    self.query_one("#settings-cache-info", Static).update("Web API Cache: 0 MB")
                except Exception as e:
                    self.notify(f"Could not clear cache: {e}", severity="error")
            else:
                self.notify("No Web API cache found.")
                
        elif event.button.id == "btn-settings-clear-player-cache":
            import shutil
            if os.path.exists("./spotifyd_cache"):
                try:
                    shutil.rmtree("./spotifyd_cache")
                    os.makedirs("./spotifyd_cache", exist_ok=True)
                    self.notify("Player daemon cache cleared!")
                except Exception as e:
                    self.notify(f"Could not clear cache: {e}", severity="error")
            else:
                self.notify("No player daemon cache found.")
                
        elif event.button.id == "btn-settings-logout":
            # 1. Stop spotifyd daemon
            self.app.stop_spotifyd()
            
            # 2. Delete cache files
            cache_path = get_spotify_cache_path()
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            import shutil
            if os.path.exists("./spotifyd_cache"):
                try:
                    shutil.rmtree("./spotifyd_cache")
                except Exception:
                    pass
                    
            # 3. Clear environment and delete .env
            os.environ.pop("SPOTIPY_CLIENT_ID", None)
            os.environ.pop("SPOTIPY_CLIENT_SECRET", None)
            os.environ.pop("SPOTIPY_REDIRECT_URI", None)
            os.environ.pop("SPOTIPY_USERNAME", None)
            os.environ.pop("SPOTIPY_PASSWORD", None)
            os.environ.pop("SPOTIPY_DEVICE_NAME", None)
            os.environ.pop("SPOTIPY_AUDIO_BACKEND", None)
            os.environ.pop("SPOTIPY_BITRATE", None)
            
            if os.path.exists(".env"):
                try:
                    os.remove(".env")
                except Exception:
                    pass
                    
            if os.path.exists("spotifyd.conf"):
                try:
                    os.remove("spotifyd.conf")
                except Exception:
                    pass
                    
            self.app.sp = None
            self.app.current_device_id = None
            
            self.notify("Logged out successfully!")
            # Pop screens to get back to Welcome
            while self.app.screen.id != "welcome":
                try:
                    self.app.pop_screen()
                except Exception:
                    break
            self.app.switch_screen("welcome")
            
        elif event.button.id == "btn-settings-save":
            client_id = self.query_one("#settings-client-id", Input).value.strip()
            client_secret = self.query_one("#settings-client-secret", Input).value.strip()
            redirect_uri = self.query_one("#settings-redirect-uri", Input).value.strip()
            
            username = self.query_one("#settings-username", Input).value.strip()
            password = self.query_one("#settings-password", Input).value.strip()
            device_name = self.query_one("#settings-device-name", Input).value.strip() or "RetroSpotify"
            backend = self.query_one("#settings-backend", Input).value.strip() or "pulseaudio"
            bitrate = self.query_one("#settings-bitrate", Input).value.strip() or "320"
            
            if not client_id:
                self.query_one("#settings-status-message", Static).update("Error: Spotify Client ID is required")
                return
                
            # Update environment
            os.environ["SPOTIPY_CLIENT_ID"] = client_id
            os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri
            if client_secret:
                os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
            else:
                os.environ.pop("SPOTIPY_CLIENT_SECRET", None)
                
            if username:
                os.environ["SPOTIPY_USERNAME"] = username
            else:
                os.environ.pop("SPOTIPY_USERNAME", None)
                
            if password:
                os.environ["SPOTIPY_PASSWORD"] = password
            else:
                os.environ.pop("SPOTIPY_PASSWORD", None)
                
            os.environ["SPOTIPY_DEVICE_NAME"] = device_name
            os.environ["SPOTIPY_AUDIO_BACKEND"] = backend
            os.environ["SPOTIPY_BITRATE"] = bitrate
            
            # Save to .env file
            with open(".env", "w") as f:
                f.write(f"SPOTIPY_CLIENT_ID={client_id}\n")
                if client_secret:
                    f.write(f"SPOTIPY_CLIENT_SECRET={client_secret}\n")
                f.write(f"SPOTIPY_REDIRECT_URI={redirect_uri}\n")
                if username:
                    f.write(f"SPOTIPY_USERNAME={username}\n")
                if password:
                    f.write(f"SPOTIPY_PASSWORD={password}\n")
                f.write(f"SPOTIPY_DEVICE_NAME={device_name}\n")
                f.write(f"SPOTIPY_AUDIO_BACKEND={backend}\n")
                f.write(f"SPOTIPY_BITRATE={bitrate}\n")
                
            self.notify("Settings saved!")
            
            # Apply changes by restarting spotifyd if it is enabled and we are not in mock mode
            if not self.app.force_mock and self.app.use_spotifyd:
                self.app.start_spotifyd()
                
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "t", "T"):
            self.app.pop_screen()
            event.prevent_default()


class DevicesScreen(ModalScreen):
    def __init__(self, devices: List[Dict], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices = devices
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="devices-modal-container"):
            yield Label("📱 Spotify Connect Devices 📱", id="devices-modal-title")
            yield Static(id="devices-list-content")
            yield Label("Press [green]Enter[/] to connect, [green]Esc[/] to cancel.", id="devices-modal-footer")

    def on_mount(self) -> None:
        self.update_list()

    def update_list(self) -> None:
        if not self.devices:
            self.query_one("#devices-list-content", Static).update(
                "[dim]No active Spotify devices found.[/dim]\n"
                "[yellow]Start spotifyd or open Spotify on your phone/computer.[/yellow]"
            )
            return

        lines = []
        for i, device in enumerate(self.devices):
            active_str = "● [green]Active[/]" if device.get("is_active") else "○ [dim]Idle[/]"
            device_type = device.get("type", "Unknown")
            icon = "💻" if device_type.lower() == "computer" else "📱" if device_type.lower() == "smartphone" else "🔊"

            if i == self.selected_index:
                lines.append(f"[bold #1db954]▶ {icon} {device.get('name')} ({device_type}) - {active_str}[/bold #1db954]")
            else:
                lines.append(f"  {icon} {device.get('name')} ({device_type}) - {active_str}")

        self.query_one("#devices-list-content", Static).update("\n".join(lines))

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                self.update_list()
            event.prevent_default()
        elif event.key == "down":
            if self.selected_index < len(self.devices) - 1:
                self.selected_index += 1
                self.update_list()
            event.prevent_default()
        elif event.key == "enter":
            if self.devices and 0 <= self.selected_index < len(self.devices):
                selected_device = self.devices[self.selected_index]
                self.dismiss(selected_device)
            else:
                self.dismiss(None)
            event.prevent_default()
        elif event.key == "escape" or event.key == "d":
            self.dismiss(None)
            event.prevent_default()


class SpotifydAuthScreen(Screen):
    def __init__(self, *args, **kwargs):
        kwargs["id"] = "spotifyd-auth"
        super().__init__(*args, **kwargs)
        self.auth_process = None
        self.auth_url = ""
        self.polling_task = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="login-container"):
            yield Static("Local Spotify Player Setup 🔊", id="login-title")
            
            # Step 1: Start Auth
            with Vertical(id="step-init-auth"):
                yield Label("To stream full-length audio directly from Spotify, we need to authorize our local player daemon (spotifyd).")
                yield Static("\nThis daemon runs in the background and acts as a local Spotify Connect device.", id="welcome-subtitle")
                with Horizontal(classes="login-actions-row"):
                    yield Button("Authorize Player", id="btn-start-auth", variant="success")
                    yield Button("Skip / Use Fallback", id="btn-skip-auth")

            # Step 2: Waiting for browser
            with Vertical(id="step-waiting-auth", classes="hidden"):
                yield Label("1. Click/Open this link in your browser:")
                auth_url_display = Input(id="spotifyd-auth-url-display")
                auth_url_display.read_only = True
                yield auth_url_display
                
                with Horizontal(classes="login-actions-row"):
                    yield Button("Open Link", id="btn-open-spotifyd-link", variant="primary")
                    yield Button("Cancel", id="btn-cancel-auth")
                
                yield Label("\n2. Log in and agree in the browser tab.")
                yield Static("⏳ Waiting for authentication in browser...", id="spotifyd-auth-status")
                
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-skip-auth":
            self.app.use_spotifyd = False
            self.app.switch_screen("player")
            
        elif event.button.id == "btn-start-auth":
            self.query_one("#step-init-auth", Vertical).add_class("hidden")
            self.query_one("#step-waiting-auth", Vertical).remove_class("hidden")
            self.run_spotifyd_auth()
            
        elif event.button.id == "btn-open-spotifyd-link":
            if self.auth_url:
                open_browser_silently(self.auth_url)
                
        elif event.button.id == "btn-cancel-auth":
            self.stop_spotifyd_auth()
            self.query_one("#step-waiting-auth", Vertical).add_class("hidden")
            self.query_one("#step-init-auth", Vertical).remove_class("hidden")

    def run_spotifyd_auth(self) -> None:
        self.stop_spotifyd_auth()
        try:
            cmd = ["./spotifyd", "authenticate", "--cache-path", "./spotifyd_cache", "--oauth-port", "8001"]
            self.auth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            async def find_url():
                def read_stdout():
                    for line in self.auth_process.stdout:
                        if "Browse to:" in line:
                            return line.split("Browse to:")[1].strip()
                    return None
                
                url = await asyncio.to_thread(read_stdout)
                if url:
                    self.auth_url = url
                    self.query_one("#spotifyd-auth-url-display", Input).value = url
                    open_browser_silently(url)
                    self.start_credentials_polling()
                else:
                    self.query_one("#spotifyd-auth-status", Static).update("[red]Error starting authentication daemon[/]")
            
            asyncio.create_task(find_url())
            
        except Exception as e:
            self.query_one("#spotifyd-auth-status", Static).update(f"[red]Error: {e}[/]")

    def start_credentials_polling(self) -> None:
        async def poll_credentials():
            for _ in range(300):
                if self.app.check_spotifyd_authenticated():
                    self.stop_spotifyd_auth()
                    self.app.notify("Spotify Player authorized successfully!")
                    self.app.start_spotifyd()
                    self.app.switch_screen("player")
                    return
                await asyncio.sleep(1)
            self.query_one("#spotifyd-auth-status", Static).update("[red]Authentication timed out. Please try again.[/]")
            self.stop_spotifyd_auth()

        self.polling_task = asyncio.create_task(poll_credentials())

    def stop_spotifyd_auth(self) -> None:
        if self.polling_task:
            self.polling_task.cancel()
            self.polling_task = None
        if self.auth_process:
            try:
                self.auth_process.terminate()
                self.auth_process.wait(timeout=1)
            except Exception:
                try:
                    self.auth_process.kill()
                except Exception:
                    pass
            self.auth_process = None


# Welcome Screen
class WelcomeScreen(Screen):
    def __init__(self, *args, **kwargs):
        kwargs["id"] = "welcome"
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="welcome-container"):
            yield Static(ASCII_LOGO, id="welcome-logo")
            yield Static("Welcome to RetroSpotify", id="welcome-title")
            yield Static("Select your login mode to begin:", id="welcome-subtitle")
            
            with Vertical(id="options-list"):
                 yield Button("1. Login with Spotify (Email, Google, Apple, etc.)", id="btn-login", variant="success")
                 yield Button("2. Explore Offline (Mock Mode)", id="btn-mock")
                 yield Button("3. About / Credits", id="btn-about")
                 
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-login":
            self.app.push_screen(LoginScreen())
        elif event.button.id == "btn-mock":
            self.app.start_mock_mode()
        elif event.button.id == "btn-about":
            self.app.push_screen(AboutScreen())


# About Screen Modal Dialog
class AboutScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container(id="about-modal-container"):
            yield Label("💚 About RetroSpotify 💚", id="about-modal-title")
            yield Static(
                "[bold]RetroSpotify v1.2.0[/bold]\n\n"
                "A nostalgic, terminal-based Spotify client that blends retro command-line vibes with modern playback controls.\n\n"
                "[bold green]Developer:[/bold green]\n"
                "• Vaibhav Rathod (GitHub: [bold white]vaibhav-rm[/bold white])\n\n"
                "[bold green]Key Technologies & Credits:[/bold green]\n"
                "• [bold white]Textual[/bold white] - Modern terminal application framework for Python.\n"
                "• [bold white]Spotipy[/bold white] - Python library for the Spotify Web API.\n"
                "• [bold white]spotifyd[/bold white] - Lightweight background music streaming daemon.\n\n"
                "You can log in to your standard Spotify account securely using the official browser-based authentication flow.",
                id="about-modal-content"
            )
            yield Button("Close", id="btn-about-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-about-close":
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "enter", "space"):
            self.app.pop_screen()


def update_env_var(key, value):
    lines = []
    if os.path.exists(".env"):
        try:
            with open(".env", "r") as f:
                lines = f.readlines()
        except Exception:
            pass
    key_found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    if not key_found:
        new_lines.append(f"{key}={value}\n")
    try:
        with open(".env", "w") as f:
            f.writelines(new_lines)
    except Exception:
        pass


import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class CallbackHandler(BaseHTTPRequestHandler):
    def __init__(self, callback_func, *args, **kwargs):
        self.callback_func = callback_func
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Suppress logging to keep stdin/stdout clean
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/callback":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Send success response to browser
            html = """
            <html>
            <head>
                <title>RetroSpotify Login Successful</title>
                <style>
                    body { background: #121212; color: #ffffff; font-family: sans-serif; text-align: center; padding-top: 50px; }
                    h1 { color: #1db954; }
                    p { color: #b3b3b3; }
                </style>
            </head>
            <body>
                <h1>💚 RetroSpotify Login Successful! </h1>
                <p>You have successfully logged in. You can close this browser tab and return to the terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
            
            host = self.headers.get("Host", "127.0.0.1:8888")
            full_url = f"http://{host}{self.path}"
            
            # Trigger the text app callback
            self.callback_func(full_url)
        else:
            self.send_response(404)
            self.end_headers()

def make_handler(callback_func):
    class CustomCallbackHandler(CallbackHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(callback_func, *args, **kwargs)
    return CustomCallbackHandler


# Login Configuration Screen
class LoginScreen(Screen):
    def __init__(self, *args, **kwargs):
        kwargs["id"] = "login"
        super().__init__(*args, **kwargs)
        self.auth_manager = None
        self.auth_url = ""
        self.http_server = None
        self.server_thread = None
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="login-container"):
            yield Static("Spotify Email Login 📧", id="login-title")
            
            # Credentials Step Block
            with Vertical(id="step-credentials"):
                yield Label("Spotify Email / Username (Optional):")
                yield Input(placeholder="Enter Spotify email...", id="input-username", value=os.getenv("SPOTIPY_USERNAME", ""))
                
                yield Static("", id="login-status-credentials")
                
                with Horizontal(classes="login-actions-row"):
                    yield Button("Next", id="btn-next", variant="success")
                    yield Button("Cancel", id="btn-cancel-credentials")
            
            # Authorize Step Block (initially hidden)
            with Vertical(id="step-authorize", classes="hidden"):
                yield Label("1. Click/Open this link in your browser:")
                auth_url_display = Input(id="auth-url-display")
                auth_url_display.read_only = True
                yield auth_url_display
                yield Button("Copy Link to Clipboard", id="btn-copy-link")
                
                yield Label("2. Paste the full redirected browser URL here:")
                yield Input(placeholder="http://127.0.0.1:8888/callback?code=...", id="input-redirected-url")
                
                yield Static("", id="login-status-authorize")
                
                with Horizontal(classes="login-actions-row"):
                    yield Button("Connect", id="btn-connect", variant="success")
                    yield Button("Back", id="btn-back")
                
        yield Footer()

    def on_unmount(self) -> None:
        self.stop_callback_server()

    def start_callback_server(self, redirect_uri: str) -> None:
        try:
            parsed = urllib.parse.urlparse(redirect_uri)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8888
            
            def on_redirect_received(full_url):
                self.app.call_from_thread(self.handle_auto_login, full_url)
                
            handler_class = make_handler(on_redirect_received)
            self.http_server = HTTPServer((host, port), handler_class)
            
            def run_server():
                try:
                    if self.http_server:
                        self.http_server.handle_request()
                except Exception:
                    pass
                finally:
                    if self.http_server:
                        try:
                            self.http_server.server_close()
                        except Exception:
                            pass
                        self.http_server = None
                        
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.query_one("#login-status-authorize", Static).update("[green]⚡ Waiting for browser login redirect on port " + str(port) + "...[/]")
        except Exception:
            self.query_one("#login-status-authorize", Static).update("[yellow]Note: Port in use. Please paste the redirect URL manually below.[/]")

    def stop_callback_server(self) -> None:
        if self.http_server:
            try:
                self.http_server.server_close()
            except Exception:
                pass
            self.http_server = None

    def handle_auto_login(self, full_url: str) -> None:
        try:
            input_field = self.query_one("#input-redirected-url", Input)
            input_field.value = full_url
            self.notify("Login redirect captured automatically!")
            self.action_connect()
        except Exception:
            pass

    def action_connect(self) -> None:
        redirected_url = self.query_one("#input-redirected-url", Input).value.strip()
        if not redirected_url:
            self.query_one("#login-status-authorize", Static).update("[red]Error: Redirect URL is required[/]")
            return
            
        self.query_one("#login-status-authorize", Static).update("[yellow]Exchanging code for token...[/]")
        self.stop_callback_server()
        
        async def exchange_token():
            try:
                def do_exchange():
                    code = self.auth_manager.parse_response_code(redirected_url)
                    if isinstance(self.auth_manager, SpotifyPKCE):
                        return self.auth_manager.get_access_token(code)
                    else:
                        return self.auth_manager.get_access_token(code, as_dict=False)
                    
                token = await asyncio.to_thread(do_exchange)
                if token:
                    await self.app.initialize_spotify(self.auth_manager)
                else:
                    self.query_one("#login-status-authorize", Static).update("[red]Error: Could not retrieve access token.[/]")
            except Exception as e:
                self.query_one("#login-status-authorize", Static).update(f"[red]Error exchanging code: {e}[/]")
                
        asyncio.create_task(exchange_token())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-credentials":
            self.stop_callback_server()
            self.app.pop_screen()
            
        elif event.button.id == "btn-next":
            username = self.query_one("#input-username", Input).value.strip()
            
            self.query_one("#login-status-credentials", Static).update("[yellow]Generating authorization link...[/]")
            
            # Save environment variables and config files (only when not in mock/test mode)
            if not self.app.force_mock:
                if username:
                    os.environ["SPOTIPY_USERNAME"] = username
                    update_env_var("SPOTIPY_USERNAME", username)
                else:
                    os.environ.pop("SPOTIPY_USERNAME", None)
                    if os.path.exists(".env"):
                        try:
                            with open(".env", "r") as f:
                                lines = f.readlines()
                            new_lines = [line for line in lines if not line.strip().startswith("SPOTIPY_USERNAME=")]
                            with open(".env", "w") as f:
                                f.writelines(new_lines)
                        except Exception:
                            pass
                            
            # Delete stale cache to prevent "invalid_grant: Refresh token revoked"
            cache_path = get_spotify_cache_path()
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            
            client_id = os.getenv("SPOTIPY_CLIENT_ID") or "906b96c8bfe0473792881c6b128c560b"
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")
            redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI") or "http://127.0.0.1:8888/callback"
            
            scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-library-read user-read-private user-read-email"
            try:
                if client_secret:
                    self.auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, cache_path=get_spotify_cache_path(), username=username)
                else:
                    self.auth_manager = SpotifyPKCE(client_id=client_id, redirect_uri=redirect_uri, scope=scope, cache_path=get_spotify_cache_path(), username=username)
                
                self.auth_url = self.auth_manager.get_authorize_url()
                
                # Switch to authorize step
                self.query_one("#auth-url-display", Input).value = self.auth_url
                self.query_one("#step-credentials").add_class("hidden")
                self.query_one("#step-authorize").remove_class("hidden")
                
                # Start callback listener server
                self.start_callback_server(redirect_uri)
                
                # Try opening the browser in background without blocking
                open_browser_silently(self.auth_url)
            except Exception as e:
                self.query_one("#login-status-credentials", Static).update(f"[red]Error: {e}[/]")
                
        elif event.button.id == "btn-copy-link":
            if self.auth_url:
                self.app.clipboard = self.auth_url
                self.notify("Link copied to clipboard!")
                
        elif event.button.id == "btn-back":
            # Switch back to credentials step
            self.stop_callback_server()
            self.query_one("#step-authorize").add_class("hidden")
            self.query_one("#step-credentials").remove_class("hidden")
            self.query_one("#login-status-credentials", Static).update("")
            
        elif event.button.id == "btn-connect":
            self.action_connect()


# Main Player Dashboard Screen
class MainPlayerScreen(Screen):
    def __init__(self, *args, **kwargs):
        kwargs["id"] = "player"
        super().__init__(*args, **kwargs)

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
                    yield Input(placeholder="🔍 Global Spotify Search (Enter to search, Esc to close)...", id="search_input", classes="hidden")
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
            yield Static("🔊 Mock Device", id="device_indicator")
            yield Static("", id="connection_status")

    async def on_mount(self) -> None:
        self.app.sidebar = self.query_one("#sidebar", PlaylistSidebar)
        self.app.track_list = self.query_one("#track_list", TrackList)
        self.app.album_art = self.query_one("#album_art", AlbumArt)
        self.app.now_playing_info = self.query_one("#now_playing_info", NowPlaying)
        self.app.music_progress = self.query_one("#music_progress", MusicProgressBar)
        self.app.status_message = self.query_one("#status_message", Static)
        self.app.device_indicator = self.query_one("#device_indicator", Static)
        self.app.connection_status = self.query_one("#connection_status", Static)
        self.app.search_input = self.query_one("#search_input", Input)
        self.app.volume_widget = self.query_one("#volume_widget", VolumeWidget)
        
        # Check initial size
        if self.app.size and self.app.size.width < 100:
            main_layout = self.query_one("#main-layout")
            main_layout.add_class("compact")
            self.app.compact_mode = True
            
        # Init values
        self.app.sidebar.set_playlists(self.app.playlists)
        if len(self.app.playlists) > 1:
            self.app.sidebar.selected_index = 1
        self.app._update_track_list()
        
        self.app.volume_widget.volume = self.app.music_player.volume
        self.app.volume_widget.shuffle = self.app.shuffle_state
        self.app.volume_widget.repeat = self.app.repeat_state
        self.app.album_art.set_fallback_art()
        
        if self.app.sp:
            current_user = self.app.sp.current_user()
            if current_user:
                self.app.connection_status.update(f"🔗 {current_user['display_name']}")
                await self.app._load_spotify_playlists()
        else:
            self.app.connection_status.update("🎵 Mock Mode")
            self.app.status_message.update("RetroSpotify (Mock Mode) • Press 'a' to set up Spotify login")

    def on_music_progress_bar_track_ended(self, message: MusicProgressBar.TrackEnded) -> None:
        self.app.handle_track_ended()


# Main App Container
class RetroSpotifyApp(App):
    TITLE = "RetroSpotify - Terminal Music Player"
    
    SCREENS = {
        "welcome": WelcomeScreen,
        "player": MainPlayerScreen,
        "settings": SettingsScreen,
        "about": AboutScreen,
    }
    
    CSS = """
    Screen {
        background: #121212;
        color: #b3b3b3;
    }
    
    WelcomeScreen, LoginScreen, SpotifydAuthScreen {
        align: center middle;
    }
    
    #welcome-container {
        align: center middle;
        text-align: center;
        background: #121212;
        padding: 4;
        border: round #282828;
        width: 100%;
        max-width: 70;
        height: auto;
    }
    
    #welcome-logo {
        color: #1db954;
        margin: 0 0 2 0;
        text-align: center;
    }
    
    #welcome-title {
        text-style: bold;
        color: #ffffff;
        margin: 0 0 1 0;
        text-align: center;
    }
    
    #welcome-subtitle {
        color: #b3b3b3;
        margin: 0 0 2 0;
        text-align: center;
    }
    
    #options-list {
        width: 100%;
        align: center middle;
    }
    
    #options-list Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    
    #login-container {
        align: center middle;
        background: #121212;
        padding: 3;
        border: round #282828;
        width: 100%;
        max-width: 60;
        height: auto;
    }
    
    #login-title {
        text-style: bold;
        color: #1db954;
        margin: 0 0 2 0;
        text-align: center;
    }
    
    #login-container Label {
        color: #ffffff;
        text-style: bold;
        margin: 1 0 0 0;
    }
    
    #login-container Input {
        margin: 0 0 1 0;
        border: solid #282828;
        background: #181818;
        color: #ffffff;
    }
    #login-container Input:focus {
        border: solid #1db954;
    }
    
    #login-status, #login-status-credentials, #login-status-authorize {
        margin: 1 0;
        text-align: center;
    }
    
    .login-actions-row {
        layout: horizontal;
        align: center middle;
        margin: 1 0 0 0;
    }
    
    .login-actions-row Button {
        margin: 0 1;
    }
    
    #btn-copy-link {
        margin: 0 0 1 0;
        width: 100%;
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
    #top-row.sidebar-hidden #playlist-sidebar {
        display: none;
    }
    #top-row.sidebar-hidden #track-list-container {
        width: 65%;
    }
    #top-row.sidebar-hidden #album-art-container {
        width: 35%;
    }
    
    #bottom-row {
        height: 35%;
        layout: horizontal;
        margin-top: 1;
    }
    
    #playlist-sidebar {
        width: 20%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #playlist-sidebar:focus-within {
        border: round #1db954;
    }
    
    #track-list-container {
        width: 45%;
        border: round #282828;
        background: #181818;
        padding: 1;
    }
    #track-list-container:focus-within {
        border: round #1db954;
    }
    #track_list {
        height: 100%;
        width: 100%;
    }
    #sidebar {
        height: 100%;
        width: 100%;
    }
    #music_progress {
        height: 2;
        width: 100%;
    }
    
    #album-art-container {
        width: 35%;
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
        padding: 0 1;
    }
    #now-playing-container:focus-within {
        border: round #1db954;
    }
    
    #progress-container {
        width: 45%;
        border: round #282828;
        background: #181818;
        padding: 0 1;
    }
    #progress-container:focus-within {
        border: round #1db954;
    }
    
    #volume-container {
        width: 25%;
        border: round #282828;
        background: #181818;
        padding: 0 1;
    }
    #volume-container:focus-within {
        border: round #1db954;
    }
    
    #playlist-sidebar, #track-list-container, #album-art-container, #now-playing-container, #progress-container, #volume-container {
        border-title-color: #888888;
        border-title-align: left;
    }
    #playlist-sidebar:focus-within, #track-list-container:focus-within, #album-art-container:focus-within, #now-playing-container:focus-within, #progress-container:focus-within, #volume-container:focus-within {
        border-title-color: #1ed760;
        border-title-style: bold;
    }
    
    #status-bar {
        height: 3;
        background: #000000;
        border: none;
        margin: 0;
        padding: 0 1;
        color: #b3b3b3;
        layout: horizontal;
    }
    #status_message {
        width: 1fr;
    }
    #device_indicator {
        width: auto;
        color: #1db954;
        margin-right: 2;
        text-style: bold;
    }
    #connection_status {
        width: auto;
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
    
    /* Responsiveness overrides on active Screen classes */
    
    /* Narrow Tablet: width < 115 */
    .narrow-tablet #playlist-sidebar {
        display: none;
    }
    .narrow-tablet #track-list-container {
        width: 60%;
    }
    .narrow-tablet #album-art-container {
        width: 40%;
    }
    
    /* Narrow Mobile: width < 75 */
    .narrow-mobile #playlist-sidebar {
        display: none;
    }
    .narrow-mobile #album-art-container {
        display: none;
    }
    .narrow-mobile #track-list-container {
        width: 100%;
    }
    .narrow-mobile #volume-container {
        display: none;
    }
    .narrow-mobile #now-playing-container {
        width: 40%;
    }
    .narrow-mobile #progress-container {
        width: 60%;
    }
    .narrow-mobile #welcome-logo {
        display: none;
    }
    .narrow-mobile #welcome-container {
        padding: 1 2;
        border: solid #282828;
    }
    .narrow-mobile #login-container {
        padding: 1 2;
        border: solid #282828;
    }
    
    /* Short Height: height < 30 */
    .short-height #album-art-container {
        display: none;
    }
    .short-height #top-row {
        height: 75%;
    }
    .short-height #bottom-row {
        height: 25%;
        margin-top: 0;
    }
    .short-height #playlist-sidebar {
        width: 30%;
    }
    .short-height #track-list-container {
        width: 70%;
    }
    .short-height.narrow-tablet #track-list-container {
        width: 100%;
    }
    .short-height #welcome-logo {
        display: none;
    }
    .short-height #welcome-container {
        padding: 1 2;
    }
    .short-height #login-container {
        padding: 1 2;
    }
    
    /* Modal Screen Styles */
    HelpScreen, DevicesScreen, AboutScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    
    #help-modal-container {
        background: #181818;
        border: round #282828;
        padding: 1 2;
        width: 65;
        height: auto;
        max-height: 95%;
        overflow-y: auto;
    }
    
    #devices-modal-container, #about-modal-container {
        background: #181818;
        border: round #282828;
        padding: 1 2;
        width: 65;
        height: auto;
        max-height: 38;
        align: center middle;
    }
    
    #help-modal-container:focus-within, #devices-modal-container:focus-within, #about-modal-container:focus-within {
        border: round #1db954;
    }
    
    #help-modal-title, #devices-modal-title, #about-modal-title {
        text-style: bold;
        color: #1db954;
        margin: 0 0 1 0;
        text-align: center;
        width: 100%;
    }
    
    #help-modal-content, #devices-list-content, #about-modal-content {
        margin: 1 0;
        color: #ffffff;
        width: 100%;
    }
    
    #devices-modal-footer {
        text-align: center;
        color: #b3b3b3;
        width: 100%;
    }
    
    #btn-close-help, #btn-about-close {
        width: 100%;
        margin-top: 1;
        background: #1db954;
        color: #ffffff;
    }
    
    /* Settings Screen Styles */
    #settings-scroll-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #settings-container {
        background: #181818;
        border: round #282828;
        padding: 2 4;
        width: 100%;
        max-width: 80;
        height: auto;
    }
    #settings-title {
        text-style: bold;
        color: #1db954;
        margin: 0 0 1 0;
        text-align: center;
        width: 100%;
    }
    #settings-profile-header {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        color: #b3b3b3;
    }
    #settings-form {
        height: auto;
        width: 100%;
    }
    .settings-col {
        width: 1fr;
        padding: 0 2;
        height: auto;
    }
    
    .narrow-tablet #settings-form, .narrow-mobile #settings-form {
        layout: vertical;
    }
    .narrow-tablet .settings-col, .narrow-mobile .settings-col {
        width: 100%;
        padding: 0;
    }
    
    #settings-username-label, #settings-username, #settings-password-label, #settings-password {
        display: none;
    }
    
    .settings-section-title {
        text-style: bold;
        color: #1db954;
        margin-bottom: 1;
    }
    #settings-container Label {
        color: #b3b3b3;
        margin-top: 1;
        text-style: bold;
    }
    #settings-container Input {
        background: #121212;
        border: solid #282828;
        color: #ffffff;
        margin-bottom: 1;
    }
    #settings-container Input:focus {
        border: solid #1db954;
    }
    #settings-cache-info {
        color: #b3b3b3;
        margin: 1 0;
    }
    #settings-status-message {
        text-align: center;
        width: 100%;
        margin-top: 1;
    }
    .settings-actions-row {
        align: center middle;
        margin-top: 2;
        height: auto;
        width: 100%;
    }
    .settings-actions-row Button {
        margin: 0 1;
    }
    #btn-close-help:focus, #btn-close-settings:focus {
        background: #1ed760;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_play", "Play/Pause"),
        ("n", "next_track", "Next Track"),
        ("p", "previous_track", "Previous Track"),
        ("l", "next_playlist"),
        ("h", "previous_playlist"),
        ("r", "refresh"),
        ("/", "search", "Search"),
        ("+", "volume_up"),
        ("-", "volume_down"),
        ("S", "toggle_shuffle"),
        ("R", "toggle_repeat"),
        ("f", "toggle_like"),
        ("e", "enqueue_selected"),
        ("d", "switch_device", "Devices"),
        ("a", "authenticate"),
        ("T", "open_settings", "Settings"),
        ("space", "toggle_play"),
        ("left", "seek_backward"),
        ("right", "seek_forward"),
        ("b", "toggle_sidebar"),
        ("?", "help", "Help"),
    ]

    def __init__(self, force_mock: bool = False):
        super().__init__()
        self.force_mock = force_mock
        self.play_queue = []
        self.liked_track_ids = set()
        self.playlists = [
            {"name": "Play Queue", "id": "play_queue", "items": []}
        ] + MOCK_PLAYLISTS.copy() + MOCK_FEATURED_PLAYLISTS.copy() + MOCK_PODCASTS.copy()
        
        # Populate initial likes from MOCK Liked Songs
        for playlist in self.playlists:
            if playlist['id'] == 'liked_songs':
                for track in playlist.get('items', []):
                    tid = track.id or track.preview_url or track.name
                    if tid:
                        self.liked_track_ids.add(tid)
                        
        self.is_playing = False
        self.sp = None
        self.current_track = None
        self.compact_mode = False
        self.music_player = MusicPlayer()
        self.shuffle_state = False
        self.repeat_state = "off"
        self.current_device_name = "RetroSpotify"
        self.current_device_id = None
        self.audio_source = "none"
        self.use_spotifyd = True
        self.spotifyd_process = None
        self.playing_playlist = None
        self.playing_track_index = 0

    def check_spotifyd_authenticated(self) -> bool:
        """Check if spotifyd has been authenticated."""
        if not self.use_spotifyd:
            return True
        if os.getenv("SPOTIPY_USERNAME") and os.getenv("SPOTIPY_PASSWORD"):
            return True
        return os.path.exists("./spotifyd_cache/oauth/credentials.json")

    def generate_spotifyd_config(self) -> str:
        """Generate spotifyd.conf based on settings."""
        username = os.getenv("SPOTIPY_USERNAME", "")
        password = os.getenv("SPOTIPY_PASSWORD", "")
        device_name = os.getenv("SPOTIPY_DEVICE_NAME", "RetroSpotify")
        backend = os.getenv("SPOTIPY_AUDIO_BACKEND", "pulseaudio")
        bitrate = os.getenv("SPOTIPY_BITRATE", "320")
        
        config = ["[global]"]
        if username:
            config.append(f'username = "{username}"')
        if password:
            config.append(f'password = "{password}"')
        
        config.append(f'device_name = "{device_name}"')
        config.append('cache_path = "./spotifyd_cache"')
        config.append(f'bitrate = {bitrate}')
        config.append(f'backend = "{backend}"')
        
        with open("spotifyd.conf", "w") as f:
            f.write("\n".join(config) + "\n")
            
        return "spotifyd.conf"

    def start_spotifyd(self) -> None:
        """Start the spotifyd daemon process in the background."""
        if not self.use_spotifyd or self.force_mock:
            return
            
        self.stop_spotifyd()
        
        # Ensure cache directory exists
        os.makedirs("./spotifyd_cache", exist_ok=True)
        
        # Generate config file
        config_path = self.generate_spotifyd_config()
        
        # Build command: run spotifyd with configured config path
        cmd = [
            "./spotifyd",
            "--no-daemon",
            "--config-path", config_path
        ]
        try:
            self.spotifyd_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            self.notify(f"Could not start local Spotify player: {e}", severity="warning")

    def stop_spotifyd(self) -> None:
        """Terminate the spotifyd process cleanly."""
        if self.spotifyd_process:
            try:
                self.spotifyd_process.terminate()
                self.spotifyd_process.wait(timeout=1)
            except Exception:
                try:
                    self.spotifyd_process.kill()
                except Exception:
                    pass
            self.spotifyd_process = None

    def get_spotifyd_device_id(self) -> Optional[str]:
        """Look up the Spotify Connect device ID for RetroSpotify."""
        if not self.sp:
            return None
        try:
            devices_info = self.sp.devices()
            for device in devices_info.get("devices", []):
                if device.get("name") == "RetroSpotify":
                    return device.get("id")
        except Exception:
            pass
        return None

    def update_responsive_classes(self) -> None:
        """Apply responsiveness classes to the current active screen based on its size."""
        screen = self.screen
        if not screen or not self.size:
            return
            
        width = self.size.width
        height = self.size.height
        
        # Width responsiveness
        if width < 75:
            screen.add_class("narrow-mobile")
            screen.remove_class("narrow-tablet")
        elif width < 115:
            screen.add_class("narrow-tablet")
            screen.remove_class("narrow-mobile")
        else:
            screen.remove_class("narrow-mobile")
            screen.remove_class("narrow-tablet")
            
        # Height responsiveness
        if height < 30:
            screen.add_class("short-height")
        else:
            screen.remove_class("short-height")
            
        # Maintain legacy compact_mode flag and class on main-layout
        self.compact_mode = (width < 100)
        layouts = self.query("#main-layout")
        if layouts:
            main_layout = layouts.first()
            if self.compact_mode:
                main_layout.add_class("compact")
            else:
                main_layout.remove_class("compact")

    def push_screen(self, screen, callback=None):
        res = super().push_screen(screen, callback)
        self.call_later(self.update_responsive_classes)
        return res

    def switch_screen(self, screen):
        super().switch_screen(screen)
        self.call_later(self.update_responsive_classes)

    def on_resize(self, event: events.Resize) -> None:
        self.update_responsive_classes()

    async def on_mount(self) -> None:
        if not self.force_mock:
            async def download_and_start_spotifyd():
                success = await asyncio.to_thread(ensure_spotifyd_binary)
                if success:
                    if self.sp and self.check_spotifyd_authenticated():
                        if not self.spotifyd_process or self.spotifyd_process.poll() is not None:
                            self.start_spotifyd()
            asyncio.create_task(download_and_start_spotifyd())

        initialized = False
        if not self.force_mock and check_cached_token() and SPOTIPY_AVAILABLE:
            client_id = os.getenv("SPOTIPY_CLIENT_ID") or "906b96c8bfe0473792881c6b128c560b"
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
            redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
            scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-library-read user-read-private user-read-email"
            
            if client_id:
                try:
                    username = os.getenv("SPOTIPY_USERNAME")
                    if client_secret:
                        auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, cache_path=get_spotify_cache_path(), username=username)
                    else:
                        auth_manager = SpotifyPKCE(client_id=client_id, redirect_uri=redirect_uri, scope=scope, cache_path=get_spotify_cache_path(), username=username)
                        
                    self.sp = spotipy.Spotify(auth_manager=auth_manager)
                    current_user = self.sp.current_user()
                    if current_user:
                        if self.check_spotifyd_authenticated():
                            self.start_spotifyd()
                            self.push_screen("player")
                        else:
                            self.push_screen(SpotifydAuthScreen())
                        initialized = True
                except Exception:
                    # Stale or revoked token in cache, clear it
                    cache_path = get_spotify_cache_path()
                    if os.path.exists(cache_path):
                        try:
                            os.remove(cache_path)
                        except Exception:
                            pass
        
        if not initialized:
            self.push_screen("welcome")

    async def initialize_spotify(self, auth_manager):
        try:
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            current_user = self.sp.current_user()
            if current_user:
                if self.screen.id != "player":
                    if self.check_spotifyd_authenticated():
                        self.start_spotifyd()
                        self.switch_screen("player")
                    else:
                        self.switch_screen(SpotifydAuthScreen())
        except Exception as e:
            self.notify(f"Spotify Connection Error: {e}")
            if self.screen.id != "welcome":
                self.switch_screen("welcome")

    def start_mock_mode(self):
        self.sp = None
        if self.screen.id != "player":
            self.switch_screen("player")

    async def _load_spotify_playlists(self):
        try:
            if not self.sp:
                return
                
            playlists = []
            
            # Liked Songs
            try:
                saved_tracks_results = await asyncio.to_thread(self.sp.current_user_saved_tracks, limit=50)
                liked_tracks = []
                pages = 0
                while saved_tracks_results and pages < 3:
                    for item in saved_tracks_results['items']:
                        track_data = item['track']
                        if track_data:
                            album_images = track_data['album']['images']
                            album_art_url = album_images[0]['url'] if album_images else None
                            
                            track_obj = Track(
                                name=track_data['name'],
                                artists=[artist['name'] for artist in track_data['artists']],
                                duration=track_data['duration_ms'] // 1000,
                                id=track_data['id'],
                                album_art_url=album_art_url,
                                preview_url=track_data.get('preview_url')
                            )
                            liked_tracks.append(track_obj)
                            if track_obj.id:
                                self.liked_track_ids.add(track_obj.id)
                    if saved_tracks_results.get('next') and pages < 2:
                        saved_tracks_results = await asyncio.to_thread(self.sp.next, saved_tracks_results)
                        pages += 1
                    else:
                        break
                
                # Append Liked Songs even if it has 0 items so it is always visible
                playlists.append({
                    'name': 'Liked Songs',
                    'id': 'liked_songs',
                    'items': liked_tracks
                })
            except Exception as e:
                self.notify(f"Failed to load Liked Songs: {e}")

            # User Playlists
            results = await asyncio.to_thread(self.sp.current_user_playlists, limit=50)
            for item in results['items']:
                tracks = []
                track_results = await asyncio.to_thread(self.sp.playlist_tracks, item['id'], limit=50)
                pages = 0
                while track_results and pages < 3:
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
                    if track_results.get('next') and pages < 2:
                        track_results = await asyncio.to_thread(self.sp.next, track_results)
                        pages += 1
                    else:
                        break
                
                playlists.append({
                    'name': item['name'],
                    'id': item['id'],
                    'items': tracks
                })
            
            # Featured Playlists from Spotify
            try:
                featured_res = await asyncio.to_thread(self.sp.featured_playlists, limit=4)
                for item in featured_res.get('playlists', {}).get('items', []):
                    tracks = []
                    track_results = await asyncio.to_thread(self.sp.playlist_tracks, item['id'], limit=20)
                    for track_item in track_results.get('items', []):
                        track_data = track_item.get('track')
                        if track_data:
                            album_images = track_data.get('album', {}).get('images', [])
                            album_art_url = album_images[0]['url'] if album_images else None
                            tracks.append(Track(
                                name=track_data['name'],
                                artists=[artist['name'] for artist in track_data['artists']],
                                duration=track_data['duration_ms'] // 1000,
                                id=track_data['id'],
                                album_art_url=album_art_url,
                                preview_url=track_data.get('preview_url')
                            ))
                    playlists.append({
                        'name': f"✨ {item['name']}",
                        'id': item['id'],
                        'items': tracks
                    })
            except Exception as e:
                self.log(f"Failed to load featured playlists: {e}")

            # Top Charts from Spotify
            try:
                topcharts_res = await asyncio.to_thread(self.sp.category_playlists, category_id="toplists", limit=2)
                for item in topcharts_res.get('playlists', {}).get('items', []):
                    tracks = []
                    track_results = await asyncio.to_thread(self.sp.playlist_tracks, item['id'], limit=20)
                    for track_item in track_results.get('items', []):
                        track_data = track_item.get('track')
                        if track_data:
                            album_images = track_data.get('album', {}).get('images', [])
                            album_art_url = album_images[0]['url'] if album_images else None
                            tracks.append(Track(
                                name=track_data['name'],
                                artists=[artist['name'] for artist in track_data['artists']],
                                duration=track_data['duration_ms'] // 1000,
                                id=track_data['id'],
                                album_art_url=album_art_url,
                                preview_url=track_data.get('preview_url')
                            ))
                    playlists.append({
                        'name': f"🔥 {item['name']}",
                        'id': item['id'],
                        'items': tracks
                    })
            except Exception as e:
                self.log(f"Failed to load toplists: {e}")

            # New Releases from Spotify
            try:
                new_releases_res = await asyncio.to_thread(self.sp.new_releases, limit=2)
                for album in new_releases_res.get('albums', {}).get('items', []):
                    tracks = []
                    album_tracks = await asyncio.to_thread(self.sp.album_tracks, album['id'], limit=10)
                    for track_data in album_tracks.get('items', []):
                        tracks.append(Track(
                            name=track_data['name'],
                            artists=[artist['name'] for artist in track_data['artists']],
                            duration=track_data['duration_ms'] // 1000,
                            id=track_data['id'],
                            album_art_url=album.get('images', [{}])[0].get('url'),
                            preview_url=track_data.get('preview_url')
                        ))
                    playlists.append({
                        'name': f"🆕 {album['name']}",
                        'id': f"album_{album['id']}",
                        'items': tracks
                    })
            except Exception as e:
                self.log(f"Failed to load new releases: {e}")

            # Recommendations from Spotify
            try:
                recs_res = await asyncio.to_thread(self.sp.recommendations, seed_genres=['pop', 'rock', 'hip-hop'], limit=20)
                tracks = []
                for track_data in recs_res.get('tracks', []):
                    album_images = track_data.get('album', {}).get('images', [])
                    album_art_url = album_images[0]['url'] if album_images else None
                    tracks.append(Track(
                        name=track_data['name'],
                        artists=[artist['name'] for artist in track_data['artists']],
                        duration=track_data['duration_ms'] // 1000,
                        id=track_data['id'],
                        album_art_url=album_art_url,
                        preview_url=track_data.get('preview_url')
                    ))
                if tracks:
                    playlists.append({
                        'name': "💡 Recommended For You",
                        'id': "recommendations",
                        'items': tracks
                    })
            except Exception as e:
                self.log(f"Failed to load recommendations: {e}")

            # User followed podcasts (saved shows)
            try:
                shows_res = await asyncio.to_thread(self.sp.current_user_saved_shows, limit=4)
                for show_item in shows_res.get('items', []):
                    show = show_item.get('show')
                    if not show:
                        continue
                    episodes = []
                    ep_res = await asyncio.to_thread(self.sp.show_episodes, show['id'], limit=10)
                    for ep in ep_res.get('items', []):
                        album_images = ep.get('images', [])
                        album_art_url = album_images[0]['url'] if album_images else None
                        episodes.append(Track(
                            name=ep['name'],
                            artists=[show['name']],
                            duration=ep['duration_ms'] // 1000,
                            id=ep['id'],
                            album_art_url=album_art_url,
                            preview_url=ep.get('preview_url')
                        ))
                    playlists.append({
                        'name': f"🎙️ {show['name']}",
                        'id': f"show_{show['id']}",
                        'is_podcast': True,
                        'items': episodes
                    })
            except Exception as e:
                self.log(f"Failed to load podcasts: {e}")
            
            # Insert Play Queue and Liked Songs at the top of playlists
            playlists.insert(0, {
                'name': 'Play Queue',
                'id': 'play_queue',
                'items': self.play_queue
            })
            
            # Ensure Liked Songs is at index 1
            has_liked = any(p['id'] == 'liked_songs' for p in playlists)
            if not has_liked:
                playlists.insert(1, {
                    'name': 'Liked Songs',
                    'id': 'liked_songs',
                    'items': []
                })
            else:
                # Move Liked Songs to index 1 if it is elsewhere
                liked_pl = None
                for p in playlists:
                    if p['id'] == 'liked_songs':
                        liked_pl = p
                        break
                if liked_pl:
                    playlists.remove(liked_pl)
                    playlists.insert(1, liked_pl)
            
            # Query active device name
            try:
                devices_info = await asyncio.to_thread(self.sp.devices)
                devices = devices_info.get("devices", [])
                active_device = next((d for d in devices if d.get("is_active")), None)
                if active_device:
                    self.current_device_name = active_device["name"]
                    if hasattr(self, "device_indicator") and self.device_indicator:
                        self.device_indicator.update(f"🔊 {self.current_device_name}")
            except Exception:
                pass

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
        if self.current_track == track and not self.is_playing:
            self._resume_track()
            return
            
        # Update playing playlist context if track is in the viewed playlist
        viewed_pl = self.sidebar.get_selected_playlist()
        if viewed_pl and track in viewed_pl.get('items', []):
            self.playing_playlist = viewed_pl
            try:
                self.playing_track_index = viewed_pl['items'].index(track)
            except ValueError:
                self.playing_track_index = 0

        self.current_track = track
        self.now_playing_info.set_track(track)
        
        if track.album_art_url:
            self.album_art.set_art_from_url(track.album_art_url)
        else:
            self.album_art.set_fallback_art()
        
        self.music_progress.stop()
        self.music_progress.play(track.duration)
        self.is_playing = True
        self.audio_source = "none"
        
        async def handle_playback():
            success = False
            if self.sp and track.id:
                self.status_message.update(f"⏳ Spotify Connect: Trying to play {track.name}...")
                
                def start_spotify_playback():
                    try:
                        # 1. Use the selected device if set, otherwise fallback to local RetroSpotify daemon
                        device_id = getattr(self, "current_device_id", None) or self.get_spotifyd_device_id()
                        if device_id:
                            self.sp.start_playback(device_id=device_id, uris=[f"spotify:track:{track.id}"])
                            return True
                        else:
                            self.sp.start_playback(uris=[f"spotify:track:{track.id}"])
                            return True
                    except Exception:
                        # 2. Try transferring playback first, then retry
                        device_id = getattr(self, "current_device_id", None) or self.get_spotifyd_device_id()
                        if device_id:
                            try:
                                self.sp.transfer_playback(device_id=device_id, force_play=True)
                                import time
                                time.sleep(0.5)
                                self.sp.start_playback(device_id=device_id, uris=[f"spotify:track:{track.id}"])
                                return True
                            except Exception:
                                pass
                        return False
                        
                success = await asyncio.to_thread(start_spotify_playback)
                if success:
                    self.audio_source = "connect"
                    self.now_playing_info.refresh()
                    self.status_message.update(f"▶️ Spotify Connect: {track.name}")
                    return
            
            # Local fallback (Spotify Preview URL -> Synth Fallback)
            self.status_message.update(f"⏳ Loading local audio...")
            play_url = track.preview_url
            
            if not play_url:
                # Play synthetic retro chiptune as fallback audio
                try:
                    play_url = generate_retro_synth_wav(min(30.0, float(track.duration)))
                except Exception:
                    play_url = f"sine=f=440:d={track.duration}"
                
            def play_local():
                return self.music_player.play(play_url)
                
            local_success = await asyncio.to_thread(play_local)
            if local_success:
                if track.preview_url and play_url == track.preview_url:
                    self.audio_source = "preview"
                else:
                    self.audio_source = "synth"
                self.now_playing_info.refresh()
                if track.preview_url and play_url == track.preview_url:
                    self.status_message.update(f"▶️ Local Player (Preview): {track.name}")
                else:
                    self.status_message.update(f"▶️ Local Player (Synth Fallback): {track.name}")
            else:
                self.audio_source = "none"
                self.now_playing_info.refresh()
                self.status_message.update(f"⏸️ Simulating: {track.name} (no local audio player)")
                
        asyncio.create_task(handle_playback())

    def _resume_track(self):
        if not self.current_track:
            return
            
        async def handle_resume():
            success = False
            if self.sp and self.current_track.id:
                self.status_message.update(f"⏳ Spotify Connect: Resuming...")
                
                def resume_spotify_playback():
                    try:
                        device_id = getattr(self, "current_device_id", None) or self.get_spotifyd_device_id()
                        if device_id:
                            self.sp.start_playback(device_id=device_id)
                        else:
                            self.sp.start_playback()
                        return True
                    except Exception:
                        return False
                        
                success = await asyncio.to_thread(resume_spotify_playback)
                if success:
                    self.audio_source = "connect"
                    self.now_playing_info.refresh()
                    self.status_message.update(f"▶️ Spotify Connect: {self.current_track.name}")
                    self.music_progress.play(self.current_track.duration)
                    self.is_playing = True
                    return
            
            # Local fallback resume
            self.status_message.update(f"⏳ Local Player: Resuming...")
            def resume_local():
                return self.music_player.resume()
            local_success = await asyncio.to_thread(resume_local)
            if local_success:
                if self.current_track.preview_url:
                    self.audio_source = "preview"
                else:
                    self.audio_source = "synth"
                self.now_playing_info.refresh()
                self.status_message.update(f"▶️ Playing: {self.current_track.name}")
                self.music_progress.play(self.current_track.duration)
                self.is_playing = True
            else:
                # If resume fails, start a new playback
                self._play_track(self.current_track)
                
        asyncio.create_task(handle_resume())

    def _pause_track(self):
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
        self.music_progress.stop()
        self.music_player.stop()
        self.is_playing = False
        self.current_track = None
        self.audio_source = "none"
        if hasattr(self, "now_playing_info"):
            self.now_playing_info.set_track(None)
        self.status_message.update("⏹️ Stopped")

    def seek_to_position(self, position_seconds: float):
        if not self.current_track:
            return
            
        position_seconds = max(0.0, min(float(self.current_track.duration), float(position_seconds)))
        
        # Update progress bar state immediately
        self.music_progress.current_position = position_seconds
        self.music_progress.start_time = time.time() - position_seconds
        self.music_progress.progress = position_seconds / self.current_track.duration
        self.music_progress.refresh(layout=True)
        
        # 1. Spotify Connect Seek
        if self.sp and self.audio_source == "connect":
            def spotify_seek():
                try:
                    self.sp.seek_track(position_ms=int(position_seconds * 1000))
                except Exception as e:
                    self.log(f"Failed to seek on Spotify Connect: {e}")
            import threading
            threading.Thread(target=spotify_seek).start()
            self.status_message.update(f"⏳ Seeking Spotify Connect to {format_duration(int(position_seconds))}...")
            
        # 2. Local player seek
        elif self.audio_source in ("preview", "synth") and self.music_player:
            play_url = self.current_track.preview_url
            if self.audio_source == "synth" or not play_url:
                try:
                    play_url = generate_retro_synth_wav(min(30.0, float(self.current_track.duration)))
                except Exception:
                    play_url = f"sine=f=440:d={self.current_track.duration}"
            
            async def restart_local_with_offset():
                def play_local():
                    return self.music_player.play(play_url, start_offset=position_seconds)
                await asyncio.to_thread(play_local)
                # Keep playing status intact
                self.music_progress.play(self.current_track.duration)
                self.music_progress.start_time = time.time() - position_seconds
                self.is_playing = True
                self.status_message.update(f"▶️ Seeked: {self.current_track.name} to {format_duration(int(position_seconds))}")
            
            asyncio.create_task(restart_local_with_offset())
        else:
            self.status_message.update(f"▶️ Seeked (Simulated) to {format_duration(int(position_seconds))}")

    def handle_track_ended(self) -> None:
        if self.repeat_state == 'track':
            if self.current_track:
                self._play_track(self.current_track)
        else:
            self.action_next_track()

    # Actions
    def action_toggle_play(self):
        if self.screen.id != "player":
            return
        if self.current_track:
            if self.is_playing:
                self._pause_track()
            else:
                self._resume_track()
        else:
            current_track = self.track_list.get_selected_track()
            if current_track:
                self.playing_playlist = self.sidebar.get_selected_playlist()
                self.playing_track_index = self.track_list.selected_index
                self._play_track(current_track)

    def action_next_track(self):
        if self.screen.id != "player":
            return
            
        # 1. Play from queue first if there are items enqueued
        if self.play_queue:
            next_track = self.play_queue.pop(0)
            
            # Update the Queue playlist representation
            for playlist in self.playlists:
                if playlist['id'] == 'play_queue':
                    playlist['items'] = self.play_queue
                    break
                    
            # Refresh if currently viewing Play Queue
            selected_pl = self.sidebar.get_selected_playlist()
            if selected_pl and selected_pl['id'] == 'play_queue':
                self._update_track_list()
                
            self._play_track(next_track)
            return

        # Initialize playing_playlist if not already set
        if not getattr(self, "playing_playlist", None):
            self.playing_playlist = self.sidebar.get_selected_playlist()
            self.playing_track_index = self.track_list.selected_index

        if not self.playing_playlist:
            return

        tracks = self.playing_playlist.get('items', [])
        if not tracks:
            self._stop_track()
            return

        # 2. Otherwise handle Shuffle
        if self.shuffle_state:
            rand_idx = random.randint(0, len(tracks) - 1)
            self.playing_track_index = rand_idx
            
            # Sync TUI cursor if viewing the same playlist
            if self.sidebar.get_selected_playlist() == self.playing_playlist:
                self.track_list.selected_index = rand_idx
                self.track_list.refresh()
                
            if self.is_playing:
                self._play_track(tracks[rand_idx])
            return
        
        # 3. Regular next track in the list
        if self.repeat_state == 'context':
            # Wrap around index
            self.playing_track_index = (self.playing_track_index + 1) % len(tracks)
            
            if self.sidebar.get_selected_playlist() == self.playing_playlist:
                self.track_list.selected_index = self.playing_track_index
                self.track_list.refresh()
                
            if self.is_playing:
                self._play_track(tracks[self.playing_track_index])
        else:
            if self.playing_track_index < len(tracks) - 1:
                self.playing_track_index += 1
                
                if self.sidebar.get_selected_playlist() == self.playing_playlist:
                    self.track_list.selected_index = self.playing_track_index
                    self.track_list.refresh()
                    
                if self.is_playing:
                    self._play_track(tracks[self.playing_track_index])
            else:
                self._stop_track()
                self.status_message.update("⏹️ Playlist ended")

    def action_previous_track(self):
        if self.screen.id != "player":
            return
            
        # Initialize playing_playlist if not already set
        if not getattr(self, "playing_playlist", None):
            self.playing_playlist = self.sidebar.get_selected_playlist()
            self.playing_track_index = self.track_list.selected_index

        if not self.playing_playlist:
            return

        tracks = self.playing_playlist.get('items', [])
        if not tracks:
            return

        if self.playing_track_index > 0:
            self.playing_track_index -= 1
            
            if self.sidebar.get_selected_playlist() == self.playing_playlist:
                self.track_list.selected_index = self.playing_track_index
                self.track_list.refresh()
                
            if self.is_playing:
                self._play_track(tracks[self.playing_track_index])

    def action_next_playlist(self):
        if self.screen.id != "player":
            return
        if self.sidebar.select_next():
            self._update_track_list()

    def action_previous_playlist(self):
        if self.screen.id != "player":
            return
        if self.sidebar.select_previous():
            self._update_track_list()

    def action_refresh(self):
        if self.screen.id != "player":
            return
        if self.sp:
            asyncio.create_task(self._load_spotify_playlists())
        else:
            self.notify("Refreshed local data")

    def action_search(self):
        if self.screen.id != "player":
            return
        self.search_input.toggle_class("hidden")
        if not self.search_input.has_class("hidden"):
            self.previous_playlist_index = self.sidebar.selected_index
            self.search_input.focus()

    def on_input_changed(self, event: Input.Changed):
        pass

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            if self.screen.id == "player" and not self.search_input.has_class("hidden"):
                self.playlists = [p for p in self.playlists if p['id'] != 'search_results']
                self.sidebar.set_playlists(self.playlists)
                
                prev_idx = getattr(self, "previous_playlist_index", 0)
                if prev_idx >= len(self.playlists):
                    prev_idx = 0
                self.sidebar.selected_index = prev_idx
                self.sidebar.refresh()
                
                self.search_input.value = ""
                self.search_input.add_class("hidden")
                self._update_track_list()
                self.track_list.focus()
                event.prevent_default()

    def on_input_submitted(self, event: Input.Submitted):
        if self.screen.id != "player":
            return
        query = event.value
        if not query:
            return
            
        if self.sp:
            asyncio.create_task(self._perform_search(query))
        else:
            self.status_message.update(f"🔍 Searching globally (Mock Mode) for '{query}'...")
            query_lower = query.lower()
            found_tracks = []
            
            seen_ids = set()
            for playlist in self.playlists:
                if playlist['id'] in ('search_results', 'play_queue'):
                    continue
                for track in playlist.get('items', []):
                    tid = track.id or track.preview_url or track.name
                    if tid not in seen_ids:
                        if query_lower in track.name.lower() or any(query_lower in a.lower() for a in track.artists):
                            found_tracks.append(track)
                            seen_ids.add(tid)
            
            for track in MOCK_GLOBAL_CATALOG:
                tid = track.id or track.preview_url or track.name
                if tid not in seen_ids:
                    if query_lower in track.name.lower() or any(query_lower in a.lower() for a in track.artists):
                        found_tracks.append(track)
                        seen_ids.add(tid)
            
            self._handle_search_results(found_tracks, query)
            
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
            
            self._handle_search_results(tracks, query)
                
        except Exception as e:
            self.status_message.update("❌ Search failed")
            self.notify(f"Search error: {e}")

    def _handle_search_results(self, tracks: List[Track], query: str):
        search_pl = None
        for playlist in self.playlists:
            if playlist['id'] == 'search_results':
                search_pl = playlist
                break
                
        if not search_pl:
            search_pl = {
                'name': f"🔍 Results: {query[:10]}",
                'id': 'search_results',
                'items': tracks
            }
            self.playlists.append(search_pl)
        else:
            search_pl['name'] = f"🔍 Results: {query[:10]}"
            search_pl['items'] = tracks
            
        self.sidebar.set_playlists(self.playlists)
        self.sidebar.selected_index = len(self.playlists) - 1
        self.sidebar.refresh()
        self._update_track_list()
        
        if tracks:
            self.status_message.update(f"✅ Found {len(tracks)} results for '{query}'")
        else:
            self.status_message.update(f"❌ No results found for '{query}'")

    def action_toggle_like(self):
        if self.screen.id != "player":
            return
        track = self.track_list.get_selected_track()
        if track:
            self.toggle_like_track(track)
            
    def action_enqueue_selected(self):
        if self.screen.id != "player":
            return
        track = self.track_list.get_selected_track()
        if track:
            self.enqueue_track(track)

    def action_switch_device(self):
        if self.screen.id != "player":
            return
            
        async def load_and_show_devices():
            devices = []
            if self.sp:
                try:
                    devices_info = await asyncio.to_thread(self.sp.devices)
                    devices = devices_info.get("devices", [])
                except Exception as e:
                    self.notify(f"Could not load devices: {e}", severity="warning")
            else:
                devices = [
                    {"id": "mock_retro", "name": "RetroSpotify", "type": "Computer", "is_active": True},
                    {"id": "mock_phone", "name": "iPhone 15 Pro", "type": "Smartphone", "is_active": False},
                    {"id": "mock_speaker", "name": "Living Room Echo", "type": "Speaker", "is_active": False},
                    {"id": "mock_web", "name": "Web Player (Chrome)", "type": "Computer", "is_active": False},
                ]
                
            def handle_device_selection(selected_device):
                if not selected_device:
                    return
                
                device_id = selected_device["id"]
                device_name = selected_device["name"]
                
                self.current_device_id = device_id
                self.current_device_name = device_name
                
                if self.sp:
                    def do_transfer():
                        try:
                            self.sp.transfer_playback(device_id=device_id, force_play=True)
                        except Exception as e:
                            self.notify(f"Could not transfer playback: {e}", severity="warning")
                    import threading
                    threading.Thread(target=do_transfer).start()
                else:
                    self.notify(f"Mock Mode: Transferred playback to {device_name}")
                    
                self.notify(f"Switched playback to {device_name}")
                self.status_message.update(f"📱 Active Device: {device_name}")
                if hasattr(self, "device_indicator") and self.device_indicator:
                    self.device_indicator.update(f"🔊 {device_name}")
                
            self.push_screen(DevicesScreen(devices=devices), handle_device_selection)
            
        asyncio.create_task(load_and_show_devices())

    def toggle_like_track(self, track: Track) -> None:
        if not track:
            return
            
        tid = track.id or track.preview_url or track.name
        if not tid:
            return
            
        is_liked = tid in self.liked_track_ids
        if is_liked:
            self.liked_track_ids.remove(tid)
            self.notify(f"Removed '{track.name}' from Liked Songs.")
            
            if self.sp and track.id:
                def delete_track():
                    try:
                        self.sp.current_user_saved_tracks_delete(tracks=[track.id])
                    except Exception as e:
                        self.log(f"Failed to remove from Spotify Liked Songs: {e}")
                import threading
                threading.Thread(target=delete_track).start()
        else:
            self.liked_track_ids.add(tid)
            self.notify(f"Added '{track.name}' to Liked Songs! ♥")
            
            if self.sp and track.id:
                def add_track():
                    try:
                        self.sp.current_user_saved_tracks_add(tracks=[track.id])
                    except Exception as e:
                        self.log(f"Failed to add to Spotify Liked Songs: {e}")
                import threading
                threading.Thread(target=add_track).start()
                
        for playlist in self.playlists:
            if playlist['id'] == 'liked_songs':
                liked_items = playlist.get('items', [])
                exists = any((t.id == track.id if track.id else (t.preview_url == track.preview_url or t.name == track.name)) for t in liked_items)
                if is_liked:
                    playlist['items'] = [t for t in liked_items if (t.id != track.id if track.id else (t.preview_url != track.preview_url and t.name != track.name))]
                else:
                    if not exists:
                        playlist['items'] = [track] + liked_items
                break
                
        self._update_track_list()
        if hasattr(self, "now_playing_info"):
            self.now_playing_info.refresh()

    def enqueue_track(self, track: Track) -> None:
        if not track:
            return
            
        self.play_queue.append(track)
        self.notify(f"Added '{track.name}' to Play Queue. ({len(self.play_queue)} in queue)")
        
        if self.sp and track.id:
            def add_to_spotify_queue():
                try:
                    self.sp.add_to_queue(uri=f"spotify:track:{track.id}")
                except Exception as e:
                    self.log(f"Failed to enqueue to Spotify: {e}")
            import threading
            threading.Thread(target=add_to_spotify_queue).start()
            
        for playlist in self.playlists:
            if playlist['id'] == 'play_queue':
                playlist['items'] = self.play_queue
                break
                
        self._update_track_list()

    def action_volume_up(self):
        if self.screen.id != "player":
            return
        self.music_player.set_volume(self.music_player.volume + 10)
        self.volume_widget.volume = self.music_player.volume
        self.notify(f"Volume: {self.music_player.volume}%")
        if self.sp and self.audio_source == "connect":
            def set_spotify_volume():
                try:
                    self.sp.volume(self.music_player.volume)
                except Exception:
                    pass
            import threading
            threading.Thread(target=set_spotify_volume).start()
        
    def action_volume_down(self):
        if self.screen.id != "player":
            return
        self.music_player.set_volume(self.music_player.volume - 10)
        self.volume_widget.volume = self.music_player.volume
        self.notify(f"Volume: {self.music_player.volume}%")
        if self.sp and self.audio_source == "connect":
            def set_spotify_volume():
                try:
                    self.sp.volume(self.music_player.volume)
                except Exception:
                    pass
            import threading
            threading.Thread(target=set_spotify_volume).start()

    def action_toggle_shuffle(self):
        if self.screen.id != "player":
            return
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
        if self.screen.id != "player":
            return
        if self.repeat_state == "off":
            self.repeat_state = "track"
        elif self.repeat_state == "track":
            self.repeat_state = "context"
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

    def action_authenticate(self):
        self.switch_screen("welcome")

    def action_help(self):
        self.push_screen(HelpScreen())

    def action_open_settings(self):
        self.push_screen(SettingsScreen())

    def action_seek_backward(self):
        if self.screen.id != "player" or not self.current_track:
            return
        new_pos = max(0.0, self.music_progress.current_position - 10.0)
        self.seek_to_position(new_pos)

    def action_seek_forward(self):
        if self.screen.id != "player" or not self.current_track:
            return
        new_pos = min(float(self.current_track.duration), self.music_progress.current_position + 10.0)
        self.seek_to_position(new_pos)

    def action_toggle_sidebar(self):
        if self.screen.id != "player":
            return
        top_row = self.screen.query_one("#top-row")
        if top_row:
            top_row.toggle_class("sidebar-hidden")

    def action_quit(self):
        self.music_player.stop()
        self.stop_spotifyd()
        self.exit()

    def on_unmount(self):
        self.music_player.stop()
        self.stop_spotifyd()

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
        # SPOTIPY_CLIENT_SECRET is optional (not needed for PKCE Quick Login)
        required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_REDIRECT_URI"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars or args.mock:
            if args.mock:
                print("🎵 RetroSpotify - Running in mock mode")
            else:
                print("🎵 RetroSpotify - Ready for connection")
                print("💡 Tip: You can configure your credentials directly in the app's Welcome Screen,")
                print("   or set these optional environment variables:")
                for var in required_vars + ["SPOTIPY_CLIENT_SECRET"]:
                    if not os.getenv(var):
                        print(f"   {var}=your_value_here")
    
    app = RetroSpotifyApp(force_mock=args.mock)
    app.run()