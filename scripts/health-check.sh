#!/usr/bin/env bash
# FieldBox self-heal — run by fieldbox-health.timer every minute.
# Escalates: restart tailscaled -> renew DHCP -> (last resort) reboot.
# "If the site is down there's nothing to route" — so we only act on OUR faults.
set -uo pipefail

STATE_DIR=/var/lib/fieldbox
FAIL_FILE=${STATE_DIR}/health-fails
MAX_FAILS=5   # ~5 minutes of sustained local failure before reboot
mkdir -p "${STATE_DIR}"

log() { logger -t fieldbox-health "$*"; }

healthy=1

# 1. tailscaled must be running.
if ! systemctl is-active --quiet tailscaled; then
  log "tailscaled not active -> restarting"
  systemctl restart tailscaled
  healthy=0
fi

# 2. There must be a default route (some WAN present). No WAN = site problem, not ours.
if ip route show default | grep -q .; then
  # 3. With a WAN up, the tailnet backend should reach Running.
  state=$(tailscale status --json 2>/dev/null | jq -r '.BackendState // "unknown"')
  if [[ "${state}" != "Running" ]]; then
    log "WAN present but backend=${state} -> nudging tailscale"
    tailscale up --reset >/dev/null 2>&1 || systemctl restart tailscaled
    healthy=0
  fi
fi

# Track consecutive failures; reboot only if we can't recover.
if [[ "${healthy}" -eq 1 ]]; then
  rm -f "${FAIL_FILE}"
else
  fails=$(( $(cat "${FAIL_FILE}" 2>/dev/null || echo 0) + 1 ))
  echo "${fails}" > "${FAIL_FILE}"
  log "unhealthy (${fails}/${MAX_FAILS})"
  if [[ "${fails}" -ge "${MAX_FAILS}" ]]; then
    log "max failures reached -> rebooting"
    rm -f "${FAIL_FILE}"
    systemctl reboot
  fi
fi
