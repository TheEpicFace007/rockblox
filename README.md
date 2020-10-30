# roblox
Python roblox module, primarily focused on the game client.

# Usage
```python
from roblox import Roblox, RobloxClientMutex
from time import sleep

# allows multiple instances to be opened
mutex = RobloxClientMutex()

with open("cookie.txt") as f:
  session = Roblox(f.read())

client = session.create_client(1818) # second argument can be a jobId
sleep(8)

client.chat_message("burger")
sleep(2)

client.screenshot().show()

sleep(5)
client.close()
```
