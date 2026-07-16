#!/usr/bin/env bash
# One-shot Tailscale bring-up on first boot. Pre-locked to your tailnet via a
# tagged, reusable auth key. Advertises the subnet auto-detected on lan0.
set -euo pipefail

AUTHKEY_FILE=/var/lib/fieldbox/authkey
STATE_DIR=/var/lib/fieldbox
LAN_IFACE=lan0

mkdir -p "${STATE_DIR}"

if [[ ! -s "${AUTHKEY_FILE}" ]]; then
  echo "No auth key at ${AUTHKEY_FILE}; skipping (device stays unconfigured)." >&2
  exit 0
fi

# Wait briefly for lan0 to get a DHCP lease so we can detect its subnet.
CIDR=""
for _ in $(seq 1 15); do
  CIDR=$(ip -j -4 addr show "${LAN_IFACE}" 2>/dev/null \
    | jq -r '.[0].addr_info[]? | select(.scope=="global") | "\(.local)/\(.prefixlen)"' \
    | head -n1 || true)
  [[ -n "${CIDR}" ]] && break
  sleep 2
done

# Normalise host address -> network address (e.g. 192.168.10.23/24 -> 192.168.10.0/24)
ROUTE_ARG=""
if [[ -n "${CIDR}" ]]; then
  NET=$(python3 -c "import ipaddress,sys; print(ipaddress.ip_network(sys.argv[1], strict=False))" "${CIDR}")
  ROUTE_ARG="--advertise-routes=${NET}"
fi

tailscale up \
  --auth-key "$(cat "${AUTHKEY_FILE}")" \
  --advertise-tags=tag:subnetrouter \
  --hostname "fieldbox-$(tr -dc a-f0-9 </dev/urandom | head -c4)" \
  ${ROUTE_ARG} \
  --accept-routes=false

touch "${STATE_DIR}/provisioned"
