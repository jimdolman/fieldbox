"""FieldBox backend: serves the touch dashboard and a small JSON API.

Run locally (dev, off-device):
    uvicorn fieldbox_ui.app:app --reload --host 127.0.0.1 --port 8080

On the Pi it's launched by systemd (see systemd/fieldbox-ui.service) and shown
fullscreen by the kiosk (systemd/fieldbox-kiosk.service).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import net, tailscale

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="FieldBox", version="0.1.0")


class SubnetBody(BaseModel):
    cidr: str


def build_status() -> dict:
    st = tailscale.status()
    self_ = (st or {}).get("Self") or {}
    backend = (st or {}).get("BackendState") or "offline"
    tailnet = ((st or {}).get("CurrentTailnet") or {}).get("Name") or (st or {}).get(
        "MagicDNSSuffix"
    )
    ips = self_.get("TailscaleIPs") or (st or {}).get("TailscaleIPs") or []

    return {
        "backend_state": backend,             # Running / Stopped / NeedsLogin / offline
        "online": backend == "Running",
        "tailnet": tailnet,
        "device_ip": ips[0] if ips else None,
        "hostname": self_.get("HostName"),
        "wan_source": net.wan_source(),        # wired / 4g / offline
        "lan_detected": net.interface_cidr(net.LAN_IFACE),
        "advertised": tailscale.advertised_routes(),
        "approved": tailscale.approved_routes(st),
    }


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/api/status")
def api_status() -> dict:
    return build_status()


@app.post("/api/subnet")
def api_set_subnet(body: SubnetBody) -> dict:
    if not net.is_valid_cidr(body.cidr):
        raise HTTPException(status_code=400, detail=f"Not a valid CIDR: {body.cidr!r}")
    if not tailscale.set_advertised_routes(body.cidr):
        raise HTTPException(status_code=500, detail="tailscale set failed")
    return build_status()


@app.post("/api/redetect")
def api_redetect() -> dict:
    cidr = net.interface_cidr(net.LAN_IFACE)
    if not cidr:
        raise HTTPException(
            status_code=409,
            detail=f"No IPv4 address on {net.LAN_IFACE} yet — is the LAN cable plugged in?",
        )
    if not tailscale.set_advertised_routes(cidr):
        raise HTTPException(status_code=500, detail="tailscale set failed")
    return build_status()


@app.post("/api/connect")
def api_connect() -> dict:
    if not tailscale.up():
        raise HTTPException(status_code=500, detail="tailscale up failed")
    return build_status()


@app.post("/api/disconnect")
def api_disconnect() -> dict:
    if not tailscale.down():
        raise HTTPException(status_code=500, detail="tailscale down failed")
    return build_status()


@app.post("/api/reboot")
def api_reboot() -> dict:
    # Guarded: only works where the service user may reboot (see sudoers note in README).
    try:
        subprocess.Popen(["sudo", "-n", "/sbin/reboot"])
    except OSError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
    return {"rebooting": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
