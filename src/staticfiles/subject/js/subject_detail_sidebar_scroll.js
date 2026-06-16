(function () {
  "use strict";

  function scrollActiveFormIntoSidebarView() {
    var sidebar = document.querySelector("aside.subject-detail-screen__sidebar");
    if (!sidebar) {
      return;
    }

    var activeItem =
      sidebar.querySelector(".subject-detail-sidebar__child.is-active") ||
      sidebar.querySelector(".subject-detail-sidebar__group.is-active");
    if (!activeItem) {
      return;
    }

    var sidebarRect = sidebar.getBoundingClientRect();
    var activeItemRect = activeItem.getBoundingClientRect();
    var targetScrollTop =
      sidebar.scrollTop +
      activeItemRect.top -
      sidebarRect.top -
      sidebar.clientHeight / 2 +
      activeItemRect.height / 2;

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
