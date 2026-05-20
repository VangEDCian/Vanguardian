(function () {
  const filter = document.querySelector('[data-verification-item-filter]');
  if (!(filter instanceof HTMLElement)) {
    return;
  }

  const root = filter.closest('.subject-form-verification-review');
  if (!(root instanceof HTMLElement)) {
    return;
  }

  const rows = Array.from(root.querySelectorAll('tr[data-field-template-id]'));
  const emptyRow = root.querySelector('[data-verification-filter-empty]');

  function selectedMode() {
    const checked = filter.querySelector('input[name="verification_item_filter"]:checked');
    return checked instanceof HTMLInputElement ? checked.value : 'needs_verification';
  }

  function applyFilter() {
    const shouldShowAll = selectedMode() === 'all';
    let visibleCount = 0;

    rows.forEach(function (row) {
      const isVerified = row.dataset.fieldVerified === 'true';
      const shouldHide = !shouldShowAll && isVerified;
      row.hidden = shouldHide;
      if (!shouldHide) {
        visibleCount += 1;
      }
    });

    if (emptyRow instanceof HTMLElement) {
      emptyRow.hidden = shouldShowAll || visibleCount > 0 || rows.length === 0;
    }
  }

  filter.addEventListener('change', applyFilter);
  root.addEventListener('verification:items-updated', applyFilter);
  applyFilter();
})();
