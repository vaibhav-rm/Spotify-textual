import asyncio
import time
import os
from textual.widgets import Input
from main import RetroSpotifyApp

def backup_env():
    env_exists = os.path.exists(".env")
    env_content = ""
    if env_exists:
        with open(".env", "r") as f:
            env_content = f.read()
            
    conf_exists = os.path.exists("spotifyd.conf")
    conf_content = ""
    if conf_exists:
        with open("spotifyd.conf", "r") as f:
            conf_content = f.read()
            
    orig_env = {
        "SPOTIPY_CLIENT_ID": os.environ.get("SPOTIPY_CLIENT_ID"),
        "SPOTIPY_CLIENT_SECRET": os.environ.get("SPOTIPY_CLIENT_SECRET"),
        "SPOTIPY_REDIRECT_URI": os.environ.get("SPOTIPY_REDIRECT_URI"),
        "SPOTIPY_USERNAME": os.environ.get("SPOTIPY_USERNAME"),
        "SPOTIPY_PASSWORD": os.environ.get("SPOTIPY_PASSWORD"),
        "SPOTIPY_DEVICE_NAME": os.environ.get("SPOTIPY_DEVICE_NAME"),
        "SPOTIPY_AUDIO_BACKEND": os.environ.get("SPOTIPY_AUDIO_BACKEND"),
        "SPOTIPY_BITRATE": os.environ.get("SPOTIPY_BITRATE"),
    }
    return env_exists, env_content, conf_exists, conf_content, orig_env

def restore_env(env_exists, env_content, conf_exists, conf_content, orig_env):
    for key, val in orig_env.items():
        if val is not None:
            os.environ[key] = val
        else:
            os.environ.pop(key, None)
            
    if env_exists:
        with open(".env", "w") as f:
            f.write(env_content)
    else:
        if os.path.exists(".env"):
            try:
                os.remove(".env")
            except Exception:
                pass
            
    if conf_exists:
        with open("spotifyd.conf", "w") as f:
            f.write(conf_content)
    else:
        if os.path.exists("spotifyd.conf"):
            try:
                os.remove("spotifyd.conf")
            except Exception:
                pass

async def test_app():
    env_exists, env_content, conf_exists, conf_content, orig_env = backup_env()
    try:
        app = RetroSpotifyApp(force_mock=True)
        await run_test_logic(app)
    finally:
        restore_env(env_exists, env_content, conf_exists, conf_content, orig_env)

async def run_test_logic(app):
    print("Starting headless app test...")
    async with app.run_test(size=(120, 40)) as pilot:
        print("✅ App mounted successfully!")
        
        await pilot.pause()
        print(f"Current screen ID: {app.screen.id}")
        assert app.screen.id == "welcome"
        print("✅ Correctly started on the Welcome Screen.")
        
        # Test Login Screen flow
        await pilot.click("#btn-login")
        await pilot.pause()
        assert app.screen.id == "login"
        print("✅ Successfully opened Login screen.")
        
        # Go to Next step
        app.screen.query_one("#input-username").value = "test_email@example.com"
        await pilot.click("#btn-next")
        await pilot.pause()
        assert app.screen.query_one("#step-credentials").has_class("hidden") is True
        assert app.screen.query_one("#step-authorize").has_class("hidden") is False
        print("✅ Transitioned to Step 2 (Authorize) successfully.")
        
        # Test background redirect server capturing URL
        import urllib.parse
        import requests
        
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI") or "http://127.0.0.1:8888/callback"
        parsed = urllib.parse.urlparse(redirect_uri)
        port = parsed.port or 8888
        
        def send_callback():
            try:
                requests.get(f"http://127.0.0.1:{port}/callback?code=mock_auth_code_for_test")
            except Exception as e:
                print(f"Callback request error: {e}")
                
        await asyncio.to_thread(send_callback)
        await pilot.pause()
        # Check that the input value was automatically populated
        captured_val = app.screen.query_one("#input-redirected-url").value
        assert "mock_auth_code_for_test" in captured_val
        print("✅ Background HTTP redirect listener captured the URL automatically!")
        
        # Click Back
        app.screen.query_one("#btn-back").focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.query_one("#step-credentials").has_class("hidden") is False
        assert app.screen.query_one("#step-authorize").has_class("hidden") is True
        print("✅ Went back to Step 1 successfully.")
        
        # Cancel back to welcome
        await pilot.click("#btn-cancel-credentials")
        await pilot.pause()
        assert app.screen.id == "welcome"
        print("✅ Cancelled login and returned to Welcome screen.")
        
        # Test About Screen modal
        app.screen.query_one("#btn-about").focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "AboutScreen"
        print("✅ About Screen modal opened successfully.")
        # Press escape to close
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.id == "welcome"
        print("✅ About Screen modal closed successfully.")
        
        # Click the "Explore Offline" button to switch to MainPlayerScreen
        await pilot.click("#btn-mock")
        await pilot.pause()
        
        # Verify we transitioned to the player screen
        assert app.screen.id == "player"
        print("✅ Successfully transitioned to MainPlayerScreen.")
        
        # Verify sidebar loaded mock playlists (including featured)
        assert len(app.sidebar.playlists) > 0
        print(f"✅ Loaded {len(app.sidebar.playlists)} mock playlists.")
        
        # Verify suggested/featured playlists are present
        featured = [p for p in app.playlists if p['name'].startswith("✨")]
        assert len(featured) > 0, "Expected at least one ✨ featured playlist"
        print(f"✅ Found {len(featured)} suggested/featured playlist(s).")
        
        # Verify tracks loaded
        assert len(app.track_list.tracks) > 0
        print(f"✅ Loaded {len(app.track_list.tracks)} tracks in first playlist.")
        
        # Verify VolumeWidget initialized
        assert app.volume_widget.volume == 100
        assert app.volume_widget.shuffle is False
        assert app.volume_widget.repeat == "off"
        print("✅ VolumeWidget values verified.")
        
        # Press Shuffle (S)
        await pilot.press("S")
        assert app.shuffle_state is True
        assert app.volume_widget.shuffle is True
        
        await pilot.press("S")
        assert app.shuffle_state is False
        assert app.volume_widget.shuffle is False
        print("✅ Shuffle toggled successfully.")
        
        # Press Repeat (R)
        await pilot.press("R")
        assert app.repeat_state == "track"
        assert app.volume_widget.repeat == "track"
        
        await pilot.press("R")
        assert app.repeat_state == "context"
        assert app.volume_widget.repeat == "context"
        
        await pilot.press("R")
        assert app.repeat_state == "off"
        assert app.volume_widget.repeat == "off"
        print("✅ 3-state Repeat cycle verified successfully.")
        
        # Press Next Track (n)
        await pilot.press("n")
        print("✅ Next Track action triggered.")
        
        # Test Search activation (/)
        await pilot.press("/")
        assert app.search_input.has_class("hidden") is False
        print("✅ Search bar opened successfully.")
        
        # Submit a search query against the global mock catalog
        app.search_input.value = "Queen"
        await pilot.press("enter")
        await pilot.pause()
        # Verify search playlist is created and contains a result from the catalog
        assert any(p['id'] == 'search_results' for p in app.playlists)
        assert app.sidebar.get_selected_playlist()['id'] == 'search_results'
        search_pl = next(p for p in app.playlists if p['id'] == 'search_results')
        assert len(search_pl['items']) > 0, "Expected search results from mock global catalog"
        print("✅ Global mock search results playlist created and populated successfully.")
        
        # Press Esc to close search and remove search playlist
        await pilot.press("escape")
        await pilot.pause()
        assert app.search_input.has_class("hidden") is True
        assert not any(p['id'] == 'search_results' for p in app.playlists)
        print("✅ Search bar closed and search results playlist cleaned up successfully.")
        
        # Test Help modal (?)
        await pilot.press("?")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "HelpScreen"
        print("✅ Help Screen modal opened successfully.")
        # Press enter to close Help screen
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.id == "player"
        print("✅ Help Screen closed successfully.")
        
        # Test Devices modal (d)
        await pilot.press("d")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "DevicesScreen"
        print("✅ Devices Screen modal opened successfully.")
        # Press escape to close Devices screen
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.id == "player"
        print("✅ Devices Screen closed successfully.")

        # Test Settings modal (T) and saving settings
        await pilot.press("T")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "SettingsScreen"
        print("✅ Settings Screen modal opened successfully.")
        
        # Modify input values
        app.screen.query_one("#settings-client-id", Input).value = "test-client-id"
        app.screen.query_one("#settings-username", Input).value = "test-username"
        app.screen.query_one("#settings-password", Input).value = "test-password"
        app.screen.query_one("#settings-device-name", Input).value = "TestDevice"
        
        # Click Save & Apply Settings by focusing and pressing enter
        app.screen.query_one("#btn-settings-save").focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.id == "player"
        print("✅ Settings saved and screen closed successfully.")
        
        # Assert updated environment variables
        assert os.environ.get("SPOTIPY_CLIENT_ID") == "test-client-id"
        assert os.environ.get("SPOTIPY_USERNAME") == "test-username"
        assert os.environ.get("SPOTIPY_PASSWORD") == "test-password"
        assert os.environ.get("SPOTIPY_DEVICE_NAME") == "TestDevice"

        # Verify Device Indicator exists in status bar
        device_ind = app.screen.query_one("#device_indicator")
        assert device_ind is not None
        assert "Device" in str(device_ind.render())
        print("✅ Persistent device indicator verified in status bar.")
        
        # Test Favorite toggle (f)
        track_to_like = app.track_list.get_selected_track()
        tid = track_to_like.id or track_to_like.preview_url or track_to_like.name
        is_liked_initial = tid in app.liked_track_ids
        
        await pilot.press("f")
        await pilot.pause()
        assert (tid in app.liked_track_ids) != is_liked_initial
        print("✅ Track liked/unliked successfully via hotkey.")
        
        # Manually restore to avoid UI selection jump
        if is_liked_initial:
            app.liked_track_ids.add(tid)
            for p in app.playlists:
                if p['id'] == 'liked_songs':
                    if not any((t.id == track_to_like.id if track_to_like.id else (t.preview_url == track_to_like.preview_url or t.name == track_to_like.name)) for t in p['items']):
                        p['items'] = [track_to_like] + p['items']
            app._update_track_list()
            await pilot.pause()
        
        # Test Enqueue (e)
        initial_queue_len = len(app.play_queue)
        await pilot.press("e")
        await pilot.pause()
        assert len(app.play_queue) == initial_queue_len + 1
        app.play_queue.clear()
        print("✅ Track enqueued successfully via hotkey.")
        
        # Test Sidebar toggle (b) - hide sidebar using top-row class
        top_row = app.screen.query_one("#top-row")
        assert top_row.has_class("sidebar-hidden") is False, "Sidebar should be visible initially"
        await pilot.press("b")
        await pilot.pause()
        assert top_row.has_class("sidebar-hidden") is True, "Sidebar should be hidden after pressing b"
        print("✅ Sidebar hidden successfully via 'b' hotkey (responsive top-row class).")
        
        # Toggle sidebar back (b) - show sidebar
        await pilot.press("b")
        await pilot.pause()
        assert top_row.has_class("sidebar-hidden") is False, "Sidebar should be visible after pressing b again"
        print("✅ Sidebar shown successfully via second 'b' press.")
        
        # Test Seek Forward (right arrow) -- needs a track loaded
        app.current_track = app.track_list.get_selected_track()
        app.music_progress.play(240)  # Simulate playing a 4-min track
        await pilot.pause()
        pos_before = app.music_progress.current_position
        await pilot.press("right")
        await pilot.pause()
        assert app.music_progress.current_position >= pos_before, "Seek forward should move position ahead"
        print("✅ Seek forward (right arrow) works correctly.")
        
        # Test Seek Backward (left arrow)
        app.music_progress.current_position = 30.0
        app.music_progress.start_time = time.time() - 30.0
        await pilot.press("left")
        await pilot.pause()
        assert app.music_progress.current_position <= 25.0, f"Expected position ~20s, got {app.music_progress.current_position}"
        print("✅ Seek backward (left arrow) works correctly.")
        
        # Test Natural Track End in repeat='track' mode
        # 1. Set repeat state to 'track'
        app.repeat_state = "track"
        app.volume_widget.repeat = "track"
        app.current_track = app.track_list.get_selected_track()
        app.music_progress.play(30)  # Simulate playing a 30s track
        app.is_playing = True
        
        # 2. Force elapsed time to be >= duration by setting start_time in the past
        app.music_progress.start_time = time.time() - 31.0
        # Trigger the progress tick that handles track ending
        app.music_progress.update_progress()
        await pilot.pause()
        
        # 3. Verify track repeats (it should play the same track again)
        assert app.is_playing is True
        assert app.music_progress.playing is True
        assert app.music_progress.current_position < 5.0, "Progress should reset when repeating"
        print("✅ Natural track end repeats the track correctly in 'track' repeat mode.")
        
        # Test Natural Track End in repeat='context' mode
        # 1. Set repeat state to 'context'
        app.repeat_state = "context"
        app.volume_widget.repeat = "context"
        first_track_name = app.current_track.name
        
        # 2. Force elapsed time to be >= duration
        app.music_progress.start_time = time.time() - (app.music_progress.duration + 1.0)
        app.music_progress.update_progress()
        await pilot.pause()
        
        assert app.current_track.name != first_track_name, "Should advance to next track in context repeat mode"
        assert app.music_progress.playing is True
        print("✅ Natural track end advances to the next track correctly in 'context' repeat mode.")

        # Press quit (q) to exit cleanly
        await pilot.press("q")
        print("✅ App exited cleanly.")
        
    print("🎉 All headless tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_app())
