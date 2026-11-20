"""Inter-process command listener.

Preserves the original wire protocol (``localhost:6234`` with authkey
``b'dendroFun'``) so external tools that submit folders continue to work, but
fixes the original bug that recreated the listener socket on every connection
and adds error handling and a clean shutdown path.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from multiprocessing.connection import Client, Listener

_ADDRESS = ("localhost", 6234)
_AUTHKEY = b"dendroFun"


class IPCListener(threading.Thread):
    """Background listener that forwards received folder paths to a handler."""

    def __init__(self, handler: Callable[[str], None]) -> None:
        super().__init__(daemon=True)
        self._handler = handler
        self._stop = threading.Event()
        self._listener: Listener | None = None

    def run(self) -> None:
        try:
            self._listener = Listener(_ADDRESS, authkey=_AUTHKEY)
        except OSError as e:
            print(f"IPC listener unavailable: {e}")
            return

        while not self._stop.is_set():
            try:
                conn = self._listener.accept()
            except OSError:
                break  # listener closed during shutdown
            try:
                msg = conn.recv()
                self._handler(str(msg))
            except (EOFError, OSError) as e:
                print(f"IPC connection error: {e}")
            finally:
                conn.close()

    def shutdown(self) -> None:
        """Stop the listener and unblock a pending ``accept()``."""

        self._stop.set()
        if self._listener is not None:
            # Wake the blocked accept() by connecting to ourselves.
            try:
                client = Client(_ADDRESS, authkey=_AUTHKEY)
                client.send("")
                client.close()
            except OSError:
                pass
            try:
                self._listener.close()
            except OSError:
                pass
