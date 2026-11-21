"use strict";

const $ = (id) => document.getElementById(id);

let csrfToken = null;
let currentAccount = null;

function setMessage(text, isError = false) {
  const node = $("formMessage");
  if (!node) return;
  node.textContent = text || "";
  node.classList.toggle("is-error", Boolean(isError));
}

function detailMessage(body, fallback) {
  const detail = body && body.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || String(item)).join(" ");
  }
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
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
    const error = new Error(detailMessage(payload, `Error ${response.status}`));
    error.status = response.status;
    throw error;
  }
  return payload;
}

function renderPersonas(personas) {
  const list = $("personaList");
  if (!list) return;
  list.innerHTML = (personas || [])
    .map((name) => `<li>${escapeHtml(name)}</li>`)
    .join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showAuth() {
  const panels = $("authPanels");
  const accountPanel = $("accountPanel");
  if (panels) panels.hidden = false;
  if (accountPanel) accountPanel.hidden = true;
  currentAccount = null;
}

function showAccount(account, csrf) {
  currentAccount = account;
  csrfToken = csrf || csrfToken;
  const panels = $("authPanels");
  const accountPanel = $("accountPanel");
  if (panels) panels.hidden = true;
  if (accountPanel) accountPanel.hidden = false;

  const accountName = $("accountName");
  const persona = $("accountPersona");
  const email = $("accountEmail");
  if (accountName) accountName.textContent = account.accountName || "—";
  if (persona) persona.textContent = account.primaryPersona || "—";
  if (email) email.textContent = account.email || "Sin email";

  renderPersonas(account.personas);
  const toggle = $("appearOnlineToggle");
  if (toggle) toggle.checked = Boolean(account.appearOnline);
}

async function loadMe() {
  try {
    const payload = await api("/api/account/me");
    if (payload.authenticated && payload.account) {
      showAccount(payload.account, payload.csrfToken);
    } else {
      showAuth();
    }
  } catch {
    showAuth();
  }
}

function wireLogin() {
  const form = $("loginForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Entrando…");
    try {
      const payload = await api("/api/account/login", {
        method: "POST",
        body: {
          identifier: $("loginIdentifier").value.trim(),
          password: $("loginPassword").value,
        },
      });
      showAccount(payload.account, payload.csrfToken);
      setMessage("Sesión iniciada. Ya podés entrar al juego.");
      form.reset();
    } catch (error) {
      setMessage(error.message || "No se pudo iniciar sesión.", true);
    }
  });
}

function wireRegister() {
  const form = $("createForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = $("createPassword").value;
    const confirmation = $("createPasswordConfirm").value;
    if (password !== confirmation) {
      setMessage("Las contraseñas no coinciden.", true);
      return;
    }
    setMessage("Creando cuenta…");
    try {
      const payload = await api("/api/account/register", {
        method: "POST",
        body: {
          accountName: $("createAccountName").value.trim(),
          persona: $("createPersona").value.trim(),
          email: $("createEmail").value.trim(),
          password,
          countryCode: "",
          appearOnline: $("createAppearOnline").checked,
          challengeSeriesAssist: true,
          inviteCode: $("createInviteCode").value.trim(),
        },
      });
      showAccount(payload.account, payload.csrfToken);
      setMessage("Cuenta creada. Descargá el cliente y entrá al juego.");
      form.reset();
    } catch (error) {
      setMessage(error.message || "No se pudo crear la cuenta.", true);
    }
  });
}

function wireLogout() {
  const button = $("logoutButton");
  if (!button) return;
  button.addEventListener("click", async () => {
    try {
      await api("/api/account/logout", { method: "POST", body: {} });
    } catch {
      /* the session may already be gone */
    }
    csrfToken = null;
    showAuth();
    setMessage("Sesión cerrada.");
  });
}

function wirePreferences() {
  const toggle = $("appearOnlineToggle");
  if (!toggle) return;
  toggle.addEventListener("change", async () => {
    const desired = toggle.checked;
    try {
      await api("/api/account/preferences", {
        method: "POST",
        body: { appearOnline: desired },
      });
      if (currentAccount) currentAccount.appearOnline = desired;
      setMessage(desired ? "Vas a aparecer en línea." : "Vas a aparecer desconectado.");
    } catch (error) {
      toggle.checked = !desired;
      if (error.status === 401 || error.status === 403) {
        showAuth();
        setMessage("La sesión venció. Volvé a entrar.", true);
      } else {
        setMessage(error.message || "No se pudo guardar la preferencia.", true);
      }
    }
  });
}

function init() {
  wireLogin();
  wireRegister();
  wireLogout();
  wirePreferences();
  loadMe();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
