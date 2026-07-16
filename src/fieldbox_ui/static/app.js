// FieldBox dashboard logic — polls /api/status and drives the touch UI.
"use strict";

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;

async function api(path, method = "GET", body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

function toast(msg, isErr = false) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.toggle("err", isErr);
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3200);
}

function render(s) {
  const light = $("light");
  const connect = $("btn-connect");

  let cls = "offline", label = "Offline", reason = "";
  if (s.online) {
    cls = "online"; label = "Online"; connect.textContent = "Disconnect";
  } else if (s.backend_state === "NeedsLogin" || s.backend_state === "Starting") {
    cls = "connecting"; label = "Connecting…"; connect.textContent = "Disconnect";
  } else {
    cls = "offline"; label = "Offline"; connect.textContent = "Connect";
    reason = s.backend_state === "offline" ? "tailscaled not reachable" : `state: ${s.backend_state}`;
  }
  if (s.online && s.wan_source === "offline") { reason = "no internet on WAN or 4G"; }

  light.className = `light ${cls}`;
  $("state").textContent = label;
  $("reason").textContent = reason;

  const wanLabel = { wired: "Wired", "4g": "4G", offline: "—" }[s.wan_source] || s.wan_source;
  $("wan").textContent = `WAN: ${wanLabel}`;
  $("lan").textContent = s.lan_detected || "not detected";

  const adv = (s.advertised || []).join(", ") || "none";
  const approved = new Set(s.approved || []);
  const anyApproved = (s.advertised || []).some((r) => approved.has(r));
  $("routes").textContent = `${adv} ${adv === "none" ? "" : anyApproved ? "✓" : "(pending)"}`.trim();

  $("tailnet").textContent = s.tailnet || "—";
  $("ip").textContent = s.device_ip || "—";
}

async function poll() {
  try {
    render(await api("/api/status"));
  } catch (e) {
    render({ backend_state: "offline", online: false, wan_source: "offline", advertised: [], approved: [] });
  }
}

async function act(fn, okMsg) {
  try {
    render(await fn());
    if (okMsg) toast(okMsg);
  } catch (e) {
    toast(e.message, true);
  }
}

// --- wiring ---
$("btn-connect").onclick = () => {
  const online = $("state").textContent === "Online";
  act(() => api(online ? "/api/disconnect" : "/api/connect", "POST"), online ? "Disconnecting" : "Connecting");
};
$("btn-redetect").onclick = () => act(() => api("/api/redetect", "POST"), "Re-detected subnet");
$("btn-reboot").onclick = () => {
  if (confirm("Reboot the FieldBox?")) act(() => api("/api/reboot", "POST"), "Rebooting…");
};

// subnet modal
$("btn-subnet").onclick = () => {
  $("cidr").value = $("lan").textContent.includes("/") ? $("lan").textContent : "";
  $("modal").classList.remove("hidden");
  $("cidr").focus();
};
$("modal-cancel").onclick = () => $("modal").classList.add("hidden");
$("modal-ok").onclick = () => {
  const cidr = $("cidr").value.trim();
  $("modal").classList.add("hidden");
  act(() => api("/api/subnet", "POST", { cidr }), `Advertising ${cidr}`);
};

poll();
setInterval(poll, POLL_MS);
