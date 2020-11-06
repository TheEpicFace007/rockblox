from enum import Enum, auto

class WebErrorType(Enum):
    INVALID_XSRF = auto()
    UNAUTHENTICATED = auto()
    UNKNOWN = auto()
    ENDPOINT_SPECIFIC = auto()

class InvalidCredentials(Exception):
    pass

class WebError(Exception):
    code: int
    message: int

    def __init__(self, code, message=None, status=None):
        self.code = code
        self.message = message
        self.status = status

    def type(self):
        if self.code == 0:
            if self.status == 403:
                return WebErrorType.INVALID_XSRF

            elif self.status == 401:
                return WebErrorType.UNAUTHENTICATED

            else:
                return WebErrorType.UNKNOWN
        
        else:
            return WebErrorType.ENDPOINT_SPECIFIC