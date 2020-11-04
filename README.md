# rockblox
Python Roblox wrapper, primarily focused on the game client.

Since this module doesn't directly hook into the client, it is limited by the following things:
- It can only interact with one client at a time
- Keystrokes may fail to register in time, causing chat messages to cut off

DM me if you know of a way to send keystrokes to the client, without focusing the window.

# Setup
```bash
pip install -U git+https://github.com/h0nde/rockblox.git
```

# Usage
```python
from rockblox import Roblox, RobloxClient, RobloxClientMutex
from time import sleep

mutex = RobloxClientMutex() # allows multiple clients to be open at once

# create new session using cookie.txt
with open("cookie.txt") as f:
  session = Roblox(f.read().strip())

with RobloxClient(session, 1818) as client:
  client.wait_for(15) # wait up to 15 seconds for game to load
  client.chat_message("burger")
  sleep(1)
  client.screenshot().show()
```

# Documentation
### Roblox(ROBLOSECURITY, manager=None)
Creates a new session instance. The manager parameter accepts a urllib3.ProxyManager object, however, opened clients will not use this.

### RobloxClientMutex()
Takes control of the client mutex, so that multiple client instances can be open at the same time. Won't work if an instance is already open before it is called.

### RobloxClient(session, place_id, job_id=None, client_path=default)
Creates a new client instance.

### RobloxClient.wait_for(timeout=15, check_interval=0.25, ignore_colors=\[(45, 45, 45)])
Waits until the client is past the loading screen. This uses the screenshot method and therefore may not be 100% reliable.

### RobloxClient.ping(match_place_id=True, match_job_id=False) -> bool
Checks if the user is currently in-game using the presence web-api, can be used as a kind of "ping" to check if the client has disconnected from the game.

### RobloxClient.screenshot() -> PIL.Image
Returns a `PIL.Image` screenshot of the client in it's current window size.

### RobloxClient.chat_message(message)
Attempts to write and send a chat message by simulating keystrokes on the client.

### RobloxClient.close()
Kills the client process.
