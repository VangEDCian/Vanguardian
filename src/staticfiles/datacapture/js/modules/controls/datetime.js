(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  function pad2(value) {
    return String(value ?? '').padStart(2, '0');
  }

  function normalizeTime(rawTime) {
    const normalized = String(rawTime || '').trim();
    if (!normalized) {
      return '';
    }
    const parts = normalized.split(':');
    if (parts.length !== 2) {
      return '';
    }
    const hour = parts[0].trim();
    const minute = parts[1].trim();
    if (!hour || !minute) {
      return '';
    }
    return `${pad2(hour)}:${pad2(minute)}`;
  }

  function buildDatetimeValue({ day, month, year, time }) {
    const normalizedDay = String(day || '').trim();
    const normalizedMonth = String(month || '').trim();
    const normalizedYear = String(year || '').trim();
    const normalizedTime = normalizeTime(time);
    if (!normalizedDay || !normalizedMonth || !normalizedYear || !normalizedTime) {
      return '';
    }
    return `${normalizedYear}-${pad2(normalizedMonth)}-${pad2(normalizedDay)} ${normalizedTime}:00`;
  }

  function syncDatetimeCompositeInput(container) {
    if (!container) {
      return;
    }
    const hiddenInput = container.querySelector('input[type="hidden"][data-date-composite-input][data-date-composite-type="datetime"]');
    if (!hiddenInput) {
      return;
    }
    const day = container.querySelector('.subject-date-picker__input--day')?.value || '';
    const month = container.querySelector('.subject-date-picker__input--month')?.value || '';
    const year = container.querySelector('.subject-date-picker__input--year')?.value || '';
    const time = container.querySelector('.subject-date-picker__input--time')?.value || '';
    hiddenInput.value = buildDatetimeValue({ day, month, year, time });
  }

  function applyDatetimeCompositeValue(container, compositeValue) {
    if (!container) {
      return;
    }
    const normalized = String(compositeValue || '').trim();
    const matched = normalized.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::\d{2})?$/);
    const dayInput = container.querySelector('.subject-date-picker__input--day');
    const monthInput = container.querySelector('.subject-date-picker__input--month');
    const yearInput = container.querySelector('.subject-date-picker__input--year');
    const timeInput = container.querySelector('.subject-date-picker__input--time');
    if (!dayInput || !monthInput || !yearInput || !timeInput) {
      return;
    }
    if (!matched) {
      dayInput.value = '';
      monthInput.value = '';
      yearInput.value = '';
      timeInput.value = '';
      return;
    }
    yearInput.value = matched[1];
    monthInput.value = String(Number.parseInt(matched[2], 10) || '');
    dayInput.value = String(Number.parseInt(matched[3], 10) || '');
    timeInput.value = `${matched[4]}:${matched[5]}`;
  }

  window.DatacaptureSubjectDetailModules.controls.datetime = {
    syncDatetimeCompositeInput,
    applyDatetimeCompositeValue,
  };
})();
