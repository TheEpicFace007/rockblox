from .exceptions import WebError, ErrorType
from urllib.parse import urlsplit
import requests
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"

## TODO:
## - Set .under_13, once a new endpoint for it is found

class Session:
    host: str
    requests_session: requests.Session
    csrf_token: str
    browser_tracker_id: int
    ROBLOSECURITY: str
    id: int
    name: str
        
    def __init__(self, ROBLOSECURITY: str=None, requests: requests.Session=None,
                 user_agent=USER_AGENT, host="roblox.com"):
        self.host = host
        self.requests_session = requests or requests.Session()
        self.cookies = self.requests_session.cookies

        self.csrf_token = None
        self.browser_id = None

        self.id = None
        self.name = None
        self.under_13 = None

        self.requests_session.headers.update({
            "User-Agent": user_agent
        })
        self._session_setup()
        if ROBLOSECURITY:
            self.auth_from_cookie(ROBLOSECURITY)
            
    def __repr__(self) -> str:
        if self.id:
            return self.name
        else:
            return "Unauthenticated"

    def _session_setup(self):
        self.request("GET", self.build_url("www", "/"))
        self.request("GET", self.build_url("www", "/timg/rbx"))

    @property
    def browser_id(self):
        if self.cookies.get("RBXEventTrackerV2"):
            return int(re.search(r"browserid=(\d+?)",
                                              self.cookies["RBXEventTrackerV2"]) \
                                              .group(1))
                                    
    def build_url(self, subdomain="www", path=""):
        if subdomain.lower() == "www" and self.under_13:
            subdomain = "web"
        return f"https://{subdomain}.{self.host}{path}"

    def auth_from_cookie(self, ROBLOSECURITY: str):
        self.cookies.create_cookie(
            domain=f".{self.host}", name=".ROBLOSECURITY", value=ROBLOSECURITY)

        auth_resp = self.request("GET", self.build_url("users", "/v1/users/authenticated"))
        if auth_resp.status != 200:
            raise Exception("Invalid or expired .ROBLOSECURITY cookie")
        
        auth_info = auth_resp.json()
        self.id = auth_info["id"]
        self.name = auth_info["name"]

        self.request("GET", self.build_url("www", "/usercheck/show-tos?isLicensingTermsCheckNeeded=False"),
                     headers={"accept-language": "en-US,en;q=0.9"})
    
    def get_headers(self, method: str, host: str, headers: dict={}) -> dict:
        headers = headers
        if host.lower().endswith(f".{host}"):
            headers["Origin"] = self.build_url("www")
            headers["Referer"] = self.build_url("www", "/")
            if method in ["POST", "PATCH", "PUT", "DELETE"]:
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token
        return headers

    def _process_response(self, resp):
        # set new xsrf token if specified
        if "x-csrf-token" in resp.headers:
            self.csrf_token = resp.headers["x-csrf-token"]

        # process json errors if specified
        if "/json" in resp.headers.get("content-type", ""):
            data = resp.json()
            resp.json = lambda: data
            for err in data.get("errors", []):
                raise WebError(
                    err.get("code"), err.get("msg"))

    def request(self, method: str, url: str, params: dict=None,
                data: (str, bytes, dict)=None, json: (str, dict)=None, headers: dict={},
                cookies: dict=None, files: dict=None, timeout: float=None,
                allow_redirects: bool=False, proxies: dict=None):
        resp = None
        def wrap():
            global resp
            parsed_url = urlsplit(url)
            headers.update(self.get_headers(method, parsed_url.hostname))

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

        wrap()
        try:
            self._process_response(resp)
        except WebError as err:
            # mismatching csrf token, re-send request
            if err.type() == ErrorType.INVALID_XSRF:
                wrap()
            else:
                raise

        return resp