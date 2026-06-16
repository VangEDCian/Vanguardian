(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};

  function pad2(value) {
    return String(value ?? '').padStart(2, '0');
  }

  function dateOrder(locale) {
    return String(locale || '').toLowerCase().startsWith('vi')
      ? ['day', 'month', 'year']
      : ['month', 'day', 'year'];
  }

  function parseDateDigits(rawValue, locale) {
    const digits = String(rawValue || '').replace(/\D/g, '').slice(0, 8);
    const order = dateOrder(locale);
    const firstKey = order[0];
    const secondKey = order[1];
    const secondMax = secondKey === 'month' ? 12 : 31;
    const parts = { day: '', month: '', year: '', consumed: 0 };

    if (digits.length <= 2) {
      parts[firstKey] = digits;
      parts.consumed = digits.length;
      return parts;
    }

    parts[firstKey] = digits.slice(0, 2);
    const remainder = digits.slice(2);
    if (remainder.length === 1) {
      parts[secondKey] = remainder;
      parts.consumed = digits.length;
      return parts;
    }

    const secondCandidate = remainder.slice(0, 2);
    const secondCandidateInt = Number.parseInt(secondCandidate, 10);
    if (secondCandidateInt > secondMax) {
      parts[secondKey] = pad2(remainder.slice(0, 1));
      parts.year = remainder.slice(1, 5);
      parts.consumed = 3 + parts.year.length;
      return parts;
    }

    parts[secondKey] = secondCandidate;
    parts.year = remainder.slice(2, 6);
    parts.consumed = 4 + parts.year.length;
    return parts;
  }

  function parseDateText(rawValue, locale) {
    const normalized = String(rawValue || '').trim();
    if (!normalized.includes('/')) {
      return parseDateDigits(normalized, locale);
    }

    const order = dateOrder(locale);
    const firstKey = order[0];
    const secondKey = order[1];
    const secondMax = secondKey === 'month' ? 12 : 31;
    const groups = normalized.split('/').map((part) => part.replace(/\D/g, ''));
    const parts = { day: '', month: '', year: '', consumed: 0, overflow: '' };
    parts[firstKey] = (groups[0] || '').slice(0, 2);
    const secondRaw = groups[1] || '';
    const explicitYearRaw = groups[2] || '';
    let second = secondRaw.slice(0, 2);
    let yearSource = explicitYearRaw || secondRaw.slice(2);

    if (second === '0' && !yearSource) {
      second = '';
    } else if (
      second.length === 2 &&
      !explicitYearRaw &&
      Number.parseInt(second, 10) > secondMax
    ) {
      yearSource = `${second.slice(1)}${secondRaw.slice(2)}`;
      second = pad2(second.slice(0, 1));
    } else if (second.length === 1 && yearSource) {
      second = pad2(second);
    }

    parts[secondKey] = second;
    parts.year = yearSource.slice(0, 4);
    parts.overflow = yearSource.slice(4);
    return parts;
  }

  function formatDateDisplay(parts, locale) {
    const order = dateOrder(locale);
    const first = parts[order[0]] || '';
    const second = parts[order[1]] || '';
    const year = parts.year || '';
    if (!first) {
      return '';
    }
    if (!second) {
      return first;
    }
    if (!year) {
      return `${first}/${second}`;
    }
    return `${first}/${second}/${year}`;
  }

  function formatTimeDigits(rawValue) {
    const digits = String(rawValue || '').replace(/\D/g, '').slice(0, 4);
    if (digits.length <= 2) {
      return digits;
    }
    return `${digits.slice(0, 2)}:${digits.slice(2)}`;
  }

  function parseDatetimeText(rawValue, locale) {
    const normalized = String(rawValue || '').trim();
    if (!normalized.includes('/')) {
      const digits = normalized.replace(/\D/g, '').slice(0, 12);
      const dateParts = parseDateDigits(digits, locale);
      const hasFullDate =
        dateParts.day && dateParts.month && String(dateParts.year || '').length === 4;
      const timeDigits = hasFullDate
        ? digits.slice(dateParts.consumed, dateParts.consumed + 4)
        : '';
      return {
        ...dateParts,
        time: formatTimeDigits(timeDigits),
      };
    }

    const [dateText, timeText = ''] = normalized.split(/\s+/, 2);
    const dateParts = parseDateText(dateText, locale);
    const hasFullDate =
      dateParts.day && dateParts.month && String(dateParts.year || '').length === 4;
    const timeSource = `${dateParts.overflow || ''}${timeText}`;
    return {
      ...dateParts,
      time: hasFullDate ? formatTimeDigits(timeSource) : '',
    };
  }

  function formatDatetimeDisplay(parts, locale) {
    const dateDisplay = formatDateDisplay(parts, locale);
    if (!dateDisplay || !parts.time) {
      return dateDisplay;
    }
    return `${dateDisplay} ${parts.time}`;
  }

  function isValidDate(parts) {
    if (!parts.day || !parts.month || !/^\d{4}$/.test(String(parts.year || ''))) {
      return false;
    }
    const day = Number.parseInt(parts.day, 10);
    const month = Number.parseInt(parts.month, 10);
    const year = Number.parseInt(parts.year, 10);
    const composed = new Date(year, month - 1, day);
    return (
      composed.getFullYear() === year &&
      composed.getMonth() === month - 1 &&
      composed.getDate() === day
    );
  }

  function isValidTime(time) {
    return /^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/.test(String(time || ''));
  }

  function buildCanonicalValue(parts, kind) {
    if (!isValidDate(parts)) {
      return '';
    }
    const dateValue = `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)}`;
    if (kind !== 'datetime') {
      return dateValue;
    }
    if (!isValidTime(parts.time)) {
      return '';
    }
    return `${dateValue} ${parts.time}:00`;
  }

  function findFieldContainer(node) {
    return node?.closest?.('[data-field-key]') || node?.closest?.('.subject-date-text') || null;
  }

  function findDateTextInput(container) {
    return container?.querySelector?.('[data-date-text-input]') || null;
  }

  function findDateTextHiddenInput(container) {
    return container?.querySelector?.('input[type="hidden"][data-date-text-composite-input]') || null;
  }

  function partsForInput(input) {
    const kind = String(input?.dataset.dateTextKind || 'date').trim().toLowerCase();
    const locale = input?.dataset.dateTextLocale || 'en';
    const parts = kind === 'datetime'
      ? parseDatetimeText(input.value, locale)
      : parseDateText(input.value, locale);
    const displayValue = kind === 'datetime'
      ? formatDatetimeDisplay(parts, locale)
      : formatDateDisplay(parts, locale);
    return { kind, locale, parts, displayValue };
  }

  function syncDateTextInput(container) {
    const input = findDateTextInput(container);
    const hiddenInput = findDateTextHiddenInput(container);
    if (!input || !hiddenInput) {
      return;
    }
    const { kind, parts, displayValue } = partsForInput(input);
    input.value = displayValue;
    hiddenInput.value = buildCanonicalValue(parts, kind);
  }

  function partsFromCanonicalValue(rawValue, kind) {
    const normalized = String(rawValue || '').trim();
    const pattern = kind === 'datetime'
      ? /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::\d{2})?$/
      : /^(\d{4})-(\d{2})-(\d{2})$/;
    const matched = normalized.match(pattern);
    if (!matched) {
      return { day: '', month: '', year: '', time: '' };
    }
    return {
      year: matched[1],
      month: String(Number.parseInt(matched[2], 10) || ''),
      day: String(Number.parseInt(matched[3], 10) || ''),
      time: kind === 'datetime' ? `${matched[4]}:${matched[5]}` : '',
    };
  }

  function applyDateTextCompositeValue(container, compositeValue) {
    const input = findDateTextInput(container);
    const hiddenInput = findDateTextHiddenInput(container);
    if (!input || !hiddenInput) {
      return;
    }
    const kind = String(hiddenInput.dataset.dateTextKind || input.dataset.dateTextKind || 'date')
      .trim()
      .toLowerCase();
    const locale = input.dataset.dateTextLocale || 'en';
    const parts = partsFromCanonicalValue(compositeValue, kind);
    input.value = kind === 'datetime'
      ? formatDatetimeDisplay(parts, locale)
      : formatDateDisplay(parts, locale);
    hiddenInput.value = buildCanonicalValue(parts, kind);
  }

  function validateDateTextInput(container) {
    const input = findDateTextInput(container);
    const hiddenInput = findDateTextHiddenInput(container);
    if (!input || !hiddenInput || input.disabled) {
      return { ok: true, message: '', focusEl: null };
    }
    syncDateTextInput(container);
    const rawValue = String(input.value || '').trim();
    if (!rawValue && !input.required) {
      return { ok: true, message: '', focusEl: null };
    }
    if (!input.checkValidity() || !hiddenInput.value) {
      const fieldLabel = input.dataset.fieldLabel || container.dataset.fieldKey || 'DateTime';
      return {
        ok: false,
        message: `${fieldLabel} is not a valid DateTime value.`,
        focusEl: input,
      };
    }
    return { ok: true, message: '', focusEl: null };
  }

  function initializeDateTextControls(root = document) {
    window.VanguardianDateAndTime?.initialize?.(root);
    root.querySelectorAll('[data-date-text-input]').forEach((input) => {
      if (input.dataset.dateTextBound === '1') {
        return;
      }
      input.dataset.dateTextBound = '1';
      const container = findFieldContainer(input);
      syncDateTextInput(container);
      input.addEventListener('input', () => {
        syncDateTextInput(container);
      });
    });
  }

  initializeDateTextControls();

  window.DatacaptureSubjectDetailModules.controls.dateText = {
    applyDateTextCompositeValue,
    initializeDateTextControls,
    syncDateTextInput,
    validateDateTextInput,
  };
})();
