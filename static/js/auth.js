/**
 * auth.js
 * OcuScan AI — Authentication & Session Gateway
 *
 * Handles login form submission, credential validation, sessionStorage role tagging,
 * and role-based routing. Provides the routeGuard() helper for protected pages.
 */

(function () {
  "use strict";

  /* ── Credential store (demo / evaluator) ──────────────────
     In a real system these would never live in client JS.
     This is purely a front-end demo simulation.
  ─────────────────────────────────────────────────────────── */
  const VALID_USERS = {
    "tech_demo":  { password: "password", role: "technician",     redirect: "technician.html" },
    "doc_demo":   { password: "password", role: "doctor",         redirect: "doctor.html"     },
    "admin_demo": { password: "password", role: "admin",          redirect: "dashboard.html"  },
  };

  const SESSION_KEY = "currentUserRole";
  const SESSION_ID_KEY = "currentUserId";

  /* ── DOM refs ─────────────────────────────────────────── */
  const loginForm   = document.getElementById("login-form");
  const usernameEl  = document.getElementById("username");
  const passwordEl  = document.getElementById("password");
  const submitBtn   = document.getElementById("submit-btn");
  const btnSpinner  = document.getElementById("btn-spinner");
  const btnIcon     = document.getElementById("btn-icon");
  const errorBox    = document.getElementById("auth-error");
  const errorText   = document.getElementById("auth-error-text");
  const pwToggle    = document.getElementById("pw-toggle");
  const pwEye       = document.getElementById("pw-eye");

  /* ── Password visibility toggle ──────────────────────── */
  if (pwToggle) {
    pwToggle.addEventListener("click", function () {
      const isText = passwordEl.type === "text";
      passwordEl.type = isText ? "password" : "text";

      // Swap icon
      if (isText) {
        // Eye open (password visible → clicking hides)
        pwEye.innerHTML = `
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        `;
      } else {
        // Eye off (password hidden → clicking reveals)
        pwEye.innerHTML = `
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
        `;
      }
    });
  }

  /* ── Show / hide error ────────────────────────────────── */
  function showError(msg) {
    if (errorText) errorText.textContent = msg || "Invalid credentials or unauthorized role.";
    if (errorBox)  {
      errorBox.classList.remove("visible");
      // Re-trigger animation
      void errorBox.offsetWidth;
      errorBox.classList.add("visible");
    }
    // Shake input fields
    [usernameEl, passwordEl].forEach(el => {
      if (el) {
        el.style.borderColor = "rgba(244,63,94,0.6)";
        el.style.boxShadow   = "0 0 0 3px rgba(244,63,94,0.12)";
        setTimeout(() => {
          el.style.borderColor = "";
          el.style.boxShadow   = "";
        }, 2000);
      }
    });
  }

  function hideError() {
    if (errorBox) errorBox.classList.remove("visible");
  }

  /* ── Button loading state ─────────────────────────────── */
  function setLoading(active) {
    if (!submitBtn) return;
    submitBtn.disabled = active;
    if (btnSpinner) btnSpinner.style.display = active ? "block" : "none";
    if (btnIcon)    btnIcon.style.display    = active ? "none"  : "block";
    submitBtn.querySelector("span") && null;
  }

  /* ── Form Submission Handler ──────────────────────────── */
  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      e.preventDefault();
      hideError();

      const username = (usernameEl.value || "").trim().toLowerCase();
      const password = (passwordEl.value || "").trim();

      if (!username || !password) {
        showError("Please enter both Staff ID and Password.");
        return;
      }

      setLoading(true);

      // Simulate a brief auth check (~600ms for realism)
      setTimeout(function () {
        const userRecord = VALID_USERS[username];

        if (!userRecord || userRecord.password !== password) {
          setLoading(false);
          showError("Invalid credentials or unauthorized role. Please try again.");
          passwordEl.value = "";
          passwordEl.focus();
          return;
        }

        // ── Auth success ─────────────────────────────────
        sessionStorage.setItem(SESSION_KEY,    userRecord.role);
        sessionStorage.setItem(SESSION_ID_KEY, username);

        // Brief success flash before redirect
        submitBtn.style.background = "linear-gradient(135deg, #16a34a, #22c55e)";
        submitBtn.innerHTML = `
          <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
          Authenticated — Redirecting...
        `;

        setTimeout(function () {
          window.location.href = userRecord.redirect;
        }, 600);

      }, 620);
    });
  }

  /* ── Clear errors on field change ─────────────────────── */
  [usernameEl, passwordEl].forEach(el => {
    if (el) el.addEventListener("input", hideError);
  });

  /* ── Enter key on username → focus password ───────────── */
  if (usernameEl) {
    usernameEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        if (passwordEl) passwordEl.focus();
      }
    });
  }

})();

/* ═══════════════════════════════════════════════════════════════════
   ROUTE GUARD — exported for use by technician.js, doctor.js, dashboard.js
   Call at the very top of each protected page script.

   Usage:
     if (!routeGuard("technician")) return;   // in technician.js
     if (!routeGuard("doctor"))     return;   // in doctor.js
     if (!routeGuard("admin"))      return;   // in dashboard.js

   The guard also accepts ["doctor","admin"] for multi-role pages.
═══════════════════════════════════════════════════════════════════ */
function routeGuard(allowedRole) {
  const currentRole = sessionStorage.getItem("currentUserRole");

  // Normalise to array for multi-role support
  const allowed = Array.isArray(allowedRole) ? allowedRole : [allowedRole];

  if (!currentRole || !allowed.includes(currentRole)) {
    // Persist where they were trying to go so we can restore after login
    sessionStorage.setItem("authRedirectAttempt", window.location.pathname);

    // Redirect to login
    window.location.href = "login.html";
    return false;
  }

  return true;
}

/* ── Demo Pill Button Logic ──────────────────────────────────────
   Fills credentials silently and auto-submits the form.
   No credentials are ever displayed on screen.
─────────────────────────────────────────────────────────────── */
function demoLogin(userId) {
  const usernameEl = document.getElementById("username");
  const passwordEl = document.getElementById("password");
  const loginForm  = document.getElementById("login-form");

  if (!usernameEl || !passwordEl || !loginForm) return;

  // Fill without exposing values as visible text hints
  usernameEl.value = userId;
  passwordEl.value = "password";

  // Dispatch input events so the form's change listeners fire
  usernameEl.dispatchEvent(new Event("input"));
  passwordEl.dispatchEvent(new Event("input"));

  // Auto-submit — triggers the existing validation + redirect logic
  loginForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

// Attach to pill buttons once DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  var techBtn = document.getElementById("demo-tech-btn");
  var docBtn  = document.getElementById("demo-doc-btn");
  if (techBtn) techBtn.addEventListener("click", function () { demoLogin("tech_demo"); });
  if (docBtn)  docBtn.addEventListener("click",  function () { demoLogin("doc_demo");  });
});
