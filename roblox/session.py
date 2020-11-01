from urllib3 import PoolManager
from urllib.parse import urlsplit
import json
import time
import random

class Session:
    manager: PoolManager
    csrf_token: str
    browser_tracker_id: int
    ROBLOSECURITY: str
    id: int
    name: str
        
    def __init__(self, ROBLOSECURITY: str=None, manager: PoolManager=None):
        self.manager = manager or PoolManager()
        self.csrf_token = None
        self.browser_tracker_id = random.randint(1, 1231324234)
        self.ROBLOSECURITY = None
        self.id = None
        self.name = None
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)
            
    def __repr__(self) -> str:
        if self.id:
            return self.name
        else:
            return "Unauthenticated"

    def auth_from_cookie(self, ROBLOSECURITY: str):
        self.ROBLOSECURITY = ROBLOSECURITY

        auth_info = self.get_auth()
        if not auth_info:
            raise Exception("Invalid or expired .ROBLOSECURITY cookie")

        self.id = auth_info["id"]
        self.name = auth_info["name"]

    def get_cookies(self, host: str) -> dict:
        cookies = {}
        if host.lower().endswith(".roblox.com"):
            if self.ROBLOSECURITY:
                cookies[".ROBLOSECURITY"] = self.ROBLOSECURITY
        return cookies
    
    def get_headers(self, method: str, host: str) -> dict:
        headers = {}
        if host.lower().endswith(".roblox.com"):
            headers["Origin"] = "https://www.roblox.com"
            headers["Referer"] = "https://www.roblox.com/"
            if method == "POST":
                headers["Content-Type"] = "application/json"
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token
        return headers

    def get_auth(self) -> dict:
        r = self.request("GET", "https://users.roblox.com/v1/users/authenticated")
        return r.status == 200 and r.json()
    
    def request(self, method: str, url: str, headers: dict={}, data=None):
        purl = urlsplit(url)
        data = data and json.dumps(data, separators=(",",":"))
        headers.update(self.get_headers(method, purl.hostname))
        cookies = self.get_cookies(purl.hostname)
        if cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k,v in cookies.items())

        resp = self.manager.request(
            method=method,
            url=url,
            headers=headers,
            body=data
        )

        if "x-csrf-token" in resp.headers:
            self.csrf_token = resp.headers["x-csrf-token"]
            return self.request(method, url, headers, data)

        resp.json = lambda: json.loads(resp.data)
        return resp