#!/usr/bin/env python
# coding: utf-8
"""
Sending files between computers in the classroom.

One computer is joined to the printer and types receive.  Everybody else
types send.  The teacher then prepares and prints whatever arrived.

The old version listened for files and waited for a print command at the
same time, which meant a student could not do anything else while waiting.
Now receiving is its own job with a clear end: type done.
"""

import os
import socket
import threading
from pathlib import Path

from .texts import say

CHUNK = 65536
HEADER_LIMIT = 512


def _safe_name(name):
    """Never let a name that arrives over the network escape the folder."""
    name = os.path.basename(name.replace("\\", "/")).strip()
    keep = [c for c in name if c.isalnum() or c in "._- "]
    name = "".join(keep).strip() or "file"
    if not name.lower().endswith((".gcode", ".stl", ".3mf", ".obj", ".bgz")):
        name += ".gcode"
    return name


def send_file(path, ip, port, sender_name):
    """Send one file.  Returns (ok, message)."""
    path = Path(path)
    if not path.exists():
        return False, "The file is missing. Type prepare first."

    filename = f"{sender_name}_{path.name}" if sender_name else path.name
    size = path.stat().st_size

    try:
        with socket.create_connection((ip, int(port)), timeout=15) as sock:
            header = f"{filename}\n{size}\n".encode("utf-8")
            sock.sendall(header.ljust(HEADER_LIMIT, b" "))

            sent = 0
            step = max(1, size // 10)
            next_report = step
            with open(path, "rb") as handle:
                while True:
                    chunk = handle.read(CHUNK)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent += len(chunk)
                    if sent >= next_report:
                        say("send_progress", percent=int(sent * 100 / size))
                        next_report += step
    except ConnectionRefusedError:
        return False, "Nobody is listening on that computer. Ask them to type receive."
    except socket.timeout:
        return False, "The other computer did not answer."
    except OSError as problem:
        return False, str(problem)

    return True, filename


class Receiver:
    """Waits for files in the background while the student keeps working."""

    def __init__(self, port, folder):
        self.port = int(port)
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.files = []
        self.running = False
        self._thread = None
        self._error = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        return self.files

    def _listen(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("0.0.0.0", self.port))
                server.listen(8)
                server.settimeout(1.0)

                while self.running:
                    try:
                        connection, address = server.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    threading.Thread(target=self._receive_one,
                                     args=(connection, address),
                                     daemon=True).start()
        except OSError as problem:
            self._error = str(problem)
            self.running = False

    def _receive_one(self, connection, address):
        with connection:
            connection.settimeout(30)
            try:
                header = b""
                while len(header) < HEADER_LIMIT:
                    piece = connection.recv(HEADER_LIMIT - len(header))
                    if not piece:
                        return
                    header += piece
                lines = header.decode("utf-8", "ignore").strip().splitlines()
                filename = _safe_name(lines[0] if lines else "file")

                target = self.folder / filename
                count = 2
                while target.exists():
                    target = self.folder / f"{target.stem}_{count}{target.suffix}"
                    count += 1

                with open(target, "wb") as handle:
                    while True:
                        chunk = connection.recv(CHUNK)
                        if not chunk:
                            break
                        handle.write(chunk)
            except (OSError, socket.timeout):
                return

        self.files.append(target)
        print()
        say("receive_got", name=target.name, who=address[0])

    @property
    def error(self):
        return self._error
