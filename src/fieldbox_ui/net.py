"""Network interface + subnet detection helpers (Linux / iproute2).

Every helper degrades gracefully (returns ``None`` / safe defaults) when
iproute2 output is unavailable — e.g. when running the dev server on macOS —
so the dashboard can still be previewed off-device.
"""

from __future__ import annotations

import ipaddress
import json
import subprocess
from typing import Optional

# Interface names are pinned by the systemd .link files (see network/).
LAN_IFACE = "lan0"    # the production network we subnet-route
WAN_IFACE = "wan0"    # the wired internet port
WWAN_IFACE = "wwan0"  # the 4G HiLink modem (Huawei E3372h), route metric 700


def _run(cmd: list[str], timeout: int = 5) -> Optional[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def interface_cidr(iface: str = LAN_IFACE) -> Optional[str]:
    """CIDR of the first global IPv4 address on ``iface`` (e.g. ``192.168.10.0/24``)."""
    raw = _run(["ip", "-j", "-4", "addr", "show", iface])
    if not raw:
        return None
    try:
        links = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for link in links:
        for addr in link.get("addr_info", []):
            if addr.get("family") == "inet" and addr.get("scope") == "global":
                ip, prefix = addr.get("local"), addr.get("prefixlen")
                if ip and prefix is not None:
                    net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
                    return str(net)
    return None


def default_route_iface() -> Optional[str]:
    """Interface carrying the current default route (i.e. the active WAN)."""
    raw = _run(["ip", "-j", "route", "show", "default"])
    if not raw:
        return None
    try:
        routes = [r for r in json.loads(raw) if r.get("dev")]
    except json.JSONDecodeError:
        return None
    if not routes:
        return None
    routes.sort(key=lambda r: r.get("metric", 0))  # lowest metric wins
    return routes[0]["dev"]


def wan_source() -> str:
    """Human label for where internet is currently coming from."""
    dev = default_route_iface()
    if dev is None:
        return "offline"
    if dev == WAN_IFACE:
        return "wired"
    if dev == WWAN_IFACE or dev.startswith(("wwan", "usb", "ppp")):
        return "4g"
    return dev


def is_valid_cidr(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except (ValueError, TypeError):
        return False
