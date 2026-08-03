(function () {
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
  if (exportForm instanceof HTMLFormElement) {
    const exportFields = Array.from(
      exportForm.querySelectorAll("[data-subject-export-field]"),
    ).filter((field) => field instanceof HTMLInputElement);
    const exportSubmit = exportForm.querySelector(
      "[data-subject-export-submit]",
    );
    const exportVisits = Array.from(
      exportForm.querySelectorAll("[data-subject-export-visit]"),
    ).filter((visit) => visit instanceof HTMLElement);
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
    exportForm.addEventListener("submit", (event) => {
      if (!exportFields.some((field) => field.checked)) {
        event.preventDefault();
        updateExportState();
        return;
      }
      const modal = document.getElementById("modal-subject-export-excel");
      modal?.classList.remove("is-open");
    });
    updateExportState();
  }

  updateState();
})();
