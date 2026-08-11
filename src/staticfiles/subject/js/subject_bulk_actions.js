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

    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "subject_ids";
    input.value = JSON.stringify(
      selectedCheckboxes().map((checkbox) => checkbox.value),
    );
    input.dataset.subjectBulkSelection = "";
    form.appendChild(input);
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

  function resetExportControls() {
    if (!(exportForm instanceof HTMLFormElement)) {
      return;
    }
    const exportFields = Array.from(
      exportForm.querySelectorAll("[data-subject-export-field]"),
    ).filter((field) => field instanceof HTMLInputElement);
    exportFields.forEach((field) => {
      field.disabled = false;
    });
    const exportSubmit = exportForm.querySelector(
      "[data-subject-export-submit]",
    );
    if (exportSubmit instanceof HTMLButtonElement) {
      exportSubmit.disabled = !exportFields.some((field) => field.checked);
    }
  }

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
    resetExportControls();
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
    if (!(exportCatalog instanceof HTMLElement)) {
      return Promise.resolve();
    }
    if (exportCatalog.dataset.subjectExportFieldCatalogLoaded === "true") {
      resetExportControls();
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
      const selectedExportFields = exportFields.filter((field) => field.checked);
      if (!selectedExportFields.length) {
        event.preventDefault();
        return;
      }

      const exportSubmit = exportForm.querySelector(
        "[data-subject-export-submit]",
      );
      if (exportSubmit instanceof HTMLButtonElement) {
        exportSubmit.disabled = true;
      }
      exportFields.forEach((field) => {
        field.disabled = true;
      });
      window.setTimeout(resetExportControls, 0);

      const existingPayloadInput = exportForm.querySelector(
        "[name='export_fields'][data-subject-export-field-payload]",
      );
      if (existingPayloadInput instanceof HTMLInputElement) {
        existingPayloadInput.remove();
      }

      const payloadInput = document.createElement("input");
      payloadInput.type = "hidden";
      payloadInput.name = "export_fields";
      payloadInput.value = JSON.stringify(
        selectedExportFields.map((field) => field.value),
      );
      payloadInput.dataset.subjectExportFieldPayload = "1";
      exportForm.appendChild(payloadInput);

      const modal = document.getElementById("modal-subject-export-excel");
      modal?.classList.remove("is-open");
    });
  }

  updateState();
})();
