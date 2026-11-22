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
      await loadAccounts();
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

function renderAccounts(accounts) {
  const table = $("accountTable");
  const count = $("accountCount");
  if (count) {
    count.textContent = `${accounts.length} cuenta${accounts.length === 1 ? "" : "s"}`;
  }
  if (!table) return;
  if (!accounts.length) {
    table.innerHTML = '<tr><td colspan="5" class="empty-state">Todavía no hay cuentas.</td></tr>';
    return;
  }
  table.innerHTML = accounts
    .map((account) => {
      const state = account.banned ? "baneada" : account.enabled ? "activa" : "deshabilitada";
      const statusClass = account.banned
        ? "status-revoked"
        : account.enabled
          ? "status-active"
          : "status-used";
      return `<tr>
        <td><code class="invite-code">${escapeHtml(account.accountName)}</code></td>
        <td>${escapeHtml((account.personas || []).join(", ") || "—")}</td>
        <td>${escapeHtml(account.email || "—")}</td>
        <td><span class="status-pill ${statusClass}">${escapeHtml(state)}</span></td>
        <td class="admin-actions">
          <button class="icon-btn" type="button" data-reset="${escapeHtml(account.accountName)}">RESET</button>
          <button class="icon-btn${account.banned ? "" : " icon-btn-danger"}" type="button" data-ban="${escapeHtml(account.accountName)}" data-banned="${account.banned ? "1" : "0"}">${account.banned ? "DESBANEAR" : "BAN"}</button>
        </td>
      </tr>`;
    })
    .join("");
}

async function loadAccounts() {
  try {
    const payload = await api("/api/admin/accounts");
    renderAccounts(payload.accounts || []);
  } catch (error) {
    if (error.status === 401) {
      showLogin();
    } else {
      setMessage("adminAccountsMessage", error.message || "No se pudieron cargar las cuentas.", true);
    }
  }
}

function wireAccounts() {
  const table = $("accountTable");
  if (!table) return;
  table.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;

    const banName = button.getAttribute("data-ban");
    if (banName) {
      const isBanned = button.getAttribute("data-banned") === "1";
      const question = isBanned
        ? `¿Desbanear a ${banName}? Va a poder volver a entrar.`
        : `¿Banear a ${banName}? Se lo desconecta ahora y no va a poder volver a entrar.`;
      if (!window.confirm(question)) return;
      try {
        await api(
          `/api/admin/accounts/${encodeURIComponent(banName)}/${isBanned ? "unban" : "ban"}`,
          { method: "POST", body: {} },
        );
        setMessage(
          "adminAccountsMessage",
          isBanned ? `${banName} fue desbaneada.` : `${banName} fue baneada.`,
        );
        await loadAccounts();
      } catch (error) {
        setMessage(
          "adminAccountsMessage",
          error.message || "No se pudo cambiar el baneo.",
          true,
        );
      }
      return;
    }

    const name = button.getAttribute("data-reset");
    if (!name) return;
    if (!window.confirm(`¿Generar una contraseña temporal para ${name}?`)) return;
    try {
      const payload = await api(
        `/api/admin/accounts/${encodeURIComponent(name)}/reset-password`,
        { method: "POST", body: {} },
      );
      const value = $("adminTempPasswordValue");
      if (value) value.textContent = payload.temporaryPassword;
      const box = $("adminTempPasswordBox");
      if (box) box.hidden = false;
      setMessage("adminAccountsMessage", `Contraseña temporal generada para ${name}.`);
      await loadAccounts();
    } catch (error) {
      setMessage("adminAccountsMessage", error.message || "No se pudo resetear.", true);
    }
  });

  const copy = $("copyAdminTempPassword");
  if (copy) {
    copy.addEventListener("click", async () => {
      const value = $("adminTempPasswordValue")?.textContent || "";
      const copied = await copyText(value);
      copy.textContent = copied ? "COPIADO" : "ERROR";
      window.setTimeout(() => {
        copy.textContent = "COPIAR";
      }, 1500);
    });
  }
}

function wireAdminPassword() {
  const form = $("adminPasswordForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if ($("adminNewPassword").value !== $("adminPasswordConfirm").value) {
      setMessage("adminPasswordMessage", "Las claves nuevas no coinciden.", true);
      return;
    }
    setMessage("adminPasswordMessage", "Cambiando clave…");
    try {
      const payload = await api("/api/admin/password", {
        method: "POST",
        body: {
          currentPassword: $("adminCurrentPassword").value,
          newPassword: $("adminNewPassword").value,
        },
      });
      csrfToken = payload.csrfToken;
      form.reset();
      setMessage("adminPasswordMessage", "Clave de administrador cambiada.");
    } catch (error) {
      setMessage("adminPasswordMessage", error.message || "No se pudo cambiar.", true);
    }
  });
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
        body: {
          username: $("adminUsername").value.trim(),
          password: $("adminPassword").value,
        },
      });
      csrfToken = payload.csrfToken;
      form.reset();
      setMessage("adminLoginMessage", "");
      showPanel();
      await loadInvites();
      await loadAccounts();
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
  wireAccounts();
  wireAdminPassword();
  loadMe();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
