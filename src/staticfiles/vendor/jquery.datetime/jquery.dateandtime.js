/*
 * Plugin date & time
 * ------------------
 *
 * Manage date/time text inputs and canonical hidden values.
 */
(function (root, factory) {
  const api = factory(root.jQuery);
  root.VanguardianDateAndTime = api;
  if (root.jQuery) {
    root.jQuery.fn.dateAndTime = function dateAndTime() {
      return this.each(function eachDateAndTimeElement() {
        api.initialize(this);
      });
    };
  }
}(window, function createDateAndTimeApi($) {
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
    if (Number.parseInt(secondCandidate, 10) > secondMax) {
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
    const parts = { day: '', month: '', year: '', overflow: '' };
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

  function parseTimeText(rawValue) {
    return { time: formatTimeDigits(rawValue) };
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
    if (kind === 'time') {
      return isValidTime(parts.time) ? parts.time : '';
    }
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

  function displayValueForParts(parts, kind, locale) {
    if (kind === 'time') {
      return parts.time || '';
    }
    if (kind === 'datetime') {
      return formatDatetimeDisplay(parts, locale);
    }
    return formatDateDisplay(parts, locale);
  }

  function parseInputValue(input) {
    const kind = String(input?.dataset.dateandtimeKind || input?.dataset.dateTextKind || 'date')
      .trim()
      .toLowerCase();
    const locale = input?.dataset.dateandtimeLocale || input?.dataset.dateTextLocale || 'en';
    const parts = kind === 'datetime'
      ? parseDatetimeText(input.value, locale)
      : kind === 'time'
        ? parseTimeText(input.value)
        : parseDateText(input.value, locale);
    return {
      kind,
      locale,
      parts,
      displayValue: displayValueForParts(parts, kind, locale),
      canonicalValue: buildCanonicalValue(parts, kind),
    };
  }

  function findContainer(node) {
    return node?.closest?.('[data-field-key]') || node?.closest?.('.subject-date-text') || null;
  }

  function findHiddenInput(container) {
    return container?.querySelector?.('input[type="hidden"][data-date-text-composite-input]') ||
      container?.querySelector?.('input[type="hidden"][data-dateandtime-hidden]') ||
      null;
  }

  function findNativeControl(node) {
    return node?.matches?.('[data-dateandtime-control]')
      ? node
      : node?.closest?.('[data-dateandtime-control]') || null;
  }

  function nativeControlKind(control) {
    return String(control?.dataset.dateandtimeKind || 'date').trim().toLowerCase();
  }

  function nativeControlParts(control) {
    return {
      day: '',
      month: '',
      year: '',
      time: control?.querySelector?.('[data-dateandtime-time]')?.value || '',
    };
  }

  function nativeDateParts(control) {
    const rawDate = String(control?.querySelector?.('[data-dateandtime-date]')?.value || '').trim();
    const matched = rawDate.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!matched) {
      return nativeControlParts(control);
    }
    return {
      year: matched[1],
      month: matched[2],
      day: matched[3],
      time: control?.querySelector?.('[data-dateandtime-time]')?.value || '',
    };
  }

  function syncInput(input) {
    if (!input) {
      return { kind: 'date', locale: 'en', parts: {}, displayValue: '', canonicalValue: '' };
    }
    const nativeControl = findNativeControl(input);
    if (nativeControl) {
      return syncControl(nativeControl);
    }
    const result = parseInputValue(input);
    input.value = result.displayValue;
    const hiddenInput = findHiddenInput(findContainer(input));
    if (hiddenInput) {
      hiddenInput.value = result.canonicalValue;
    }
    return result;
  }

  function partsFromCanonicalValue(rawValue, kind) {
    const normalized = String(rawValue || '').trim();
    if (kind === 'time') {
      return { day: '', month: '', year: '', time: formatTimeDigits(normalized) };
    }
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

  function applyCanonicalValue(container, compositeValue) {
    const nativeControl = findNativeControl(container);
    if (nativeControl) {
      const kind = nativeControlKind(nativeControl);
      const parts = partsFromCanonicalValue(compositeValue, kind);
      const dateInput = nativeControl.querySelector('[data-dateandtime-date]');
      const timeInput = nativeControl.querySelector('[data-dateandtime-time]');
      if (dateInput) {
        dateInput.value = parts.year && parts.month && parts.day
          ? `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)}`
          : '';
      }
      if (timeInput) {
        timeInput.value = parts.time || '';
      }
      syncControl(nativeControl);
      return;
    }
    const input = container?.querySelector?.('[data-dateandtime-input]') || null;
    if (!input) {
      return;
    }
    const hiddenInput = findHiddenInput(container);
    const kind = String(input.dataset.dateandtimeKind || hiddenInput?.dataset.dateTextKind || 'date')
      .trim()
      .toLowerCase();
    const locale = input.dataset.dateandtimeLocale || input.dataset.dateTextLocale || 'en';
    const parts = partsFromCanonicalValue(compositeValue, kind);
    input.value = displayValueForParts(parts, kind, locale);
    if (hiddenInput) {
      hiddenInput.value = buildCanonicalValue(parts, kind);
    }
  }

  function validateInput(input) {
    if (!input || input.disabled) {
      return { ok: true, message: '', focusEl: null };
    }
    const nativeControl = findNativeControl(input);
    if (nativeControl) {
      return validateControl(nativeControl);
    }
    const { canonicalValue } = syncInput(input);
    const rawValue = String(input.value || '').trim();
    if (!rawValue && !input.required) {
      return { ok: true, message: '', focusEl: null };
    }
    if (!input.checkValidity() || !canonicalValue) {
      const fieldLabel = input.dataset.fieldLabel || input.name || 'DateTime';
      return {
        ok: false,
        message: `${fieldLabel} is not a valid DateTime value.`,
        focusEl: input,
      };
    }
    return { ok: true, message: '', focusEl: null };
  }

  function syncControl(control) {
    const kind = nativeControlKind(control);
    const parts = kind === 'time' ? nativeControlParts(control) : nativeDateParts(control);
    const canonicalValue = buildCanonicalValue(parts, kind);
    const hiddenInput = findHiddenInput(control);
    if (hiddenInput) {
      hiddenInput.value = canonicalValue;
    }
    return {
      kind,
      locale: control?.dataset.dateandtimeLocale || 'en',
      parts,
      displayValue: '',
      canonicalValue,
    };
  }

  function validateControl(control) {
    const controls = Array.from(control?.querySelectorAll?.('[data-dateandtime-input]') || []);
    for (const input of controls) {
      if (input.disabled) {
        continue;
      }
      if (!input.checkValidity()) {
        const fieldLabel = input.dataset.fieldLabel || input.name || 'DateTime';
        return {
          ok: false,
          message: `${fieldLabel} is not a valid DateTime value.`,
          focusEl: input,
        };
      }
    }
    const { canonicalValue } = syncControl(control);
    const hasValue = controls.some((input) => String(input.value || '').trim());
    const isRequired = controls.some((input) => input.required);
    if ((hasValue || isRequired) && !canonicalValue) {
      const focusEl = controls.find((input) => !input.disabled) || null;
      const fieldLabel = focusEl?.dataset.fieldLabel || focusEl?.name || 'DateTime';
      return {
        ok: false,
        message: `${fieldLabel} is not a valid DateTime value.`,
        focusEl,
      };
    }
    return { ok: true, message: '', focusEl: null };
  }

  function initialize(root = document) {
    const scope = root?.querySelectorAll ? root : document;
    const controls = root?.matches?.('[data-dateandtime-control]')
      ? [root]
      : Array.from(scope.querySelectorAll('[data-dateandtime-control]'));
    controls.forEach((control) => {
      if (control.dataset.dateandtimeBound === '1') {
        return;
      }
      control.dataset.dateandtimeBound = '1';
      const hiddenInput = findHiddenInput(control);
      if (hiddenInput?.value) {
        applyCanonicalValue(control, hiddenInput.value);
      } else {
        syncControl(control);
      }
      control.querySelectorAll('[data-dateandtime-input]').forEach((input) => {
        input.addEventListener('input', () => syncControl(control));
        input.addEventListener('change', () => syncControl(control));
      });
    });

    const nodes = root?.matches?.('[data-dateandtime-input]') && !findNativeControl(root)
      ? [root]
      : Array.from(scope.querySelectorAll('[data-dateandtime-input]')).filter((input) => !findNativeControl(input));
    nodes.forEach((input) => {
      if (input.dataset.dateandtimeBound === '1') {
        return;
      }
      input.dataset.dateandtimeBound = '1';
      syncInput(input);
      input.addEventListener('input', () => {
        syncInput(input);
      });
    });
  }

  function initializeWhenReady() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => initialize(), { once: true });
      return;
    }
    initialize();
  }

  initializeWhenReady();

  return {
    applyCanonicalValue,
    buildCanonicalValue,
    displayValueForParts,
    formatDateDisplay,
    formatDatetimeDisplay,
    initialize,
    isValidDate,
    isValidTime,
    parseDateText,
    parseDatetimeText,
    parseInputValue,
    parseTimeText,
    syncControl,
    syncInput,
    validateControl,
    validateInput,
  };
}));
