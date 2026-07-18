import asyncio
from main import RetroSpotifyApp

async def test_app():
    # Start the app in mock mode to avoid any Spotify API network calls
    app = RetroSpotifyApp(force_mock=True)
    
    print("Starting headless app test...")
    async with app.run_test() as pilot:
        print("✅ App mounted successfully!")
        
        # Verify sidebar loaded mock playlists
        assert len(app.sidebar.playlists) > 0
        print(f"✅ Loaded {len(app.sidebar.playlists)} mock playlists.")
        
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
        print("✅ Shuffle toggled successfully.")
        
        # Press Repeat (R)
        await pilot.press("R")
        assert app.repeat_state == "track"
        assert app.volume_widget.repeat == "track"
        print("✅ Repeat toggled successfully.")
        
        # Press Next Track (n)
        await pilot.press("n")
        print("✅ Next Track action triggered.")
        
        # Test Search activation (/)
        await pilot.press("/")
        assert app.search_input.has_class("hidden") is False
        print("✅ Search bar opened successfully.")
        
        # Press Esc to close search
        await pilot.press("escape")
        assert app.search_input.has_class("hidden") is True
        print("✅ Search bar closed successfully via Esc.")
        
        # Press quit (q) to exit cleanly
        await pilot.press("q")
        print("✅ App exited cleanly.")
        
    print("🎉 All headless tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_app())
