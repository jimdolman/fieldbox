#!/usr/bin/env bash
# FieldBox provisioning — run once on a fresh Raspberry Pi OS (Bookworm) image.
# Idempotent-ish; safe to re-run. Review before use — this is a scaffold.
set -euo pipefail

REPO_DST=/opt/fieldbox
KIOSK_USER=fieldbox

echo "==> Installing packages"
sudo apt-get update
sudo apt-get install -y \
  python3-venv python3-pip \
  network-manager \
  cage chromium-browser \
  curl jq

echo "==> Installing Tailscale"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

echo "==> Copying repo to ${REPO_DST}"
sudo mkdir -p "${REPO_DST}"
sudo cp -r "$(cd "$(dirname "$0")/.." && pwd)/." "${REPO_DST}/"

echo "==> Python venv"
sudo python3 -m venv "${REPO_DST}/.venv"
sudo "${REPO_DST}/.venv/bin/pip" install -r "${REPO_DST}/requirements.txt"

echo "==> Kiosk user"
id -u "${KIOSK_USER}" >/dev/null 2>&1 || sudo useradd -m -s /bin/bash "${KIOSK_USER}"

echo "==> System config (forwarding, watchdog)"
sudo cp "${REPO_DST}/config/99-forwarding.conf" /etc/sysctl.d/
sudo sysctl --system
sudo mkdir -p /etc/systemd/system.conf.d
sudo cp "${REPO_DST}/config/watchdog.conf" /etc/systemd/system.conf.d/

echo "==> Interface pinning (.link) — EDIT MACs in network/*.link first!"
sudo cp "${REPO_DST}/network/10-wan.link" "${REPO_DST}/network/20-lan.link" /etc/systemd/network/

echo "==> NetworkManager profiles (wired WAN preferred, LAN never-default)"
# wan0: preferred internet (low metric). 4G connection should be metric 700.
sudo nmcli connection add type ethernet ifname wan0 con-name wan0 \
  ipv4.route-metric 100 ipv6.route-metric 100 2>/dev/null || true
# lan0: DHCP for an address to route from, but NEVER a default route.
sudo nmcli connection add type ethernet ifname lan0 con-name lan0 \
  ipv4.never-default yes ipv6.never-default yes 2>/dev/null || true
# NOTE: the 4G HiLink dongle usually appears as its own DHCP iface (usb0/eth1);
#       add it as a connection with ipv4.route-metric 700 once you know its name.

echo "==> systemd units"
sudo cp "${REPO_DST}"/systemd/*.service "${REPO_DST}"/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fieldbox-ui.service fieldbox-kiosk.service \
  fieldbox-firstboot.service fieldbox-health.timer

echo "==> Allow the UI to reboot without a password"
echo "${KIOSK_USER} ALL=(root) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/fieldbox-reboot >/dev/null

echo
echo "Done. Remaining manual steps:"
echo "  1. Put a tagged, reusable auth key in /var/lib/fieldbox/authkey (chmod 600)."
echo "  2. Edit MACs in /etc/systemd/network/*.link, then reboot."
echo "  3. Paste tailscale/acl.hujson blocks into your tailnet ACLs."
echo "  4. In the admin console, disable key expiry for this device."
