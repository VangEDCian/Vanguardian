(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  function pad2(value) {
    return String(value ?? '').padStart(2, '0');
  }

  function buildDateValue({ day, month, year }) {
    const normalizedDay = String(day || '').trim();
    const normalizedMonth = String(month || '').trim();
    const normalizedYear = String(year || '').trim();
    if (!normalizedDay || !normalizedMonth || !normalizedYear) {
      return '';
    }
    return `${normalizedYear}-${pad2(normalizedMonth)}-${pad2(normalizedDay)}`;
  }

  function syncDateCompositeInput(container) {
    if (!container) {
      return;
    }
    const hiddenInput = container.querySelector('input[type="hidden"][data-date-composite-input][data-date-composite-type="date"]');
    if (!hiddenInput) {
      return;
    }
    const day = container.querySelector('.subject-date-picker__input--day')?.value || '';
    const month = container.querySelector('.subject-date-picker__input--month')?.value || '';
    const year = container.querySelector('.subject-date-picker__input--year')?.value || '';
    hiddenInput.value = buildDateValue({ day, month, year });
  }

  function applyDateCompositeValue(container, compositeValue) {
    if (!container) {
      return;
    }
    const normalized = String(compositeValue || '').trim();
    const matched = normalized.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    const dayInput = container.querySelector('.subject-date-picker__input--day');
    const monthInput = container.querySelector('.subject-date-picker__input--month');
    const yearInput = container.querySelector('.subject-date-picker__input--year');
    if (!dayInput || !monthInput || !yearInput) {
      return;
    }
    if (!matched) {
      dayInput.value = '';
      monthInput.value = '';
      yearInput.value = '';
      return;
    }
    yearInput.value = matched[1];
    monthInput.value = String(Number.parseInt(matched[2], 10) || '');
    dayInput.value = String(Number.parseInt(matched[3], 10) || '');
  }

  window.DatacaptureSubjectDetailModules.controls.datePicker = {
    syncDateCompositeInput,
    applyDateCompositeValue,
  };
})();
