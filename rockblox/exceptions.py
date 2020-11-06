from enum import Enum, auto

class ErrorType(Enum):
    INVALID_XSRF = auto()
    UNAUTHENTICATED = auto()
    ENDPOINT_SPECIFIC = auto()

class WebError(Exception):
    code: int
    message: int

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def type(self):
        if self.message == "Token Validation Failed":
            return ErrorType.INVALID_XSRF

        elif self.message == "Authorization has been denied for this request.":
            return ErrorType.UNAUTHENTICATED
        
        else:
            return ErrorType.ENDPOINT_SPECIFIC