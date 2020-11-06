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

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def type(self):
        if self.code == 0:
            if self.message == "Token Validation Failed":
                return WebErrorType.INVALID_XSRF

            elif self.message == "Authorization has been denied for this request.":
                return WebErrorType.UNAUTHENTICATED

            else:
                return WebErrorType.UNKNOWN
        
        else:
            return WebErrorType.ENDPOINT_SPECIFIC