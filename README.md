# roblox
Python roblox module, primarily focused on the game client.

The timing of key presses needs to be improved.

# Usage
```python
from roblox import Roblox, RobloxClientMutex
from time import sleep

# allows for multiple clients to be opened
mutex = RobloxClientMutex()

with open("cookie.txt") as f:
  session = Roblox(f.read().strip())

client = session.create_client(1818) # second argument can be a jobId
sleep(8)

client.chat_message("burger")
sleep(2)

client.screenshot().save("me_saying_burger.png")

sleep(5)
client.close()
```
