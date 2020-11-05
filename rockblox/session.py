from urllib3 import PoolManager, Retry
from urllib.parse import urlsplit, urlencode
import json
import time
import random
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
_json = json

class Session:
    manager: PoolManager
    csrf_token: str
    browser_tracker_id: int
    ROBLOSECURITY: str
    id: int
    name: str
        
    def __init__(self, ROBLOSECURITY: str=None, manager: PoolManager=None,
                 user_agent=USER_AGENT):
        self.manager = manager or PoolManager()
        self.user_agent = user_agent

        self.csrf_token = None
        self.browser_tracker_id = None

        self.RBXImageCache = None
        self.GuestData = None
        self.RBXSource = None
        self.RBXEventTrackerV2 = None
        self.RBXViralAcquisition = None
        self.RBXSessionTracker = None
        self.RequestVerificationToken = None
        self.ROBLOSECURITY = None

        self.id = None
        self.name = None

        self.setup()
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)
            
    def __repr__(self) -> str:
        if self.id:
            return self.name
        else:
            return "Unauthenticated"
            
    def setup(self):
        index_resp = self.request("GET", "https://www.roblox.com/",
                                  headers={"accept-language": "en-US,en;q=0.9"})
        self.GuestData = index_resp.cookies["GuestData"]
        self.RBXSource = index_resp.cookies["RBXSource"]
        self.RBXViralAcquisition = index_resp.cookies.get("RBXViralAcquisition")
        self.RBXEventTrackerV2 = index_resp.cookies.get("RBXEventTrackerV2")
        timg_resp = self.request("GET", "https://www.roblox.com/timg/rbx")
        self.RBXImageCache = timg_resp.cookies["RBXImageCache"]

        if self.RBXEventTrackerV2:
            self.browser_tracker_id = int(re.search(r"browserid=(\d+?)",
                                                    self.RBXEventTrackerV2) \
                                                    .group(1))

    def auth_from_cookie(self, ROBLOSECURITY: str):
        self.ROBLOSECURITY = ROBLOSECURITY

        auth_resp = self.request("GET", "https://users.roblox.com/v1/users/authenticated")
        if auth_resp.status != 200:
            raise Exception("Invalid or expired .ROBLOSECURITY cookie")
        
        auth_info = auth_resp.json()
        self.id = auth_info["id"]
        self.name = auth_info["name"]

        tos_resp = self.request("GET", "https://www.roblox.com/usercheck/show-tos?isLicensingTermsCheckNeeded=False",
                                headers={"accept-language": "en-US,en;q=0.9"})
        self.RBXSessionTracker = tos_resp.cookies["RBXSessionTracker"]

    def get_cookies(self, host: str) -> dict:
        cookies = {}
        if host.lower().endswith(".roblox.com"):
            if self.ROBLOSECURITY:
                cookies.update({
                    ".ROBLOSECURITY": self.ROBLOSECURITY,
                    "GuestData": self.GuestData,
                    "RBXSource": self.RBXSource,
                    "RBXImageCache": self.RBXImageCache,
                    "RBXEventTrackerV2": self.RBXEventTrackerV2,
                    "RBXViralAcquisition": self.RBXViralAcquisition,
                    "RBXSessionTracker": self.RBXSessionTracker,
                    "__RequestVerificationToken": self.RequestVerificationToken,
                    "rbx-ip2": ""
                })
        return cookies
    
    def get_headers(self, method: str, host: str, mode: str) -> dict:
        headers = {}
        headers.update({
            "User-Agent": self.user_agent
        })
        if host.lower().endswith(".roblox.com"):
            headers["Origin"] = "https://www.roblox.com"
            headers["Referer"] = "https://www.roblox.com/"
            if method in ["POST", "PATCH", "PUT", "DELETE"]:
                if mode == "json":
                    headers["Content-Type"] = "application/json"
                elif mode == "url":
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                elif mode == "xml":
                    headers["Content-Type"] = "text/xml"
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token
        return headers

    def _on_response(self, resp):
        if "__RequestVerificationToken" in resp.cookies:
            self.RequestVerificationToken = resp.cookies["__RequestVerificationToken"]
    
    def request(self, method: str, url: str, headers: dict={}, data=None, mode="json"):
        purl = urlsplit(url)
        headers.update(self.get_headers(method, purl.hostname, mode))
        cookies = self.get_cookies(purl.hostname)
        if cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k,v in cookies.items() if v != None)

        if data and not type(data) in [str, bytes]:
            if mode == "json":
                data = _json.dumps(data, separators=(",",":"))
            elif mode == "url":
                data = urlencode(data)
    
        resp = self.manager.request(
            method=method,
            url=url,
            headers=headers,
            body=data,
            retries=Retry(redirect=False)
        )

        if "x-csrf-token" in resp.headers:
            self.csrf_token = resp.headers["x-csrf-token"]
            return self.request(method, url, headers, data)

        resp.cookies = {
            cv.split("=")[0]: cv.split(";")[0].split("=", 1)[1]
            for cn, cv in resp.headers.items()
            if cn == "set-cookie"
        }
        resp.json = lambda: _json.loads(resp.data)
        self._on_response(resp)
        return resp