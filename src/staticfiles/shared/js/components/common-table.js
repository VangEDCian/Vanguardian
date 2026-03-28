(function () {
  const tables = Array.from(document.querySelectorAll("[data-common-table]"));
  if (!tables.length) {
    return;
  }

  function syncRowSelection(row, checkbox) {
    row.classList.toggle("is-selected", checkbox.checked);
  }

  function isInteractiveTarget(target) {
    return Boolean(
      target.closest("a, button, input, label, select, textarea")
    );
  }

  tables.forEach((table) => {
    const enableDetailClick = table.dataset.enableDetailClick === "true";
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

      const detailHref = row.dataset.detailHref || "";

      syncRowSelection(row, checkbox);

      checkbox.addEventListener("change", () => {
        syncRowSelection(row, checkbox);
      });

      row.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
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

        if (enableDetailClick && detailHref) {
          window.location.href = detailHref;
        }
      });
    });
  });
})();
