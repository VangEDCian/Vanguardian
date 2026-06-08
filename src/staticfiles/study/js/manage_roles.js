(function () {
  function initRoleSelects() {
    if (!window.jQuery || !jQuery.fn.select2) {
      return;
    }

    jQuery(".manage-roles-select").select2({
      width: "100%",
      allowClear: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRoleSelects);
  } else {
    initRoleSelects();
  }
})();
