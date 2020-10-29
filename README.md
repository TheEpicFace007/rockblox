# roblox
Python roblox module, primarily focused on the game client.

# Usage
```python
from roblox import Roblox
import time

with open("cookie.txt") as f:
  session = Roblox(f.read())

client = session.create_client(1818) # second argument can be a jobId
time.sleep(8)

client.chat_message("burger")
time.sleep(2)

client.screenshot().show()

time.sleep(5)
client.close()
```
