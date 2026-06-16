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
    const explicitHref =
      row.getAttribute("data-detail-href") || row.dataset.detailHref || "";
    if (explicitHref) {
      return explicitHref;
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
