document.addEventListener("DOMContentLoaded", () => {
  const toggles = document.querySelectorAll("[data-password-toggle]");

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const fieldControl = toggle.closest(".field-control");
      const input = fieldControl?.querySelector("input");

      if (!input) {
        return;
      }

      input.type = input.type === "password" ? "text" : "password";
    });
  });

  const form = document.querySelector("[data-reset-form]");
  if (!form) {
    return;
  }

  const passwordInput = form.querySelector("#id_new_password1");
  const confirmInput = form.querySelector("#id_new_password2");
  const meter = form.querySelector("[data-password-meter]");
  const bar = form.querySelector("[data-password-strength-bar]");
  const label = form.querySelector("[data-password-strength-label]");
  const match = form.querySelector("[data-password-match]");

  const evaluateStrength = (value) => {
    if (!value) {
      return { visible: false, width: "0%", color: "", label: "" };
    }

    const hasUpper = /[A-Z]/.test(value);
    const hasLower = /[a-z]/.test(value);
    const hasDigitOrSymbol = /[\d\W_]/.test(value);

    if (value.length < 8 || !(hasUpper && hasLower)) {
      return { visible: true, width: "33%", color: "#f44336", label: "Yếu" };
    }

    if (!hasDigitOrSymbol || value.length < 10) {
      return { visible: true, width: "66%", color: "#ff9800", label: "Trung bình" };
    }

    return { visible: true, width: "100%", color: "#4caf50", label: "Mạnh" };
  };

  const render = () => {
    const strength = evaluateStrength(passwordInput?.value || "");

    if (meter && bar && label) {
      meter.classList.toggle("is-visible", strength.visible);
      bar.style.width = strength.width;
      bar.style.backgroundColor = strength.color;
      label.textContent = strength.label;
      label.style.color = strength.color;
    }

    if (match && passwordInput && confirmInput) {
      if (!confirmInput.value) {
        match.textContent = "";
        match.classList.remove("is-success", "is-error");
        return;
      }

      const matched = passwordInput.value === confirmInput.value;
      match.textContent = matched ? "Mật khẩu khớp" : "Mật khẩu không khớp";
      match.classList.toggle("is-success", matched);
      match.classList.toggle("is-error", !matched);
    }
  };

  passwordInput?.addEventListener("input", render);
  confirmInput?.addEventListener("input", render);
  render();
});
