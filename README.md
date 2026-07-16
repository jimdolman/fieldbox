# FieldBox

A rugged, self-contained **Tailscale subnet router** in a Pelicase — drop it into a
venue / production network and the rest of your tailnet can reach devices on that LAN.
Built to be operated by a non-technical person: power on → green light → done, with a
touchscreen for the one thing that varies (the subnet).

See **[PLAN.md](PLAN.md)** for the full hardware BOM, network design, and rationale.

## What it does

- **2× Ethernet + 4G with auto-failover** — wired internet preferred, 4G prepaid modem takes over.
- **Pre-locked to your tailnet** (tagged auth key + ACL autoApprovers) — zero login.
- **Auto-detects the subnet** on the LAN port and advertises it; changeable on the touchscreen.
- **Self-healing** — hardware watchdog + a health timer that restarts/reboots on local faults only.
- **Touch dashboard** — big ONLINE/OFFLINE light, WAN source, subnet + approval, big buttons.

## Layout

```
src/fieldbox_ui/     FastAPI backend + touch web dashboard (static/)
systemd/             services: ui, kiosk (cage+chromium), firstboot, health timer
network/             10-wan.link / 20-lan.link  (pin interface names by MAC)
config/              99-forwarding.conf (IP forward), watchdog.conf (hw watchdog)
tailscale/           acl.hujson  (tagOwners + autoApprovers to paste into your ACLs)
scripts/             setup.sh (provision the Pi), firstboot.sh, health-check.sh
```

## Dev preview (on your Mac / any laptop)

The backend degrades gracefully when `tailscale`/`ip` aren't present, so you can preview the
UI off-device — it just shows an OFFLINE state.

```bash
cd ~/projects/fieldbox
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn fieldbox_ui.app:app --reload --host 127.0.0.1 --port 8080 --app-dir src
# open http://127.0.0.1:8080
```

## Deploy to the Pi (outline)

1. Flash Raspberry Pi OS (Bookworm) to the CM4; enable SSH.
2. `git clone` this repo onto the Pi and run `scripts/setup.sh` (review it first — it's a scaffold).
3. Edit the MACs in `/etc/systemd/network/*.link` (find them with `ip -br link`), reboot.
4. Drop a **tagged, reusable** Tailscale auth key into `/var/lib/fieldbox/authkey` (`chmod 600`).
5. Paste the blocks from `tailscale/acl.hujson` into your tailnet's Access Controls.
6. In the Tailscale admin console, **disable key expiry** for the device so it never drops off.

## Status

Scaffold / work-in-progress — being refined via Ultraplan. Sections marked `TODO` in the
code (e.g. the exact "approved routes" field name) need confirming against the pinned
Tailscale version and the chosen carrier board's display connector (DSI vs micro-HDMI).
