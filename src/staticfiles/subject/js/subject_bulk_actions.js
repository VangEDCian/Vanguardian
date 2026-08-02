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
  const actionButtons = Array.from(
    actions.querySelectorAll("[data-subject-bulk-submit]"),
  );
  const count = actions.querySelector("[data-subject-selection-count]");
  const headerCell = panel.querySelector(
    ".entity-table thead .entity-table__select-column",
  );
  let selectAll = null;

  function selectedCheckboxes() {
    return rowCheckboxes.filter((checkbox) => checkbox.checked);
  }

  function updateState() {
    const selectedCount = selectedCheckboxes().length;
    if (count) {
      count.textContent = String(selectedCount);
    }
    actionButtons.forEach((button) => {
      if (button instanceof HTMLButtonElement) {
        button.disabled = selectedCount === 0;
      }
    });
    if (selectAll instanceof HTMLInputElement) {
      selectAll.checked = rowCheckboxes.length > 0 && selectedCount === rowCheckboxes.length;
      selectAll.indeterminate = selectedCount > 0 && selectedCount < rowCheckboxes.length;
    }
  }

  function appendSelectedIds(form) {
    form.querySelectorAll("[data-subject-bulk-id]").forEach((input) => input.remove());
    selectedCheckboxes().forEach((checkbox) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "subject_ids";
      input.value = checkbox.value;
      input.dataset.subjectBulkId = "";
      form.appendChild(input);
    });
  }

  if (headerCell instanceof HTMLTableCellElement) {
    selectAll = document.createElement("input");
    selectAll.type = "checkbox";
    selectAll.setAttribute("aria-label", "Select all subjects on this page");
    selectAll.dataset.subjectSelectAll = "";
    headerCell.appendChild(selectAll);
    selectAll.addEventListener("change", () => {
      rowCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      });
      updateState();
    });
  }

  rowCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", updateState);
  });

  actions.querySelectorAll("[data-subject-bulk-form]").forEach((form) => {
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    form.addEventListener("submit", (event) => {
      if (!selectedCheckboxes().length) {
        event.preventDefault();
        updateState();
        return;
      }
      appendSelectedIds(form);
    });
  });

  updateState();
})();
