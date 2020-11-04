from .input import press_key, release_key, bulk_press_and_release_key
from urllib3 import PoolManager
from threading import Lock
from PIL import Image
import ctypes
import win32ui
import win32gui
import win32process
import win32con
import win32com.client
import subprocess
import time
import os

client_lock = Lock() # used to limit certain interactions to one client at a time
shell = win32com.client.Dispatch("WScript.Shell") # setforeground needs this for some reason

def get_hwnd_for_pid(pid) -> int:
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
                #return False
        return True
        
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds and hwnds[0]

def find_client_path() -> str:
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
        path = template.format(
            username=username,
            version=version)
        if os.path.exists(path):
            return path

    raise FileNotFoundError("Could not find path to client")

class ClientMutex:
    """
    Takes control of the client mutex, allowing multiple clients to be open at the same time.
    Won't work if a client is already open before it is called.
    """
    
    def __init__(self):
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "ROBLOX_singletonMutex")

class Client:
    redeem_url = "https://www.roblox.com/Login/Negotiate.ashx"
    place_id: int
    job_id: str
    hwnd: int
    process: subprocess.Popen

    def __init__(self, session: 'Session', place_id: int, job_id: str=None,
        client_path: str=find_client_path()):
        if not session.id:
            raise("Session is not authenticated")
        self.session = session
        self.client_path = client_path
        self.place_id = place_id
        self.job_id = job_id
        self.process = None
        self.hwnd = None
        self.start()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
    
    def __repr__(self):
        return f"Client for {self.session}"

    def build_joinscript_url(self) -> str:
        pl_url = "https://assetgame.roblox.com/game/PlaceLauncher.ashx"
        if self.place_id and self.job_id:
            script_url = f"{pl_url}?request=RequestGameJob&browserTrackerId={self.session.browser_tracker_id}&placeId={self.place_id}&gameId={self.job_id}&isPlayTogetherGame=false"
        elif self.place_id:
            script_url = f"{pl_url}?request=RequestGame&browserTrackerId={self.session.browser_tracker_id}&placeId={self.place_id}&isPlayTogetherGame=false"
        return script_url
    
    """
    Uses the 'Presence Web-API' to check if the user is currently in-game.
    Can be used as a kind of "ping" to check if the client has disconnected from the game.
    """
    def ping(self, match_place_id: bool=True, match_job_id: bool=False) -> bool:
        resp = self.session.request(
            method="GET",
            url=f"https://api.roblox.com/users/{self.session.id}/onlinestatus",
        )
        presence = resp.json()

        if not presence["PlaceId"]:
            return False
        
        if match_place_id \
            and presence["PlaceId"] != self.place_id:
            return False
        
        if match_job_id \
            and presence["GameId"] != self.job_id:
            return False
        
        return True

    """
    Waits until the client is past the loading screen.
    """
    def wait_for(self, timeout: float=15, check_interval: float=0.25,
        ignored_colors: list=[(45, 45, 45), (255, 255, 255)]):
        start = time.time()
        
        while time.time()-start < timeout:
            screenshot = self.screenshot()
            px_count = screenshot.size[0]*screenshot.size[1]
            dominant_color = sorted(
                screenshot.getcolors(px_count),
                key=lambda t: t[0])[-1][1]
            if not dominant_color in ignored_colors:
                return
            time.sleep(check_interval)
        
        raise TimeoutError
        
    def start(self):
        if self.process:
            raise Exception(".start() has already been called")

        auth_ticket = self.session.request("POST", "https://auth.roblox.com/v1/authentication-ticket") \
            .headers["rbx-authentication-ticket"]
        
        self.process = subprocess.Popen([
            os.path.join(self.client_path, "RobloxPlayerBeta.exe"),
            "--play",
            "-a", self.redeem_url,
            "-t", auth_ticket,
            "-j", self.build_joinscript_url(),
            "-b", str(self.session.browser_tracker_id),
            f"--launchtime={int(time.time()*1000)}",
            "--rloc", "en_us",
            "--gloc", "en_us"
        ])

        start = time.time()
        while time.time()-start < 5:
            hwnd = get_hwnd_for_pid(self.process.pid)
            if hwnd:
                self.hwnd = hwnd
                break
        
        if not self.hwnd:
            self.close()
            raise TimeoutError("Timed out while getting window")

    def close(self):
        self.process.kill()

    def focus(self):
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(self.hwnd)

    def size(self, xo=0, yo=0) -> tuple:
        rect = win32gui.GetWindowRect(self.hwnd)
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        return (w-xo, h-yo)
    
    """
    Captures a `PIL.Image` screenshot of the client window
    """
    def screenshot(self) -> Image:
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
        return im.crop((11,45, *self.size(11, 11))) # crop borders
    
    """
    Attempts to write and send a chat message by simulating keystrokes
    """
    def chat_message(self, message: str):
        with client_lock:
            self.focus()
            press_key(0xBF)
            release_key(0xBF)
            time.sleep(0.05)
            bulk_press_and_release_key(message)
            press_key(0x0D)
            release_key(0x0D)
            time.sleep(0.05)
