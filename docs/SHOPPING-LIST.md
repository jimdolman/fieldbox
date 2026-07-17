# FieldBox — Shopping list (one unit)

Everything needed to build one FieldBox. Prices are ballpark EUR, ex. shipping and SIM plan.
Check the two ⚠️ items before ordering (see notes at the bottom).

## Core electronics
- [ ] **Raspberry Pi CM4104032** — CM4, 4 GB RAM, 32 GB eMMC, Wi-Fi/BT — ×1 — ~€75
- [ ] **Seeed Dual Gigabit Ethernet Carrier Board for CM4** (reRouter CM4001) — ×1 — ~€60
- [ ] **Huawei E3372h-320** USB 4G modem (⚠️ **HiLink** firmware) — ×1 — ~€35
- [ ] **Prepaid data SIM** (mini/2FF, fits the E3372h) — ×1 — plan cost
- [ ] **5″ HDMI capacitive touchscreen, 800×480** (Waveshare 5inch HDMI LCD (H)) — ×1 — ~€45

## Power
- [ ] **Official Raspberry Pi 5 V / 3 A USB-C PSU** — ×1 — ~€12
- [ ] **Panel-mount USB-C feedthrough** coupler — ×1 — ~€8

## Networking & RF
- [ ] **RJ45 Cat6 feedthrough couplers**, panel mount (WAN + LAN) — ×2 — ~€10
- [ ] **Short Cat6 patch leads**, ~0.25 m (carrier → panel couplers) — ×2 — ~€6
- [ ] **TS-9 → SMA pigtail** (E3372h antenna port → panel) — ×1 — ~€6
- [ ] **SMA 4G whip antenna** (external) — ×1 — ~€8

## Display cabling
- [ ] **micro-HDMI (M) → HDMI (M) cable**, ~0.3 m (carrier → screen) — ×1 — ~€6
- [ ] **USB-A → micro-USB cable**, short (touch signal) — ×1 — ~€3

## Cooling
- [ ] **CM4 heatsink** — ×1 — ~€5
- [ ] **30 mm 5 V fan** — ×1 — ~€4
- [ ] **Gore / pressure-equalization vent** plug — ×1 — ~€8

## Case & mechanical
- [ ] **Pelicase 1150 or 1200** — ×1 — ~€55
- [ ] **M2.5 brass standoff + screw kit** — ×1 — ~€8
- [ ] **Cable ties + adhesive mounts** (pack) — ×1 — ~€4
- [ ] **Connector panel** — ABS/aluminium blank or 3D-printed — ×1 — ~€5
- [ ] **Thermal pads / paste** — ×1 — ~€3

## Flashing & bring-up (you may already own these)
- [ ] **USB-A ↔ USB-C data cable** (for `rpiboot` eMMC flashing) — ×1 — ~€4
- No microSD needed — the CM4 boots from its onboard eMMC.
- A host PC with `rpiboot` to flash the eMMC (one-time, per unit).

---

**Estimated total: ~€370 / unit** (ex. shipping + SIM plan). Second units drop the one-time
host-PC/cable cost.

### ⚠️ Confirm before ordering
1. **E3372h firmware** must be **HiLink** (presents as a USB-Ethernet interface with its own DHCP) —
   *not* the "Stick"/PPP variant. The `-320` is normally HiLink; verify with the seller.
2. **Carrier display output** — the reRouter exposes **micro-HDMI** (why we picked an HDMI screen).
   Confirm the revision you receive matches before buying the cable/screen.
3. **Disable the SIM PIN** (in a phone) before first insert, and **disable Tailscale key expiry**
   for the device in the admin console.
