"use strict";

const $ = (id) => document.getElementById(id);

let csrfToken = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setMessage(id, text, isError = false) {
  const node = $(id);
  if (!node) return;
  node.textContent = text || "";
  node.classList.toggle("is-error", Boolean(isError));
}

async function api(path, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  let body = options.body;
  if (body && typeof body !== "string") {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const response = await fetch(path, {
    method,
    headers,
    body,
    credentials: "same-origin",
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = new Error(
      payload && typeof payload.detail === "string"
        ? payload.detail
        : `Error ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

function formatDate(seconds) {
  if (!seconds) return "nunca";
  return new Date(Number(seconds) * 1000).toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function statusLabel(status) {
  return (
    {
      active: "activa",
      used: "agotada",
      expired: "vencida",
      revoked: "revocada",
    }[status] || status
  );
}

function showLogin() {
  const login = $("adminLoginPanel");
  const panel = $("adminPanel");
  if (login) login.hidden = false;
  if (panel) panel.hidden = true;
}

function showPanel() {
  const login = $("adminLoginPanel");
  const panel = $("adminPanel");
  if (login) login.hidden = true;
  if (panel) panel.hidden = false;
}

async function loadMe() {
  try {
    const payload = await api("/api/admin/me");
    if (payload.authenticated) {
      csrfToken = payload.csrfToken;
      showPanel();
      await loadInvites();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

function renderInvites(invites) {
  const table = $("inviteTable");
  const count = $("inviteCount");
  if (count) {
    count.textContent = `${invites.length} invitación${invites.length === 1 ? "" : "es"}`;
  }
  if (!table) return;
  if (!invites.length) {
    table.innerHTML = '<tr><td colspan="6" class="empty-state">Todavía no hay invitaciones.</td></tr>';
    return;
  }
  table.innerHTML = invites
    .map((invite) => {
      const code = String(invite.code || "");
      const codeCell = code
        ? `<code class="invite-code">${escapeHtml(code)}</code>`
        : '<span class="muted">creada antes del panel</span>';
      const canRevoke = invite.status === "active" || invite.status === "used";
      return `<tr>
        <td>${codeCell}</td>
        <td>${escapeHtml(invite.label || "—")}</td>
        <td>${Number(invite.uses) || 0}/${Number(invite.maxUses) || 0}</td>
        <td>${formatDate(invite.expiresAt)}</td>
        <td><span class="status-pill status-${escapeHtml(invite.status)}">${escapeHtml(statusLabel(invite.status))}</span></td>
        <td class="admin-actions">
          ${code ? `<button class="icon-btn" type="button" data-copy="${escapeHtml(code)}">COPIAR</button>` : ""}
          ${canRevoke ? `<button class="icon-btn icon-btn-danger" type="button" data-revoke="${escapeHtml(invite.codeHash)}">REVOCAR</button>` : ""}
        </td>
      </tr>`;
    })
    .join("");
}

async function loadInvites() {
  try {
    const payload = await api("/api/admin/invites");
    renderInvites(payload.invites || []);
  } catch (error) {
    if (error.status === 401) {
      showLogin();
    } else {
      setMessage("adminMessage", error.message || "No se pudieron cargar las invitaciones.", true);
    }
  }
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
    /* fall through */
  }
  const area = document.createElement("textarea");
  area.value = value;
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

function wireLogin() {
  const form = $("adminLoginForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("adminLoginMessage", "Entrando…");
    try {
      const payload = await api("/api/admin/login", {
        method: "POST",
        body: { password: $("adminPassword").value },
      });
      csrfToken = payload.csrfToken;
      form.reset();
      setMessage("adminLoginMessage", "");
      showPanel();
      await loadInvites();
    } catch (error) {
      setMessage("adminLoginMessage", error.message || "Clave incorrecta.", true);
    }
  });
}

function wireLogout() {
  const button = $("adminLogoutButton");
  if (!button) return;
  button.addEventListener("click", async () => {
    try {
      await api("/api/admin/logout", { method: "POST", body: {} });
    } catch {
      /* session may already be gone */
    }
    csrfToken = null;
    showLogin();
    setMessage("adminLoginMessage", "Sesión cerrada.");
  });
}

function wireCreate() {
  const form = $("adminCreateForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("adminMessage", "Creando invitación…");
    try {
      const payload = await api("/api/admin/invites", {
        method: "POST",
        body: {
          label: $("adminLabel").value.trim(),
          maxUses: Number($("adminMaxUses").value) || 1,
          days: Number($("adminDays").value) || 0,
        },
      });
      const code = payload.invite && payload.invite.code ? payload.invite.code : "";
      setMessage("adminMessage", code ? `Invitación creada: ${code}` : "Invitación creada.");
      form.reset();
      $("adminMaxUses").value = "10";
      $("adminDays").value = "30";
      await loadInvites();
    } catch (error) {
      setMessage("adminMessage", error.message || "No se pudo crear la invitación.", true);
    }
  });
}

function wireTable() {
  const table = $("inviteTable");
  if (!table) return;
  table.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const copy = button.getAttribute("data-copy");
    if (copy) {
      const copied = await copyText(copy);
      if (copied) {
        button.textContent = "COPIADO";
        window.setTimeout(() => {
          button.textContent = "COPIAR";
        }, 1500);
      }
      return;
    }
    const hash = button.getAttribute("data-revoke");
    if (!hash) return;
    if (!window.confirm("¿Revocar esta invitación? Los amigos que no la usaron no van a poder registrarse con ella.")) {
      return;
    }
    try {
      await api(`/api/admin/invites/${encodeURIComponent(hash)}/revoke`, {
        method: "POST",
        body: {},
      });
      setMessage("adminMessage", "Invitación revocada.");
      await loadInvites();
    } catch (error) {
      setMessage("adminMessage", error.message || "No se pudo revocar.", true);
    }
  });
}

function init() {
  wireLogin();
  wireLogout();
  wireCreate();
  wireTable();
  loadMe();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
