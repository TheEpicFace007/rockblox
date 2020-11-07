from .exceptions import WebError, WebErrorType
from urllib.parse import urlsplit
import requests
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
DEFAULT_HOST = "roblox.com"

class Session:
    host: str
    requests_session: requests.Session
    csrf_token: str
    id: int
    name: str
    under_13: bool
    
    def __init__(self, ROBLOSECURITY: str=None, requests_session: requests.Session=None,
                 user_agent: str=USER_AGENT, host: str=DEFAULT_HOST):
        self.host = host

        self.requests_session = requests_session or requests.Session()
        self.cookies = self.requests_session.cookies
        self.requests_session.headers.update({
            "User-Agent": user_agent
        })

        self.csrf_token = None
        self.id = None
        self.name = None
        self.under_13 = None

        self._session_setup()
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)
    
    """
    Represent instance based on username, or string 'Unauthenticated'
    """
    def __repr__(self) -> str:
        if self.id:
            return self.name
        else:
            return "Unauthenticated"

    """
    Return browser tracking ID from RBXEventTrackerV2 cookie
    """
    @property
    def browser_id(self) -> int:
        if self.cookies.get("RBXEventTrackerV2"):
            return int(re.search(r"browserid=(\d+?)",
                       self.cookies["RBXEventTrackerV2"]).group(1))
    """
    Build URL based on self.host, subdomain and path
    """                            
    def build_url(self, subdomain: str, path: str="") -> str:
        # redirect under 13 accounts to the web. subdomain
        if subdomain.lower() == "www" and self.under_13:
            subdomain = "web"
        return f"https://{subdomain}.{self.host}{path}"

    """
    Attempt to authenticate using provided .ROBLOSECURITY cookie
    """
    def auth_from_cookie(self, ROBLOSECURITY: str):
        self.cookies.set(
            domain=f".{self.host}", name=".ROBLOSECURITY", value=ROBLOSECURITY,
            secure=True)
        self._auth_setup()

    def _auth_setup(self):
        with self.request("GET",
            self.build_url("users", "/v1/users/authenticated")) as resp:
            user = resp.json()
            self.id = user["id"]
            self.name = user["name"]

        # visit homepage to get tracking cookies, initial xsrf token and under_13
        with self.request("GET", self.build_url("www", "/home"),
                          allow_redirects=True) as resp:
            self.under_13 = re.search(
                r"data-isunder13=\"?(true|false)\"?",
                resp.text
            ).group(1) == "true"
            self.csrf_token = re.search(
                r"<script>Roblox\.XsrfToken\.setToken\('([A-z0-9+-_]{8,14})'\);<\/script>",
                resp.text
            ).group(1)

    """
    Gather tracking cookies from pages that a real browser would visit
    """
    def _session_setup(self):
        self.request("GET", self.build_url("www", "/"))
        self.request("GET", self.build_url("www", "/timg/rbx"))
    
    """
    Build dict of headers based on method, host and extra headers
    """
    def _build_headers(self, method: str, host: str, headers: dict={}) -> dict:
        if host.lower() == self.host.lower() \
            or host.lower().endswith(f".{self.host}"):
            headers["Origin"] = self.build_url("www")
            headers["Referer"] = self.build_url("www", "/")
            if method in ["POST", "PATCH", "DELETE", "PUT"]:
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token
        return headers

    """
    Callback for responses from .request
    """
    def _process_response(self, resp: requests.Response):
        # set new xsrf token if specified
        if "x-csrf-token" in resp.headers:
            self.csrf_token = resp.headers["x-csrf-token"]

        # process json errors if specified
        if "/json" in resp.headers.get("content-type", ""):
            data = resp.json()
            resp.json = lambda: data # if we parse it, might as well cache it
            for err in data.get("errors", []):
                raise WebError(
                    err.get("code"), err.get("message"), resp.status_code)

    """
    Wrapper for requests_session.request
    """
    def request(self, method: str, url: str, params: dict=None,
                data: (str, bytes, dict)=None, json: (str, dict)=None, headers: dict={},
                cookies: dict=None, files: dict=None, timeout: float=None,
                allow_redirects: bool=False, proxies: dict=None) -> requests.Response:
        def wrap():
            parsed_url = urlsplit(url)
            headers.update(self._build_headers(method, parsed_url.hostname))

            resp = self.requests_session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                cookies=cookies,
                files=files,
                timeout=timeout,
                allow_redirects=allow_redirects,
                proxies=proxies
            )
            return resp

        resp = wrap()
        try:
            self._process_response(resp)
        except WebError as err:
            # mismatching csrf token, re-send request
            if err.type() == WebErrorType.INVALID_XSRF:
                resp = wrap()
            else:
                raise
        
        return resp
