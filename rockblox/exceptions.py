from enum import Enum, auto

class WebErrorType(Enum):
    INVALID_XSRF = auto()
    UNAUTHENTICATED = auto()
    TOO_MANY_REQUESTS = auto()
    UNKNOWN = auto()
    ENDPOINT_SPECIFIC = auto()

# login error, or invalid cookie
class InvalidCredentials(Exception):
    pass

class WebError(Exception):
    code: int
    message: int

    def __init__(self, code, message=None, status=None):
        self.code = code
        self.message = message
        self.status = status

    def __repr__(self):
        return f"{self.message} ({self.code} - {self.status})"

    def type(self):
        if self.status == 429:
            return WebErrorType.TOO_MANY_REQUESTS
        
        if self.code == 0:
            if self.status == 403:
                return WebErrorType.INVALID_XSRF

            elif self.status == 401:
                return WebErrorType.UNAUTHENTICATED

            else:
                return WebErrorType.UNKNOWN
        
        else:
            return WebErrorType.ENDPOINT_SPECIFIC