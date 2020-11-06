import os

from .session import Session
if os.name == "nt":
    from .client import Client
    from .client import ClientMutex
from .exceptions import WebError
from .exceptions import WebErrorType