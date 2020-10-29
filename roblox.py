from urllib3 import PoolManager
from urllib.parse import urlsplit
from input import press_key, release_key, bulk_press_and_release_key
from threading import Lock
from PIL import Image, ImageGrab
import json
import time
import subprocess
import random
import ctypes
import os
import win32gui
import win32process
import win32gui
import win32com.client

shell = win32com.client.Dispatch("WScript.Shell")
client_lock = Lock()

def get_hwnds_for_pid(pid):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True
        
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds

def find_roblox_client_path():
    templates = [
        "C:\\Users\\{username}\\AppData\\Local\\Roblox\\Versions\\{version}",
        "C:\\Program Files (x86)\\Roblox\\Versions\\{version}",
        "C:\\Program Files\\Roblox\\Versions\\{version}",
    ]
    username = os.environ["USERPROFILE"].split("\\")[-1]
    with PoolManager() as pm:
        version = pm.request("GET", "http://setup.roblox.com/version.txt") \
            .data.decode("UTF-8").strip()
    
    for template in templates:
        path = template \
            .format(
                username=username,
                version=version)
        if os.path.exists(path):
            return path

    raise FileNotFoundError("Could not find path to client")

class RobloxClientMutex:
    def __init__(self):
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ROBLOX_singletonMutex")

class Client:
    def __init__(self, parent, script_url):
        self.parent = parent
        self.process = None
        self.hwnd = None
        self.auth_ticket = None
        self.script_url = script_url
        self.redeem_url = "https://www.roblox.com/Login/Negotiate.ashx"
        self.start()

    def start(self):
        if self.process:
            raise Exception(".start() has already been called")

        self.auth_ticket = self.parent.request("POST", "https://auth.roblox.com/v1/authentication-ticket") \
            .headers["rbx-authentication-ticket"]
        
        launch_time = int(time.time()*1000)
        self.process = subprocess.Popen([
            find_roblox_client_path() + "\\RobloxPlayerBeta.exe",
            "--play",
            "-a", self.redeem_url,
            "-t", self.auth_ticket,
            "-j", self.script_url,
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

    def close(self):
        self.process.kill()

    def focus(self):
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(self.hwnd)

    def screenshot(self):
        with client_lock:
            self.focus()
            press_key(0x7A)
            release_key(0x7A)
            time.sleep(0.1)
            image = ImageGrab.grab()
            press_key(0x7A)
            release_key(0x7A)
        return image

    def chat_message(self, message):
        with client_lock:
            self.focus()
            press_key(0xBF)
            time.sleep(0.03)
            release_key(0xBF)
            time.sleep(0.05)
            bulk_press_and_release_key(message)
            press_key(0x0D)
            time.sleep(0.03)
            release_key(0x0D)
            time.sleep(0.08)

class Roblox:
    def __init__(self, ROBLOSECURITY=None, manager=None):
        self.manager = manager or PoolManager()
        self.csrf_token = None
        self.browser_tracker_id = random.randint(1, 1231324234)
        self.ROBLOSECURITY = None
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)

    def auth_from_cookie(self, ROBLOSECURITY):
        self.ROBLOSECURITY = ROBLOSECURITY

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

    def is_auth(self):
        r = self.request("GET", "https://economy.roblox.com/v2/users/transactions?transactionType=Sale&limit=10")
        return r.status == 200
    
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

    def create_client(self, place_id, game_id=None):
        if place_id and game_id:
            script_url = f"https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGameJob&browserTrackerId={self.browser_tracker_id}&placeId={place_id}&gameId={game_id}&isPlayTogetherGame=false"
        else:
            script_url = f"https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGame&browserTrackerId={self.browser_tracker_id}&placeId={place_id}&isPlayTogetherGame=false"

        return Client(self, script_url)
