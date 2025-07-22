from __future__ import annotations

import json
import pathlib
import time
from typing import Optional, Protocol, TypedDict, runtime_checkable
import fcntl  # only works on Unix‑likes; OK for dev. Windows users see note below.


class TokenBundle(TypedDict):
    access_token: str
    refresh_token: str
    expires_at: float


# Inteface for token store
@runtime_checkable
class TokenStore(Protocol):
    def get(self, key: str) -> Optional[TokenBundle]: ...
    def set(self, key: str, value: TokenBundle) -> None: ...

# File token store implementation
class FileTokenStore:
    def __init__(self, path: pathlib.Path):
        self.path = path

    def get(self, key: str) -> Optional[TokenBundle]:
        if not self.path.exists():
            return None
        with self.path.open("r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return None

    def set(self,key : str,value: TokenBundle):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            json.dump(value, file)
            file.flush()
            file.truncate()  # Ensure no old data remains
            fcntl.flock(file, fcntl.LOCK_UN)

