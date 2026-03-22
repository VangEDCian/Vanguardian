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
});

