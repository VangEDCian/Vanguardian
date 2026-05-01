(function () {
  const toggleButtons = document.querySelectorAll("[data-admin-password-toggle]");

  toggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const control = button.closest(".admin-password-control");
      const input = control ? control.querySelector("input") : null;

      if (!input) {
        return;
      }

      const shouldShow = input.type === "password";
      const showLabel = button.dataset.showLabel || "Show";
      const hideLabel = button.dataset.hideLabel || "Hide";

      input.type = shouldShow ? "text" : "password";
      button.textContent = shouldShow ? hideLabel : showLabel;
    });
  });
})();
