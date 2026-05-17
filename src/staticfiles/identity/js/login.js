document.addEventListener("DOMContentLoaded", () => {
  const toggles = document.querySelectorAll("[data-password-toggle]");

  toggles.forEach((toggle) => {
    const icon = toggle.querySelector(".svg-icon");
    const defaultIconUrl = icon?.style.getPropertyValue("--icon-url") || "";
    const eyeSlashIconUrl = defaultIconUrl.replace("eye.svg", "eye-slash.svg");

    const syncIcon = (isPasswordVisible) => {
      if (!icon || !defaultIconUrl) {
        return;
      }

      icon.style.setProperty("--icon-url", isPasswordVisible ? eyeSlashIconUrl : defaultIconUrl);
      toggle.setAttribute("aria-pressed", isPasswordVisible ? "true" : "false");
    };

    toggle.addEventListener("click", () => {
      const fieldControl = toggle.closest(".field-control");
      const input = fieldControl?.querySelector("input");

      if (!input) {
        return;
      }

      input.type = input.type === "password" ? "text" : "password";
      syncIcon(input.type === "text");
    });

    const input = toggle.closest(".field-control")?.querySelector("input");
    if (input) {
      syncIcon(input.type === "text");
    }
  });
});

