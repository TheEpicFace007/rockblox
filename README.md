# roblox
Python roblox module, primarily focused on the game client.

Since this module doesn't directly hook into the client, it is limited by the following things:
- It can only interact with one client at a time
- The timing of key presses may cause chat messages to be cut off

# Usage
```python
from roblox import Roblox, RobloxClientMutex
from time import sleep

# allows for multiple clients to be opened
mutex = RobloxClientMutex()

with open("cookie.txt") as f:
  session = Roblox(f.read().strip())

client = session.create_client(1818) # second argument can be a jobId
client.wait_for(15) # wait up to 15 seconds, for user to appear in game

client.chat_message("burger")
sleep(2)

client.screenshot().save("me_saying_burger.png")

sleep(2)
client.close()
```
