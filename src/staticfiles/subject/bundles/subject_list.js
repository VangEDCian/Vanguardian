/* Source: shared/js/components/common-table.js */
(function () {
  const tables = Array.from(document.querySelectorAll("[data-common-table]"));
  if (!tables.length) {
    return;
  }

  function syncRowSelection(row, checkbox) {
    row.classList.toggle("is-selected", checkbox.checked);
  }

  function resolveClickElement(target) {
    if (target instanceof Element) {
      return target;
    }
    if (target instanceof Text && target.parentElement) {
      return target.parentElement;
    }
    return null;
  }

  function isInteractiveTarget(target) {
    const el = resolveClickElement(target);
    if (!el) {
      return false;
    }
    return Boolean(
      el.closest("[data-dropdown]") ||
        el.closest("a, button, input, label, select, textarea"),
    );
  }

  function getDetailHref(row) {
    if (row.hasAttribute("data-detail-href")) {
      return row.getAttribute("data-detail-href") || "";
    }

    const firstLink = row.querySelector("a[href]");
    if (firstLink instanceof HTMLAnchorElement) {
      return firstLink.href;
    }

    return "";
  }

  tables.forEach((table) => {
    const enableDetailClick = table.dataset.enableDetailClick !== "false";
    const sortHeaders = Array.from(table.querySelectorAll("[data-sort-header]"));
    const rows = Array.from(table.querySelectorAll("[data-selectable-row]"));

    sortHeaders.forEach((header) => {
      const form = header.querySelector("[data-sort-form]");
      if (!(form instanceof HTMLFormElement)) {
        return;
      }

      header.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
          return;
        }

        if (isInteractiveTarget(target)) {
          return;
        }

        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
          return;
        }

        form.submit();
      });
    });

    rows.forEach((row) => {
      const checkbox = row.querySelector("[data-row-checkbox]");
      if (!(checkbox instanceof HTMLInputElement)) {
        return;
      }

      syncRowSelection(row, checkbox);

      checkbox.addEventListener("change", () => {
        syncRowSelection(row, checkbox);
      });

      row.addEventListener("click", (event) => {
        const target = resolveClickElement(event.target);
        if (!target) {
          return;
        }

        if (isInteractiveTarget(target)) {
          return;
        }

        const clickedCell = target.closest("td");
        if (!(clickedCell instanceof HTMLTableCellElement)) {
          return;
        }

        if (clickedCell.cellIndex === 0) {
          checkbox.checked = !checkbox.checked;
          syncRowSelection(row, checkbox);
          return;
        }

        const detailHref = getDetailHref(row);
        if (enableDetailClick && detailHref) {
          window.location.href = detailHref;
        }
      });
    });
  });
})();

/* Source: shared/js/layout.js */
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
    const inputNode = dropdown.querySelector("[data-dropdown-input]");
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
        if (inputNode) {
          inputNode.value = option.value || "";
        }
        trigger.setAttribute("aria-expanded", "false");
        menu.hidden = true;
        if (option.hasAttribute("data-dropdown-auto-submit")) {
          option.form?.submit();
        }
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

/* Source: shared/js/components/modal.js */
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

/* Source: shared/js/request_feedback.js */
(() => {
  const DISPLAY_DURATION_MS = 2100;

  function hideFeedbackMessages() {
    const containers = document.querySelectorAll('.request-feedback');
    containers.forEach((container) => {
      window.setTimeout(() => {
        container.classList.add('is-hidden');
      }, DISPLAY_DURATION_MS);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideFeedbackMessages, { once: true });
    return;
  }
  hideFeedbackMessages();
})();

/* Source: identity/js/session_guard.js */
(function () {
  "use strict";

  var root = document.querySelector("[data-session-guard-status-url]");
  if (!root || !window.fetch) {
    return;
  }

  var statusUrl = root.getAttribute("data-session-guard-status-url");
  var loginUrl = root.getAttribute("data-session-guard-login-url") || "/login/";
  var pollInterval = Number(root.getAttribute("data-session-guard-interval") || "15000");
  var modal = document.querySelector("[data-session-guard-modal]");
  var loginLink = document.querySelector("[data-session-guard-login]");
  var stopped = false;

  function showInvalidatedSession(nextLoginUrl) {
    if (stopped) {
      return;
    }
    stopped = true;
    if (loginLink) {
      loginLink.setAttribute("href", nextLoginUrl || loginUrl);
    }
    if (modal) {
      modal.classList.add("is-open");
      var focusTarget = modal.querySelector("[data-session-guard-login]");
      if (focusTarget) {
        focusTarget.focus();
      }
      return;
    }
    window.location.assign(nextLoginUrl || loginUrl);
  }

  function checkSession() {
    if (stopped) {
      return;
    }

    window.fetch(statusUrl, {
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    }).then(function (response) {
      return response.json().catch(function () {
        return {
          authenticated: response.ok,
          session_valid: response.ok,
          login_url: loginUrl,
        };
      });
    }).then(function (payload) {
      if (!payload.authenticated || !payload.session_valid) {
        showInvalidatedSession(payload.login_url);
        return;
      }
      window.setTimeout(checkSession, pollInterval);
    }).catch(function () {
      window.setTimeout(checkSession, pollInterval);
    });
  }

  window.setTimeout(checkSession, pollInterval);
})();

/* Source: subject/js/subject_bulk_actions.js */
(function () {
  function initializeSubjectActionsDropdown(dropdown) {
    const trigger = dropdown.querySelector("[data-dropdown-trigger]");
    const menu = dropdown.querySelector("[data-dropdown-menu]");
    if (
      !(trigger instanceof HTMLButtonElement) ||
      !(menu instanceof HTMLElement)
    ) {
      return;
    }

    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = trigger.getAttribute("aria-expanded") === "true";
      trigger.setAttribute("aria-expanded", String(!isOpen));
      menu.hidden = isOpen;
    });
    menu.querySelectorAll("[data-dropdown-option]").forEach((option) => {
      option.addEventListener("click", () => {
        trigger.setAttribute("aria-expanded", "false");
        menu.hidden = true;
      });
    });
    document.addEventListener("click", (event) => {
      if (event.target instanceof Node && !dropdown.contains(event.target)) {
        trigger.setAttribute("aria-expanded", "false");
        menu.hidden = true;
      }
    });
  }

  function initializeSubjectListRowActions() {
    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const trigger = target.closest("[data-subject-actions-loader-trigger]");
      if (!(trigger instanceof HTMLButtonElement)) {
        return;
      }
      const loader = trigger.closest("[data-subject-actions-loader]");
      if (!(loader instanceof HTMLElement) || loader.dataset.loading === "true") {
        return;
      }

      const url = loader.dataset.subjectActionsUrl || "";
      if (!url) {
        return;
      }
      trigger.disabled = true;
      loader.dataset.loading = "true";
      window
        .fetch(url, {
          credentials: "same-origin",
          headers: {
            Accept: "text/html",
            "X-Requested-With": "XMLHttpRequest",
          },
        })
        .then((response) => {
          if (!response.ok) {
            throw new Error(
              `Subject actions request failed: ${response.status}`,
            );
          }
          return response.text();
        })
        .then((html) => {
          const template = document.createElement("template");
          template.innerHTML = html.trim();
          const dropdown = template.content.firstElementChild;
          if (!(dropdown instanceof HTMLElement)) {
            throw new Error("Subject actions response is empty");
          }
          loader.replaceWith(dropdown);
          initializeSubjectActionsDropdown(dropdown);
          const loadedTrigger = dropdown.querySelector(
            "[data-dropdown-trigger]",
          );
          const menu = dropdown.querySelector("[data-dropdown-menu]");
          if (loadedTrigger instanceof HTMLButtonElement) {
            loadedTrigger.setAttribute("aria-expanded", "true");
          }
          if (menu instanceof HTMLElement) {
            menu.hidden = false;
          }
        })
        .catch(() => {
          trigger.disabled = false;
          delete loader.dataset.loading;
        });
    });

    document.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        const element =
          target instanceof Element
            ? target
            : target && target.nodeType === 3
              ? target.parentElement
              : null;
        const navigation = element?.closest("[data-subject-verify-form-nav]");
        if (!(navigation instanceof HTMLElement)) {
          return;
        }
        const url = navigation.dataset.subjectVerifyFormNav || "";
        if (!url) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        window.location.assign(url);
      },
      true,
    );
  }

  initializeSubjectListRowActions();

  const actions = document.querySelector("[data-subject-bulk-actions]");
  if (!(actions instanceof HTMLElement)) {
    return;
  }

  const panel = actions.closest(".entity-table-panel");
  if (!(panel instanceof HTMLElement)) {
    return;
  }

  const rowCheckboxes = Array.from(
    panel.querySelectorAll("[data-row-checkbox]"),
  ).filter((checkbox) => checkbox instanceof HTMLInputElement);
  const count = actions.querySelector("[data-subject-selection-count]");
  const selectFiltered = actions.querySelector(
    "[data-subject-select-filtered]",
  );
  const actionSelect = actions.querySelector("[data-subject-action-select]");
  const actionInput = actions.querySelector("[data-subject-action-input]");
  const actionTrigger = actions.querySelector("[data-subject-action-trigger]");
  const executeButton = actions.querySelector("[data-subject-bulk-execute]");
  const actionForm = actions.querySelector("[data-subject-action-form]");
  const headerCell = panel.querySelector(
    ".entity-table thead .entity-table__select-column",
  );
  const filteredCount = Number(actions.dataset.subjectFilteredCount || 0);
  const filterQuery = actions.dataset.subjectFilterQuery || "";
  let selectAll = null;
  let allFilteredSelected = false;
  let syncingCheckboxes = false;

  function selectedCheckboxes() {
    return rowCheckboxes.filter((checkbox) => checkbox.checked);
  }

  function effectiveSelectedCount() {
    return allFilteredSelected ? filteredCount : selectedCheckboxes().length;
  }

  function updateExecuteButton() {
    const hasSelection = effectiveSelectedCount() > 0;
    if (actionTrigger instanceof HTMLButtonElement) {
      actionTrigger.disabled = !hasSelection;
    }
    if (!(executeButton instanceof HTMLButtonElement)) {
      return;
    }

    const selectedAction =
      actionInput instanceof HTMLInputElement ? actionInput.value : "";
    executeButton.disabled = !hasSelection || !selectedAction;
    if (selectedAction === "delete") {
      executeButton.dataset.modalOpen = "modal-subject-bulk-delete";
    } else if (selectedAction === "early_terminate") {
      executeButton.dataset.modalOpen = "modal-subject-bulk-early-termination";
    } else if (selectedAction === "export_excel") {
      executeButton.dataset.modalOpen = "modal-subject-export-excel";
    } else {
      delete executeButton.dataset.modalOpen;
    }
  }

  function updateState() {
    const selectedCount = selectedCheckboxes().length;
    const effectiveCount = effectiveSelectedCount();
    if (count) {
      count.textContent = String(effectiveCount);
    }
    if (selectFiltered instanceof HTMLButtonElement) {
      selectFiltered.hidden =
        effectiveCount === 0 ||
        (!allFilteredSelected && selectedCount >= filteredCount);
      selectFiltered.textContent = allFilteredSelected
        ? selectFiltered.dataset.clearAllLabel || "(bỏ chọn tất cả)"
        : selectFiltered.dataset.selectAllLabel ||
          `(chọn tất cả ${filteredCount} subject)`;
      selectFiltered.classList.toggle("is-active", allFilteredSelected);
    }
    updateExecuteButton();
    if (selectAll instanceof HTMLInputElement) {
      selectAll.checked =
        rowCheckboxes.length > 0 &&
        (allFilteredSelected || selectedCount === rowCheckboxes.length);
      selectAll.indeterminate =
        !allFilteredSelected &&
        selectedCount > 0 &&
        selectedCount < rowCheckboxes.length;
    }
  }

  function appendSelection(form) {
    form
      .querySelectorAll("[data-subject-bulk-selection]")
      .forEach((input) => input.remove());

    const selectionMode = document.createElement("input");
    selectionMode.type = "hidden";
    selectionMode.name = "selection_mode";
    selectionMode.value = allFilteredSelected ? "filtered" : "selected";
    selectionMode.dataset.subjectBulkSelection = "";
    form.appendChild(selectionMode);

    if (allFilteredSelected) {
      const queryInput = document.createElement("input");
      queryInput.type = "hidden";
      queryInput.name = "filter_query";
      queryInput.value = filterQuery;
      queryInput.dataset.subjectBulkSelection = "";
      form.appendChild(queryInput);
      return;
    }

    selectedCheckboxes().forEach((checkbox) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "subject_ids";
      input.value = checkbox.value;
      input.dataset.subjectBulkSelection = "";
      form.appendChild(input);
    });
  }

  function setPageCheckboxes(checked) {
    syncingCheckboxes = true;
    rowCheckboxes.forEach((checkbox) => {
      checkbox.checked = checked;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    });
    syncingCheckboxes = false;
  }

  if (headerCell instanceof HTMLTableCellElement) {
    selectAll = document.createElement("input");
    selectAll.type = "checkbox";
    selectAll.setAttribute("aria-label", "Select all subjects on this page");
    selectAll.dataset.subjectSelectAll = "";
    headerCell.appendChild(selectAll);
    selectAll.addEventListener("change", () => {
      allFilteredSelected = false;
      setPageCheckboxes(selectAll.checked);
      updateState();
    });
  }

  rowCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (!syncingCheckboxes) {
        allFilteredSelected = false;
      }
      updateState();
    });
  });

  if (selectFiltered instanceof HTMLButtonElement) {
    selectFiltered.addEventListener("click", () => {
      allFilteredSelected = !allFilteredSelected;
      setPageCheckboxes(allFilteredSelected);
      updateState();
    });
  }

  if (actionSelect instanceof HTMLElement) {
    actionSelect
      .querySelectorAll("[data-dropdown-option]")
      .forEach((option) => {
        option.addEventListener("click", updateExecuteButton);
      });
  }

  actions.querySelectorAll("[data-subject-bulk-form]").forEach((form) => {
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    form.addEventListener("submit", (event) => {
      if (!effectiveSelectedCount()) {
        event.preventDefault();
        updateState();
        return;
      }
      appendSelection(form);
    });
  });

  if (executeButton instanceof HTMLButtonElement) {
    executeButton.addEventListener("click", () => {
      if (
        executeButton.disabled ||
        !(actionInput instanceof HTMLInputElement)
      ) {
        return;
      }

      const selectedAction = actionInput.value;
      if (selectedAction === "delete") {
        const modalForm = actions.querySelector(
          "#modal-subject-bulk-delete [data-subject-bulk-form]",
        );
        if (modalForm instanceof HTMLFormElement) {
          appendSelection(modalForm);
        }
        return;
      }
      if (selectedAction === "early_terminate") {
        const modalForm = actions.querySelector(
          "#modal-subject-bulk-early-termination [data-subject-bulk-form]",
        );
        if (modalForm instanceof HTMLFormElement) {
          appendSelection(modalForm);
        }
        return;
      }
      if (selectedAction === "export_excel") {
        const modalForm = actions.querySelector(
          "#modal-subject-export-excel [data-subject-bulk-form]",
        );
        if (modalForm instanceof HTMLFormElement) {
          appendSelection(modalForm);
        }
        loadExportCatalog();
        return;
      }
      if (
        selectedAction === "resync_stage" &&
        actionForm instanceof HTMLFormElement
      ) {
        appendSelection(actionForm);
        actionForm.requestSubmit();
      }
    });
  }

  const exportForm = actions.querySelector("[data-subject-export-form]");
  const exportCatalog = actions.querySelector(
    "[data-subject-export-field-catalog]",
  );
  let exportCatalogPromise = null;

  function initializeExportCatalog() {
    if (!(exportForm instanceof HTMLFormElement)) {
      return;
    }
    const exportVisits = Array.from(
      exportForm.querySelectorAll("[data-subject-export-visit]"),
    ).filter((visit) => visit instanceof HTMLElement);
    const exportFields = Array.from(
      exportForm.querySelectorAll("[data-subject-export-field]"),
    ).filter((field) => field instanceof HTMLInputElement);
    const fieldsForVisit = (visit) =>
      Array.from(visit.querySelectorAll("[data-subject-export-field]")).filter(
        (field) => field instanceof HTMLInputElement,
      );
    const setVisitExpanded = (visit, expanded) => {
      const collapse = visit.querySelector(
        "[data-subject-export-visit-collapse]",
      );
      const fieldGrid = visit.querySelector(
        ".subject-export-modal__field-grid",
      );
      if (
        !(collapse instanceof HTMLButtonElement) ||
        !(fieldGrid instanceof HTMLElement)
      ) {
        return;
      }
      collapse.setAttribute("aria-expanded", String(expanded));
      collapse.setAttribute(
        "aria-label",
        expanded
          ? collapse.dataset.expandedLabel || "Thu gọn Visit"
          : collapse.dataset.collapsedLabel || "Mở rộng Visit",
      );
      fieldGrid.hidden = !expanded;
      visit.classList.toggle("is-collapsed", !expanded);
    };
    const updateExportState = () => {
      const exportSubmit = exportForm.querySelector(
        "[data-subject-export-submit]",
      );
      if (exportSubmit instanceof HTMLButtonElement) {
        exportSubmit.disabled = !exportFields.some((field) => field.checked);
      }
      exportVisits.forEach((visit) => {
        const visitFields = fieldsForVisit(visit);
        const toggle = visit.querySelector(
          "[data-subject-export-visit-toggle]",
        );
        if (!(toggle instanceof HTMLButtonElement)) {
          return;
        }
        const allChecked =
          visitFields.length > 0 && visitFields.every((field) => field.checked);
        toggle.disabled = visitFields.length === 0;
        toggle.setAttribute("aria-pressed", String(allChecked));
        toggle.textContent = allChecked
          ? toggle.dataset.clearLabel || "Bỏ chọn toàn bộ field"
          : toggle.dataset.selectLabel || "Chọn toàn bộ field";
      });
    };
    exportFields.forEach((field) => {
      field.addEventListener("change", updateExportState);
    });
    exportVisits.forEach((visit) => {
      const toggle = visit.querySelector("[data-subject-export-visit-toggle]");
      if (toggle instanceof HTMLButtonElement) {
        toggle.addEventListener("click", () => {
          const visitFields = fieldsForVisit(visit);
          const shouldCheck = !visitFields.every((field) => field.checked);
          visitFields.forEach((field) => {
            field.checked = shouldCheck;
          });
          updateExportState();
        });
      }
      const collapse = visit.querySelector(
        "[data-subject-export-visit-collapse]",
      );
      if (collapse instanceof HTMLButtonElement) {
        collapse.addEventListener("click", () => {
          const isExpanded = collapse.getAttribute("aria-expanded") === "true";
          setVisitExpanded(visit, !isExpanded);
        });
      }
    });
    updateExportState();
  }

  function loadExportCatalog() {
    if (
      !(exportCatalog instanceof HTMLElement) ||
      exportCatalog.dataset.subjectExportFieldCatalogLoaded === "true"
    ) {
      return Promise.resolve();
    }
    if (exportCatalogPromise) {
      return exportCatalogPromise;
    }

    const url = exportCatalog.dataset.subjectExportFieldCatalogUrl || "";
    const loading = exportCatalog.querySelector(
      "[data-subject-export-field-loading]",
    );
    const error = exportCatalog.querySelector(
      "[data-subject-export-field-error]",
    );
    const groups = exportCatalog.querySelector(
      "[data-subject-export-field-groups]",
    );
    if (!url || !(groups instanceof HTMLElement)) {
      return Promise.resolve();
    }

    if (loading instanceof HTMLElement) {
      loading.hidden = false;
    }
    if (error instanceof HTMLElement) {
      error.hidden = true;
    }
    exportCatalogPromise = window
      .fetch(url, {
        credentials: "same-origin",
        headers: {
          Accept: "text/html",
          "X-Requested-With": "XMLHttpRequest",
        },
      })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Export field catalog request failed: ${response.status}`);
        }
        return response.text();
      })
      .then((html) => {
        groups.innerHTML = html;
        exportCatalog.dataset.subjectExportFieldCatalogLoaded = "true";
        initializeExportCatalog();
      })
      .catch(() => {
        if (error instanceof HTMLElement) {
          error.hidden = false;
        }
      })
      .finally(() => {
        if (loading instanceof HTMLElement) {
          loading.hidden = true;
        }
        exportCatalogPromise = null;
      });
    return exportCatalogPromise;
  }

  if (exportForm instanceof HTMLFormElement) {
    exportForm.addEventListener("submit", (event) => {
      const exportFields = Array.from(
        exportForm.querySelectorAll("[data-subject-export-field]"),
      ).filter((field) => field instanceof HTMLInputElement);
      if (!exportFields.some((field) => field.checked)) {
        event.preventDefault();
        return;
      }
      const modal = document.getElementById("modal-subject-export-excel");
      modal?.classList.remove("is-open");
    });
  }

  updateState();
})();
