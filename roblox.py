from urllib3 import PoolManager
from urllib.parse import urlsplit
from input import press_key, release_key, bulk_press_and_release_key
from threading import Lock
from PIL import Image
import win32gui
import win32ui
import win32con
import win32process
import win32com.client
import json
import time
import subprocess
import random
import ctypes
import os

client_lock = Lock() # used to limit certain interactions to one client at a time
shell = win32com.client.Dispatch("WScript.Shell") # setforeground needs this for some reason

# get the current client version
with PoolManager() as pm:
    CLIENT_VERSION = pm.request("GET", "http://setup.roblox.com/version.txt") \
        .data.decode("UTF-8").strip()


def get_hwnds_for_pid(pid): # TODO: make this less bulkier
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True
        
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds

def find_client_path():
    templates = [
        "C:\\Users\\{username}\\AppData\\Local\\Roblox\\Versions\\{version}",
        "C:\\Program Files (x86)\\Roblox\\Versions\\{version}",
        "C:\\Program Files\\Roblox\\Versions\\{version}",
    ]
    username = os.environ["USERPROFILE"].split("\\")[-1]
    
    for template in templates:
        path = template \
            .format(
                username=username,
                version=CLIENT_VERSION)
        if os.path.exists(path):
            return path

    raise FileNotFoundError("Could not find path to client")

class RobloxClientMutex:
    """
    Takes control of the client mutex, allowing multiple clients to be open at the same time.
    Won't work if a client is already open before it is called.
    """
    
    def __init__(self):
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ROBLOX_singletonMutex")

class Client:
    redeem_url = "https://www.roblox.com/Login/Negotiate.ashx"

    def __init__(self, parent, place_id, job_id=None):
        self.parent = parent
        self.place_id = place_id
        self.job_id = job_id
        self.process = None
        self.hwnd = None
        self.start()
    
    def __repr__(self):
        return f"Client for {self.parent}"

    def build_joinscript_url(self):
        pl_url = "https://assetgame.roblox.com/game/PlaceLauncher.ashx"
        if self.place_id and self.job_id:
            script_url = f"{pl_url}?request=RequestGameJob&browserTrackerId={self.parent.browser_tracker_id}&placeId={self.place_id}&gameId={self.job_id}&isPlayTogetherGame=false"
        elif self.place_id:
            script_url = f"{pl_url}?request=RequestGame&browserTrackerId={self.parent.browser_tracker_id}&placeId={self.place_id}&isPlayTogetherGame=false"
        return script_url
    
    """
    Uses the 'Presence Web-API' to check if the user is currently in-game.
    Can be used as a kind of "ping" to check if the client has disconnected from the game.
    """
    def is_in_game(self, match_job_id=False):
        resp = self.parent.request(
            method="POST",
            url="https://presence.roblox.com/v1/presence/users",
            data={"userIds": [self.parent.id]}
        )
        me = resp.json()["userPresences"][0]
        return me["placeId"] == self.place_id \
            and ((self.job_id and match_job_id and me["gameId"] == self.job_id) \
                or (not self.job_id or not match_job_id))

    """
    Waits until the client is past the loading screen.
    """
    def wait_for(self, timeout=15, check_interval=0.25):
        t = time.time()
        
        while (time.time()-t) < timeout:
            screenshot = self.screenshot()
            pixels = screenshot.getcolors(screenshot.size[0]*screenshot.size[1])
            sorted_pixels = sorted(pixels, key=lambda t: t[0])
            dominant_color = sorted_pixels[-1][1]
            if dominant_color != (45, 45, 45):
                return
            time.sleep(check_interval)
        
        raise TimeoutError
        
    def start(self):
        if self.process:
            raise Exception(".start() has already been called")

        auth_ticket = self.parent.request("POST", "https://auth.roblox.com/v1/authentication-ticket") \
            .headers["rbx-authentication-ticket"]
        
        launch_time = int(time.time()*1000)
        self.process = subprocess.Popen([
            find_client_path() + "\\RobloxPlayerBeta.exe",
            "--play",
            "-a", self.redeem_url,
            "-t", auth_ticket,
            "-j", self.build_joinscript_url(),
            "-b", str(self.parent.browser_tracker_id),
            "--launchtime=" + str(launch_time),
            "--rloc", "en_us",
            "--gloc", "en_us"
        ])

        start_time = time.time()
        while (time.time()-start_time) < 5:
            hwnds = get_hwnds_for_pid(self.process.pid)
            if hwnds:
                self.hwnd = hwnds[0]
                break
        
        if not self.hwnd:
            self.close()
            raise TimeoutError("Timed out while getting window")

        time.sleep(1)

    def close(self):
        self.process.kill()

    def focus(self):
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(self.hwnd)

    def size(self, xo=0, yo=0):
        rect = win32gui.GetWindowRect(self.hwnd)
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        return (w-xo, h-yo)

    def screenshot(self):
        dc_handle = win32gui.GetWindowDC(self.hwnd)
        dcObj=win32ui.CreateDCFromHandle(dc_handle)
        cDC=dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, *self.size())
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0,0),self.size(), dcObj, (0,0), win32con.SRCCOPY)
        bmpinfo = dataBitMap.GetInfo()
        bmpstr = dataBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.DeleteObject(dataBitMap.GetHandle())
        win32gui.ReleaseDC(self.hwnd, dc_handle)
        return im.crop((11,45, *self.size(11, 11)))

    def chat_message(self, message):
        with client_lock:
            self.focus()
            press_key(0xBF)
            release_key(0xBF)
            time.sleep(0.05)
            bulk_press_and_release_key(message)
            press_key(0x0D)
            release_key(0x0D)
            time.sleep(0.05)

class Roblox:
    def __init__(self, ROBLOSECURITY=None, manager=None):
        self.manager = manager or PoolManager()
        self.csrf_token = None
        self.browser_tracker_id = random.randint(1, 1231324234)
        self.ROBLOSECURITY = None
        self.id = None
        self.name = None
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)
            
    def __repr__(self):
        if self.id:
            return self.name
        else:
            return "Unauthenticated"

    def auth_from_cookie(self, ROBLOSECURITY):
        self.ROBLOSECURITY = ROBLOSECURITY

        auth_info = self.get_auth()
        if not auth_info:
            raise Exception("Invalid or expired .ROBLOSECURITY cookie")

        self.id = auth_info["id"]
        self.name = auth_info["name"]

    def get_cookies(self, host):
        cookies = {}
        if host.lower().endswith(".roblox.com"):
            if self.ROBLOSECURITY:
                cookies[".ROBLOSECURITY"] = self.ROBLOSECURITY
        return cookies
    
    def get_headers(self, method, host):
        headers = {}
        if host.lower().endswith(".roblox.com"):
            headers["Origin"] = "https://www.roblox.com"
            headers["Referer"] = "https://www.roblox.com/"
            if method == "POST":
                headers["Content-Type"] = "application/json"
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token
        return headers

    def get_auth(self):
        r = self.request("GET", "https://users.roblox.com/v1/users/authenticated")
        return r.status == 200 and r.json()
    
    def request(self, method, url, headers={}, data=None):
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

    def create_client(self, place_id, job_id=None):
        return Client(self, place_id, job_id)
