(function () {
  "use strict";

  function scrollActiveFormIntoSidebarView() {
    var sidebar = document.querySelector("aside.subject-detail-screen__sidebar");
    if (!sidebar) {
      return;
    }

    var activeForm = sidebar.querySelector(".subject-detail-sidebar__child.is-active");
    if (!activeForm) {
      return;
    }

    var sidebarRect = sidebar.getBoundingClientRect();
    var activeFormRect = activeForm.getBoundingClientRect();
    var targetScrollTop =
      sidebar.scrollTop +
      activeFormRect.top -
      sidebarRect.top -
      sidebar.clientHeight / 2 +
      activeFormRect.height / 2;

    sidebar.scrollTo({
      top: Math.max(targetScrollTop, 0),
      behavior: "smooth",
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scrollActiveFormIntoSidebarView, { once: true });
    return;
  }

  scrollActiveFormIntoSidebarView();
})();
