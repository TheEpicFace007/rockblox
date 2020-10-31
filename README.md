# roblox
Python roblox module, primarily focused on the game client.

Since this module doesn't directly hook into the client, it is limited by the following things:
- It can only interact with one client at a time
- Keystrokes may fail to register in time, causing chat messages to cut off

DM me if you're smart, and know a way to send keystrokes to the client, without focusing the window.

# Usage
```python
from roblox import Roblox, RobloxClientMutex
from time import sleep

mutex = RobloxClientMutex() # allows for multiple clients to be open at once

with open("cookie.txt") as f:
  session = Roblox(f.read().strip())

client = session.create_client(1818) # second argument can be a jobId
client.wait_for(15) # wait up to 15 seconds for game to load

client.chat_message("burger")
sleep(1)

client.screenshot().show()
client.close()
```

# Documentation

### Client.wait_for(timeout=15, check_interval=0.25)
Waits until the client is past the loading screen. It uses the screenshot method and therefore may not be 100% reliable.

### Client.is_in_game(match_job_id=False)
Checks if the user is currently in-game using the presence web-api, can be used as a kind of "ping" to check if the client has disconnected from the game.

### Client.screenshot()
Returns a `PIL.Image` screenshot of the client in it's current window size.

### Client.chat_message(message)
Attempts to write and send a chat message by simulating keystrokes on the client.

### Client.close()
Kills the client process.
