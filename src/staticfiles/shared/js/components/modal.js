(function () {
  "use strict";

  /* ── Helpers ───────────────────────────────────────────── */

  function getBackdrop(id) {
    return document.getElementById(id);
  }

  function openModal(id) {
    var backdrop = getBackdrop(id);
    if (!backdrop) return;

    backdrop.classList.add("is-open");

    // Move focus to the first focusable element inside the modal.
    var focusable = backdrop.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable) focusable.focus();
  }

  function closeModal(id) {
    var backdrop = getBackdrop(id);
    if (!backdrop) return;
    backdrop.classList.remove("is-open");
  }

  /* ── Open triggers — [data-modal-open="modal-id"] ─────── */

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-modal-open]");
    if (!trigger) return;
    e.preventDefault();
    openModal(trigger.getAttribute("data-modal-open"));
  });

  /* ── Close triggers — [data-modal-close="modal-id"] ───── */

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-modal-close]");
    if (!btn) return;
    closeModal(btn.getAttribute("data-modal-close"));
  });

  /* ── Close on backdrop click ───────────────────────────── */

  document.addEventListener("click", function (e) {
    if (!e.target.classList.contains("modal-backdrop")) return;
    if (!e.target.classList.contains("is-open")) return;
    closeModal(e.target.id);
  });

  /* ── Close on Escape ───────────────────────────────────── */

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var open = document.querySelector(".modal-backdrop.is-open");
    if (open) closeModal(open.id);
  });
})();
