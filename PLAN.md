# Build plan: "FieldBox" — Pelicase Tailscale subnet router

## Context

Jim wants a rugged, self-contained field appliance (Raspberry Pi + touchscreen in a
Pelicase) whose only job is to be a **Tailscale subnet router** — dropped into a venue /
production network so the rest of the tailnet can reach devices on that LAN remotely.
It must be usable by a non-technical operator ("idiot-proof"): power on → it connects and
shows a green light, with a touchscreen for the one thing that actually varies (the subnet).

This is a from-scratch hardware + software build (no existing codebase). The routing itself
is a solved, robust problem; the effort is in the **idiot-proof touchscreen GUI**, the
**dual-WAN failover**, and the **Pelicase fabrication**.

### Decisions locked with Jim
- **Platform:** **Raspberry Pi 5 (8GB)** + a **USB 2.5GbE adapter** for the 2nd Ethernet port —
  chosen over CM4 + reRouter carrier purely for **availability** (Pi 5 is next-day at NL shops;
  CM4 has backorder lead times). Same OS/software/touchscreen; the 2nd NIC is USB instead of PCIe.
- **WAN:** 2× Ethernet + 4G, **auto-failover** (wired internet preferred, 4G takes over).
- **Tailnet join:** **pre-locked to Jim's tailnet** (tagged auth key + ACL autoApprovers), zero login.
- **Subnet:** **auto-detected** from the LAN port's DHCP lease, **changeable on the touchscreen**.
- **Power:** mains USB-C, **no battery**; rely on a **hardware watchdog + self-heal** ("if the site is down, we don't need to be online").
- **Interface:** self-contained **touchscreen** dashboard, no phone/keyboard needed.

### Difficulty verdict
Not hard. Working bench prototype in ~1 day; polished, cased, idiot-proof unit ~1 week part-time.
Most time goes to the GUI and the case, not the networking.

---

## Hardware / BOM (~€330–420 per unit)

Finalised part choices (see `docs/SHOPPING-LIST.md` for the full purchase list):

| Part | Choice | Notes |
|---|---|---|
| Compute | **Raspberry Pi 5 (8GB)** | Next-day at NL shops; boots from microSD/NVMe (much simpler than CM4 eMMC) |
| 2nd NIC | **USB 3.0 → 2.5GbE adapter** (Realtek RTL8156) | The WAN port. Well-supported on Pi OS Bookworm. Pinned `wan0`. |
| WAN #2 | **Huawei E3372h‑320 (HiLink)** + prepaid SIM | HiLink = DHCP ethernet iface, no ModemManager/PPP. Pinned `wwan0`, metric 700. **Disable SIM PIN.** |
| Display | **5" HDMI capacitive touchscreen, 800×480** (Waveshare 5inch HDMI LCD (H)) | Via micro‑HDMI → HDMI; touch over USB. (Pi 5 DSI + official Touch Display 2 is an alt.) |
| Power | Official **27W (5.1V/5A) USB‑C** PSU | Pi 5 needs 27W for full USB budget (NIC + modem + screen). Panel-mount USB‑C feedthrough. |
| Storage | **microSD 32GB (A2)** | Image with Raspberry Pi Imager — no rpiboot/eMMC dance |
| Cooling | **Official Pi 5 Active Cooler** + Gore/vent plug | Fan+heatsink in one; sealed Pelicase needs a pressure vent |
| Case | Pelicase 1150/1200 | Panel-mount: 2× RJ45 Cat6 feedthrough, USB‑C power, SMA bulkhead for 4G antenna |

Second-unit build is flash-and-go from a golden image.

---

## Network architecture

Stable interface names via `systemd .link` files (match by MAC/PCI path → pin names), because
the two NICs can otherwise enumerate inconsistently:

- `lan0` — **Pi 5 built-in GbE** → production network we subnet-route → DHCP client, **never a default route** (`ipv4.never-default=yes`)
- `wan0` — **USB 2.5GbE adapter** → wired WAN → DHCP client, **default route metric 100** (preferred)
- `wwan0` — 4G HiLink modem (E3372h) → DHCP client, **default route metric 700** (backup), marked metered

**Failover:** run **NetworkManager** (Bookworm default) with per-connection route metrics + its
connectivity check. Live wired internet wins; if `wan0` loses connectivity NM demotes it and 4G's
default route takes over automatically; re-plugging fails back. `lan0` never carries internet.

**Subnet routing (the core):**
- `net.ipv4.ip_forward=1` + `net.ipv6.conf.all.forwarding=1` in `/etc/sysctl.d/`.
- `tailscale up --advertise-routes=<lan0 CIDR> --advertise-tags=tag:subnetrouter --auth-key=<key> --hostname=fieldbox-NN`
- **SNAT/masquerade is Tailscale's default and stays ON** — this is the key idiot-proof win: devices
  on the production LAN need **zero** gateway/route changes; return traffic looks like it comes from `lan0`.
- **ACL autoApprovers** pre-approve RFC1918 for the tag, so any detected subnet is approved with **no admin click**:
  ```jsonc
  "tagOwners":     { "tag:subnetrouter": ["autogroup:admin"] },
  "autoApprovers": { "routes": {
      "10.0.0.0/8":     ["tag:subnetrouter"],
      "172.16.0.0/12":  ["tag:subnetrouter"],
      "192.168.0.0/16": ["tag:subnetrouter"] } }
  ```
- **Auth key:** reusable + pre-authorized + tagged, stored in the image; **disable key expiry** on the
  device in the admin console so it never silently drops off the tailnet.

**Subnet auto-detect + on-screen change:**
- Read `ip -j addr show lan0` → compute the CIDR from the DHCP lease = "detected subnet".
- GUI: shows detected CIDR; buttons **[Use detected] / [Change (manual CIDR)] / [Re-detect]**.
- Apply with `tailscale set --advertise-routes=<cidr>` (no full re-up); autoApprovers covers it instantly.

---

## Software / artifacts to create

1. **`fieldbox-ui`** — local touch web app (Python **FastAPI** + one touch-friendly HTML/JS page),
   shown fullscreen via **`cage` (Wayland kiosk) + Chromium** at `localhost`. Web = easy to make
   attractive, touch-friendly, and restyleable.
   - Backend shells to `tailscale status --json`, `tailscale ip`, `tailscale set`, `ip -j`, and (for
     4G signal) the dongle's status page or `mmcli`. Runs as a systemd service; page polls ~2s.
   - Dashboard: big **ONLINE / CONNECTING / OFFLINE** light (+ reason); **WAN source** in use
     (Wired / 4G + signal bars); **detected vs advertised subnet + approved?**; tailnet name + this
     node's Tailscale IP. Buttons: **Connect/Disconnect, Change subnet, Re-detect, Details/logs, Reboot**.
2. **`10-wan.link` / `20-lan.link` / `30-wwan.link`** + NetworkManager connection profiles (route metrics wan0=100 / wwan0=700, `lan0` never-default).
3. **`/etc/sysctl.d/99-forwarding.conf`** — IP forwarding.
4. **`fieldbox-firstboot.service`** — one-shot `tailscale up` with stored auth key on first boot.
5. **`fieldbox-health.service` + timer** — self-heal: verify tailscaled running, WAN default route
   reachable, backend state = `Running`; on sustained failure restart tailscaled / renew DHCP →
   last-resort reboot.
6. **Hardware watchdog** — `/etc/systemd/system.conf`: `RuntimeWatchdogSec=15`, `RebootWatchdogSec=2min`
   (BCM2711 wdt) → auto-reboot on hard hang. This is Jim's "auto-reboot" requirement.
7. **`setup.sh` + golden image** (pi-gen or scripted) so unit #2 is flash-and-go.

---

## Case fabrication

- Lid: cutout + gasket for the touchscreen.
- Rear/side panel: 2× RJ45 feedthrough couplers (label **WAN** / **LAN**), panel-mount USB‑C power,
  SMA bulkhead(s) for the 4G antenna (external whip for signal).
- Internal: standoffs for carrier + screen, heatsink + fan, cable management, Gore vent for pressure/airflow.
- Colour-code / label ports so the operator can't mix up WAN and LAN.

---

## Verification / testing (bench first, then in the case)

1. **Boot & naming:** flash image, boot on a desk HDMI screen; `ip -br link` shows `wan0`, `lan0`, 4G iface.
2. **WAN failover:** wired internet plugged → `ip route` default via `wan0`, `tailscale netcheck` OK.
   Unplug wired → within a few s 4G default route takes over, tailnet stays up. Re-plug → fails back.
3. **Subnet routing:** connect `lan0` to a test net (e.g. `192.168.50.0/24`, device at `.10`). From a
   laptop elsewhere on the tailnet: `tailscale status` shows `192.168.50.0/24` **approved** (autoApprovers);
   `ping 192.168.50.10` + open its web UI works with **no change on the .10 device** (proves masquerade).
4. **Subnet change:** move `lan0` to a different subnet → **Re-detect** on screen → new CIDR advertised,
   auto-approved, reachable.
5. **Watchdog / self-heal:** `kill -9 tailscaled` → health service restarts it; stop feeding the hw
   watchdog → board auto-reboots and returns to **ONLINE** unattended.
6. **Idiot test:** cold power-cycle → within ~60–90s the screen shows **ONLINE + the detected subnet**
   with zero interaction.

---

## Buy-early checks (before ordering)
- **USB 2.5GbE adapter:** pick a **Realtek RTL8156**-based one (native Pi OS Bookworm support).
- **USB power budget:** with the 27W PSU the Pi 5 gives 5V/5A; the touchscreen + NIC + modem fit,
  but a small **powered USB hub** is cheap insurance if the screen browns out.
- **4G firmware:** confirm the E3372h is the **HiLink** (USB-ethernet) firmware, not the stick/PPP one;
  **disable the SIM PIN** before first insert. Carrier CGNAT is fine for Tailscale (DERP/NAT traversal).
- **Auth key expiry:** disable device key expiry in the admin console so it never drops off.
- **Heat:** sealed Pelicase → heatsink + fan + Gore vent.
- **Security:** the image contains a tailnet auth key — keep images controlled; consider tailnet lock.
