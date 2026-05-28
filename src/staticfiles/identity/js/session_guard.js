(function () {
  "use strict";

  var root = document.querySelector("[data-session-guard-status-url]");
  if (!root || !window.fetch) {
    return;
  }

  var statusUrl = root.getAttribute("data-session-guard-status-url");
  var loginUrl = root.getAttribute("data-session-guard-login-url") || "/itsnotasignin/";
  var pollInterval = Number(root.getAttribute("data-session-guard-interval") || "15000");
  var modal = document.querySelector("[data-session-guard-modal]");
  var loginLink = document.querySelector("[data-session-guard-login]");
  var stopped = false;

  function showInvalidatedSession(nextLoginUrl) {
    if (stopped) {
      return;
    }
    stopped = true;
    if (loginLink) {
      loginLink.setAttribute("href", nextLoginUrl || loginUrl);
    }
    if (modal) {
      modal.classList.add("is-open");
      var focusTarget = modal.querySelector("[data-session-guard-login]");
      if (focusTarget) {
        focusTarget.focus();
      }
      return;
    }
    window.location.assign(nextLoginUrl || loginUrl);
  }

  function checkSession() {
    if (stopped) {
      return;
    }

    window.fetch(statusUrl, {
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    }).then(function (response) {
      return response.json().catch(function () {
        return {
          authenticated: response.ok,
          session_valid: response.ok,
          login_url: loginUrl,
        };
      });
    }).then(function (payload) {
      if (!payload.authenticated || !payload.session_valid) {
        showInvalidatedSession(payload.login_url);
        return;
      }
      window.setTimeout(checkSession, pollInterval);
    }).catch(function () {
      window.setTimeout(checkSession, pollInterval);
    });
  }

  window.setTimeout(checkSession, pollInterval);
})();
