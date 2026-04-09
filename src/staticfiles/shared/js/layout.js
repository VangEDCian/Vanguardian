(function () {
  const shell = document.querySelector("[data-dashboard-shell]");
  if (!shell) {
    return;
  }

  const navItems = Array.from(shell.querySelectorAll("[data-nav-item]"));
  const breadcrumbActive = shell.querySelector("[data-breadcrumb-active]");

  const dropdowns = Array.from(shell.querySelectorAll("[data-dropdown]"));
  const horizontalDragScrollAreas = Array.from(shell.querySelectorAll("[data-horizontal-drag-scroll]"));
  const avatarMenu = shell.querySelector("[data-avatar-menu]");
  const avatarTrigger = avatarMenu?.querySelector("[data-avatar-trigger]");
  const avatarPanel = avatarMenu?.querySelector("[data-avatar-panel]");

  function closeAllDropdowns(except) {
    dropdowns.forEach((dropdown) => {
      if (except && dropdown === except) {
        return;
      }

      const trigger = dropdown.querySelector("[data-dropdown-trigger]");
      const menu = dropdown.querySelector("[data-dropdown-menu]");
      if (trigger) {
        trigger.setAttribute("aria-expanded", "false");
      }
      if (menu) {
        menu.hidden = true;
      }
    });
  }

  function closeAvatarMenu() {
    if (avatarTrigger) {
      avatarTrigger.setAttribute("aria-expanded", "false");
    }
    if (avatarPanel) {
      avatarPanel.hidden = true;
    }
  }

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((node) => node.classList.remove("is-active"));
      item.classList.add("is-active");
      const label = item.getAttribute("data-nav-label") || "";
      if (breadcrumbActive) {
        breadcrumbActive.textContent = label;
      }
    });
  });

  dropdowns.forEach((dropdown, index) => {
    const trigger = dropdown.querySelector("[data-dropdown-trigger]");
    const menu = dropdown.querySelector("[data-dropdown-menu]");
    const valueNode = dropdown.querySelector("[data-dropdown-value]");
    const options = Array.from(dropdown.querySelectorAll("[data-dropdown-option]"));

    if (!trigger || !menu || !valueNode) {
      return;
    }

    trigger.addEventListener("click", () => {
      const isOpen = trigger.getAttribute("aria-expanded") === "true";
      closeAllDropdowns(dropdown);
      closeAvatarMenu();
      trigger.setAttribute("aria-expanded", isOpen ? "false" : "true");
      menu.hidden = isOpen;
    });

    options.forEach((option) => {
      option.addEventListener("click", () => {
        valueNode.textContent = option.textContent || "";
        trigger.setAttribute("aria-expanded", "false");
        menu.hidden = true;
      });
    });
  });


  horizontalDragScrollAreas.forEach((area) => {
    let isDragging = false;
    let startX = 0;
    let startScrollLeft = 0;

    area.addEventListener("mousedown", (event) => {
      if (event.button !== 0) {
        return;
      }
      isDragging = true;
      startX = event.pageX;
      startScrollLeft = area.scrollLeft;
      area.classList.add("is-dragging");
    });

    area.addEventListener("mousemove", (event) => {
      if (!isDragging) {
        return;
      }
      event.preventDefault();
      const deltaX = event.pageX - startX;
      area.scrollLeft = startScrollLeft - deltaX;
    });

    ["mouseleave", "mouseup"].forEach((eventName) => {
      area.addEventListener(eventName, () => {
        isDragging = false;
        area.classList.remove("is-dragging");
      });
    });

    area.addEventListener("wheel", (event) => {
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
        return;
      }
      event.preventDefault();
      area.scrollLeft += event.deltaY;
    }, { passive: false });
  });

  if (avatarTrigger && avatarPanel) {
    avatarTrigger.addEventListener("click", () => {
      const isOpen = avatarTrigger.getAttribute("aria-expanded") === "true";
      closeAllDropdowns();
      avatarTrigger.setAttribute("aria-expanded", isOpen ? "false" : "true");
      avatarPanel.hidden = isOpen;
    });
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }

    const clickedDropdown = target.closest("[data-dropdown]");
    const clickedAvatar = target.closest("[data-avatar-menu]");

    if (!clickedDropdown) {
      closeAllDropdowns();
    }
    if (!clickedAvatar) {
      closeAvatarMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllDropdowns();
      closeAvatarMenu();
    }
  });
})();


(function () {
  const setCookie = (name, value, days = null) => {
    let expires = "";
    if (days) {
      const date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    }
    // encodeURIComponent handles special characters like semicolons or spaces
    document.cookie = encodeURIComponent(name) + "=" + encodeURIComponent(value) + expires + "; path=/; SameSite=Lax";
  }

  const cookiesKeyStudy = document.getElementById('idx-comment-select---cookies-key--study').value;
  document.querySelectorAll('.common-select--study button[data-dropdown-option]').forEach((node, index) => {
    node.addEventListener('click', (event) => {
      setCookie(cookiesKeyStudy, node.getAttribute("value"));
      window.location.reload();
    })
  });

  const cookiesKeySite = document.getElementById('idx-comment-select---cookies-key--site').value;
  document.querySelectorAll('.common-select--site button[data-dropdown-option]').forEach((node, index) => {
    node.addEventListener('click', (event) => {
      setCookie(cookiesKeySite, node.getAttribute("value"));
      window.location.reload();
    })
  });
})();
