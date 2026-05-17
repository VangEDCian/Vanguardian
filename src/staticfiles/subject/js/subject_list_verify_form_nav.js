(function () {
  function resolveElement(target) {
    if (target instanceof Element) {
      return target;
    }
    if (target && target.nodeType === 3 && target.parentElement) {
      return target.parentElement;
    }
    return null;
  }

  document.addEventListener(
    "click",
    function (event) {
      const el = resolveElement(event.target);
      if (!el) {
        return;
      }
      const nav = el.closest("[data-subject-verify-form-nav]");
      if (!(nav instanceof HTMLElement)) {
        return;
      }
      const url = nav.getAttribute("data-subject-verify-form-nav");
      if (!url) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      window.location.assign(url);
    },
    true,
  );
})();
