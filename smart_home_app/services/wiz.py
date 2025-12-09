"""WiZ light helpers."""

from __future__ import annotations

import json
import socket
from typing import List, Optional

from ..core.constants import WIZ_PORT


class WiZLightClient:
    """Client responsible for scanning and sending commands to WiZ devices."""

    def __init__(self, port: int = WIZ_PORT) -> None:
        self.port = port

    def send_request(self, ip: str | None, payload: dict, timeout: float = 1.0) -> dict | None:
        if not ip:
            return None

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(json.dumps(payload).encode(), (ip, self.port))
            data, _ = sock.recvfrom(4096)
            return json.loads(data.decode())
        except OSError:
            return None
        finally:
            sock.close()

    def scan(self, broadcast_timeout: float = 1.5) -> list[str]:
        """Broadcast for WiZ lights and return the list of IPs found."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(broadcast_timeout)
        found: list[str] = []
        try:
            msg = json.dumps({"method": "getPilot", "params": {}}).encode()
            sock.sendto(msg, ("255.255.255.255", self.port))
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    if addr[0] not in found:
                        found.append(addr[0])
                except OSError:
                    break
        finally:
            sock.close()
        return found

    def get_state(self, ip: str) -> dict | None:
        return self.send_request(ip, {"method": "getPilot", "params": {}})

    def set_power(self, ip: str, state: bool) -> None:
        self.send_request(ip, {"id": 1, "method": "setState", "params": {"state": state}})

    def set_pilot(self, ip: str, temp: int, dimming: int) -> None:
        self.send_request(
            ip,
            {"id": 1, "method": "setPilot", "params": {"temp": temp, "dimming": dimming}},
        )


__all__ = ["WiZLightClient"]

