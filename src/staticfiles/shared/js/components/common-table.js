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
    const rows = Array.from(table.querySelectorAll("[data-selectable-row]"));

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
        const target = event.target;
        if (!(target instanceof Element)) {
          return;
        }

        if (isInteractiveTarget(target)) {
          return;
        }

        checkbox.checked = !checkbox.checked;
        syncRowSelection(row, checkbox);
      });
    });
  });
})();
