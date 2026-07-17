"""Thin wrapper around the ``tailscale`` CLI.

Every call degrades gracefully (returns ``None`` / empty) when tailscale is not
installed or not reachable, so the dashboard renders an OFFLINE state instead of
crashing (handy for previewing on a dev machine).
"""

from __future__ import annotations

import json
import subprocess
from typing import Optional


def _run(args: list[str], timeout: int = 10) -> Optional[str]:
    try:
        out = subprocess.run(
            ["tailscale", *args], capture_output=True, text=True, timeout=timeout
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def status() -> Optional[dict]:
    raw = _run(["status", "--json"])
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def prefs() -> Optional[dict]:
    raw = _run(["debug", "prefs"])
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def advertised_routes() -> list[str]:
    return list((prefs() or {}).get("AdvertiseRoutes") or [])


def approved_routes(st: Optional[dict] = None) -> list[str]:
    """Subnet routes this node is approved for and actively serving.

    Reads ``Self.PrimaryRoutes`` from ``tailscale status --json`` — the routes
    the node is the primary router for, i.e. advertised AND approved. If a route
    is advertised but absent here, the UI shows it as "pending".
    """
    st = st if st is not None else status()
    self_ = (st or {}).get("Self") or {}
    return list(self_.get("PrimaryRoutes") or [])


def set_advertised_routes(cidr: str) -> bool:
    """Change the advertised subnet without a full re-up. autoApprovers auto-approves it."""
    return _run(["set", f"--advertise-routes={cidr}"]) is not None


def up(extra: Optional[list[str]] = None) -> bool:
    return _run(["up", "--reset", *(extra or [])], timeout=30) is not None


def down() -> bool:
    return _run(["down"]) is not None
