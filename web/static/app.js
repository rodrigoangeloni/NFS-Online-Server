"use strict";

const REFRESH_MS = 10000;

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function gameLabel(game) {
  const labels = {
    u2: "Underground 2",
    mw: "Most Wanted",
    all: "U2 + MW",
    carbon: "Carbon",
  };
  return labels[String(game || "").toLowerCase()] || String(game || "NFS");
}

function formatTime(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "—";
  return new Date(value * 1000).toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value;
}

async function fetchJson(path) {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

function renderStatus(live) {
  const rooms = Array.isArray(live.rooms) ? live.rooms : [];
  const players = Array.isArray(live.players) ? live.players : [];
  const total = Number(live.totalPlayers) || players.length;
  const connected = Boolean(live.connected);

  setText("totalPlayers", String(total));
  setText("roomCount", String(rooms.length));
  setText("playerCount", String(total));
  setText("updatedAt", formatTime(live.updatedAt));

  const chip = $("connectionChip");
  if (chip) {
    chip.textContent = connected ? "en línea" : "sin salas";
    chip.className = `chip ${connected ? "chip-online" : "chip-offline"}`;
  }

  const grid = $("serverGrid");
  if (grid) {
    grid.innerHTML = `
      <article class="status-card">
        <div class="status-card-head"><span>Servidor</span><span class="chip ${connected ? "chip-online" : "chip-offline"}">${connected ? "activo" : "en espera"}</span></div>
        <strong class="status-value">${connected ? "ONLINE" : "STANDBY"}</strong>
      </article>
      <article class="status-card">
        <div class="status-card-head"><span>Salas</span><span>U2 / MW</span></div>
        <strong class="status-value">${rooms.length}</strong>
      </article>
      <article class="status-card">
        <div class="status-card-head"><span>Jugadores</span><span>ahora</span></div>
        <strong class="status-value">${total}</strong>
      </article>
      <article class="status-card">
        <div class="status-card-head"><span>Última señal</span><span>local</span></div>
        <strong class="status-value">${formatTime(live.updatedAt)}</strong>
      </article>`;
  }

  const roomGrid = $("roomGrid");
  if (roomGrid) {
    if (!rooms.length) {
      roomGrid.innerHTML = '<div class="empty-state">No hay salas abiertas. Creá una desde el juego y va a aparecer acá.</div>';
    } else {
      roomGrid.innerHTML = rooms
        .map((room) => {
          const personas = Array.isArray(room.personas) ? room.personas : [];
          const chips = personas.length
            ? `<div class="room-personas">${personas.map((name) => `<span class="player-chip">${escapeHtml(name)}</span>`).join("")}</div>`
            : "";
          return `<article class="room-card">
            <span class="room-game">${escapeHtml(gameLabel(room.game))}</span>
            <h3 class="room-name">${escapeHtml(room.name || "Sala sin nombre")}</h3>
            <p class="room-meta">${Number(room.players) || personas.length}/${Number(room.capacity) || "?"} jugadores · ${escapeHtml(room.state || "OPEN")}</p>
            ${chips}
          </article>`;
        })
        .join("");
    }
  }

  const list = $("playerList");
  if (list) {
    list.innerHTML = players.length
      ? players.map((name) => `<span class="player-chip">${escapeHtml(name)}</span>`).join("")
      : "";
  }
}

function renderDownloads(payload) {
  setText("serverAddress", payload.serverAddress || "—");
  const downloads = Array.isArray(payload.downloads) ? payload.downloads : [];
  setText(
    "downloadSummary",
    downloads.length
      ? `${downloads.length} paquete${downloads.length === 1 ? "" : "s"} listo${downloads.length === 1 ? "" : "s"}`
      : "Todavía no hay paquetes configurados"
  );

  const grid = $("downloadGrid");
  if (!grid) return;
  if (!downloads.length) {
    grid.innerHTML = '<div class="empty-state">El administrador todavía no publicó paquetes. Volvé a intentar en un rato.</div>';
    return;
  }

  grid.innerHTML = downloads
    .map((item) => {
      const available = Boolean(item.available);
      const action = available
        ? `<a class="btn btn-primary btn-small" href="${escapeHtml(item.downloadUrl || `/downloads/${item.id}`)}">Descargar</a>`
        : '<span class="download-unavailable">No disponible</span>';
      return `<article class="download-card">
        <div class="download-head">
          <h3 class="download-title">${escapeHtml(item.title || item.id)}</h3>
          <span class="download-game">${escapeHtml(gameLabel(item.game))}</span>
        </div>
        <p class="download-description">${escapeHtml(item.description || "")}</p>
        <div class="download-meta">
          <span>Versión <strong>${escapeHtml(item.version || "—")}</strong></span>
          <span>Tamaño <strong>${escapeHtml(item.sizeLabel || "—")}</strong></span>
          ${item.recommended ? "<span><strong>Recomendado</strong></span>" : ""}
        </div>
        <code class="download-hash">SHA-256 ${escapeHtml(String(item.sha256 || "").slice(0, 24) || "—")}…</code>
        <div class="download-action">
          <span class="download-size">${escapeHtml(item.filename || "")}</span>
          ${action}
        </div>
      </article>`;
    })
    .join("");
}

async function copyText(text) {
  const value = String(text || "");
  if (!value) return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    /* fall through to the legacy path */
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  }
  area.remove();
  return copied;
}

async function refreshLive() {
  const warning = $("connectionWarning");
  try {
    const live = await fetchJson("/api/live");
    renderStatus(live);
    if (warning) warning.hidden = true;
  } catch {
    if (warning) warning.hidden = false;
  }
}

async function refreshConnect() {
  try {
    const payload = await fetchJson("/api/connect");
    renderDownloads(payload);
  } catch {
    setText("downloadSummary", "No se pudieron cargar las descargas");
  }
}

function wireCopyButton() {
  const button = $("copyServerAddress");
  if (!button) return;
  button.addEventListener("click", async () => {
    const address = $("serverAddress")?.textContent || "";
    const copied = await copyText(address);
    const original = button.textContent;
    button.textContent = copied ? "COPIADO" : "ERROR";
    window.setTimeout(() => {
      button.textContent = original;
    }, 1600);
  });
}

async function refreshAll() {
  await Promise.allSettled([refreshLive(), refreshConnect()]);
}

function init() {
  wireCopyButton();
  refreshAll();
  window.setInterval(refreshAll, REFRESH_MS);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
