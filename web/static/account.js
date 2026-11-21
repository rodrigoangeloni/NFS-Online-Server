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

function setSectionMessage(id, text, isError = false) {
  const node = $(id);
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
  const forgotPanel = $("forgotPanel");
  if (panels) panels.hidden = false;
  if (accountPanel) accountPanel.hidden = true;
  if (forgotPanel) forgotPanel.hidden = true;
  currentAccount = null;
}

function showAccount(account, csrf, recoveryCode = "") {
  currentAccount = account;
  csrfToken = csrf || csrfToken;
  const panels = $("authPanels");
  const accountPanel = $("accountPanel");
  const forgotPanel = $("forgotPanel");
  if (panels) panels.hidden = true;
  if (accountPanel) accountPanel.hidden = false;
  if (forgotPanel) forgotPanel.hidden = true;

  const accountName = $("accountName");
  const persona = $("accountPersona");
  const email = $("accountEmail");
  if (accountName) accountName.textContent = account.accountName || "—";
  if (persona) persona.textContent = account.primaryPersona || "—";
  if (email) email.textContent = account.email || "Sin email";

  const emailInput = $("accountEmailInput");
  if (emailInput) emailInput.value = account.email || "";

  const warning = $("mustChangeWarning");
  if (warning) warning.hidden = !account.mustChangePassword;

  const recoveryBox = $("registrationRecoveryBox");
  if (recoveryBox) {
    recoveryBox.hidden = !recoveryCode;
    if (recoveryCode) {
      const value = $("registrationRecoveryValue");
      if (value) value.textContent = recoveryCode;
    }
  }

  renderPersonas(account.personas);
  const toggle = $("appearOnlineToggle");
  if (toggle) toggle.checked = Boolean(account.appearOnline);
  if (account.mustChangePassword) {
    const password = $("passwordCurrent");
    if (password) password.focus();
  }
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
      showAccount(payload.account, payload.csrfToken, payload.recoveryCode || "");
      setMessage("Cuenta creada. Guardá el código de recuperación y descargá el cliente.");
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

function wireRecoveryActions() {
  const showForgot = $("showForgot");
  const hideForgot = $("hideForgot");
  if (showForgot) {
    showForgot.addEventListener("click", () => {
      const auth = $("authPanels");
      const account = $("accountPanel");
      const forgot = $("forgotPanel");
      if (auth) auth.hidden = true;
      if (account) account.hidden = true;
      if (forgot) forgot.hidden = false;
      setMessage("");
    });
  }
  if (hideForgot) {
    hideForgot.addEventListener("click", () => {
      showAuth();
      setMessage("");
    });
  }

  const form = $("forgotForm");
  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const box = $("temporaryPasswordBox");
      if (box) box.hidden = true;
      setMessage("Verificando datos…");
      try {
        const payload = await api("/api/account/forgot", {
          method: "POST",
          body: {
            accountName: $("forgotAccountName").value.trim(),
            email: $("forgotEmail").value.trim(),
            recoveryCode: $("forgotRecoveryCode").value.trim(),
          },
        });
        const value = $("temporaryPasswordValue");
        if (value) value.textContent = payload.temporaryPassword;
        if (box) box.hidden = false;
        setMessage("");
      } catch (error) {
        setMessage(error.message || "Los datos no coinciden.", true);
      }
    });
  }

  const copyTemp = $("copyTemporaryPassword");
  if (copyTemp) {
    copyTemp.addEventListener("click", async () => {
      const value = $("temporaryPasswordValue")?.textContent || "";
      const copied = await copyText(value);
      copyTemp.textContent = copied ? "COPIADO" : "ERROR";
      window.setTimeout(() => {
        copyTemp.textContent = "COPIAR";
      }, 1500);
    });
  }

  const generate = $("generateRecoveryCode");
  if (generate) {
    generate.addEventListener("click", async () => {
      setSectionMessage("recoveryMessage", "Generando código…");
      try {
        const payload = await api("/api/account/recovery-code", {
          method: "POST",
          body: {},
        });
        const value = $("recoveryCodeValue");
        if (value) value.textContent = payload.recoveryCode;
        const box = $("recoveryCodeBox");
        if (box) box.hidden = false;
        setSectionMessage("recoveryMessage", "Código nuevo generado. Guardalo.");
      } catch (error) {
        setSectionMessage("recoveryMessage", error.message || "No se pudo generar.", true);
      }
    });
  }

  const copyRecovery = $("copyRecoveryCode");
  if (copyRecovery) {
    copyRecovery.addEventListener("click", async () => {
      const value = $("recoveryCodeValue")?.textContent || "";
      const copied = await copyText(value);
      copyRecovery.textContent = copied ? "COPIADO" : "ERROR";
      window.setTimeout(() => {
        copyRecovery.textContent = "COPIAR";
      }, 1500);
    });
  }

  const copyRegistration = $("copyRegistrationRecovery");
  if (copyRegistration) {
    copyRegistration.addEventListener("click", async () => {
      const value = $("registrationRecoveryValue")?.textContent || "";
      const copied = await copyText(value);
      copyRegistration.textContent = copied ? "COPIADO" : "ERROR";
      window.setTimeout(() => {
        copyRegistration.textContent = "COPIAR";
      }, 1500);
    });
  }
}

function wirePassword() {
  const form = $("passwordForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const newPassword = $("passwordNew").value;
    if (newPassword !== $("passwordConfirm").value) {
      setSectionMessage("passwordMessage", "Las contraseñas nuevas no coinciden.", true);
      return;
    }
    setSectionMessage("passwordMessage", "Cambiando contraseña…");
    try {
      await api("/api/account/password", {
        method: "POST",
        body: {
          currentPassword: $("passwordCurrent").value,
          newPassword,
        },
      });
      if (currentAccount) currentAccount.mustChangePassword = false;
      const warning = $("mustChangeWarning");
      if (warning) warning.hidden = true;
      setSectionMessage("passwordMessage", "Contraseña cambiada.");
      form.reset();
    } catch (error) {
      setSectionMessage("passwordMessage", error.message || "No se pudo cambiar.", true);
    }
  });
}

function wireEmail() {
  const form = $("emailForm");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setSectionMessage("emailMessage", "Guardando email…");
    try {
      const payload = await api("/api/account/email", {
        method: "POST",
        body: {
          email: $("accountEmailInput").value.trim(),
          password: $("emailPassword").value,
        },
      });
      if (currentAccount) currentAccount.email = payload.account.email;
      const email = $("accountEmail");
      if (email) email.textContent = payload.account.email || "Sin email";
      setSectionMessage("emailMessage", "Email guardado.");
      form.reset();
      const emailInput = $("accountEmailInput");
      if (emailInput) emailInput.value = payload.account.email || "";
    } catch (error) {
      setSectionMessage("emailMessage", error.message || "No se pudo guardar.", true);
    }
  });
}

function init() {
  wireLogin();
  wireRegister();
  wireLogout();
  wirePreferences();
  wireRecoveryActions();
  wirePassword();
  wireEmail();
  loadMe();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
