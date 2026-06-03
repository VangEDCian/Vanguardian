(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};
  const numberControlSelector = 'input[data-submitted-diff-input][data-submitted-diff-control="number"]';
  const boundNumberInputs = new WeakSet();

  function parseNumericValue(rawValue) {
    const normalized = String(rawValue ?? '').trim().replace(',', '.');
    if (!normalized || ['-', '.', ',', '-.', '-,'].includes(normalized)) {
      return null;
    }
    if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) {
      return null;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function parsePrecision(rawValue) {
    if (rawValue === undefined || rawValue === null || rawValue === '') {
      return null;
    }
    const precision = Number.parseInt(String(rawValue), 10);
    if (!Number.isFinite(precision) || precision < 0) {
      return null;
    }
    return Math.min(precision, 20);
  }

  function decimalSeparator(rawValue) {
    return String(rawValue ?? '').includes(',') ? ',' : '.';
  }

  function formatNumericValue(value, separator, precision = null) {
    let text;
    if (precision !== null) {
      text = value.toFixed(precision);
      if (precision > 0) {
        text = text.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
      }
    } else {
      text = String(value);
    }
    if (text === '-0') {
      text = '0';
    }
    return separator === ',' ? text.replace('.', ',') : text;
  }

  function sanitizeNumberText(rawValue) {
    const value = String(rawValue ?? '');
    let sanitized = '';
    let hasDecimalSeparator = false;

    for (let index = 0; index < value.length; index += 1) {
      const char = value[index];
      if (char >= '0' && char <= '9') {
        sanitized += char;
        continue;
      }
      if ((char === '.' || char === ',') && !hasDecimalSeparator) {
        sanitized += char;
        hasDecimalSeparator = true;
        continue;
      }
      if (char === '-' && sanitized.length === 0) {
        sanitized += char;
      }
    }

    return sanitized;
  }

  function clampNumericValue(input, numericValue) {
    const minValue = parseNumericValue(input.dataset.rangeMin);
    if (minValue !== null && numericValue < minValue) {
      return minValue;
    }
    const maxValue = parseNumericValue(input.dataset.rangeMax);
    if (maxValue !== null && numericValue > maxValue) {
      return maxValue;
    }
    return numericValue;
  }

  function setNumberValidity(input, numericValue) {
    if (!input.value || numericValue !== null) {
      input.setCustomValidity('');
      return;
    }
    const fieldLabel = input.dataset.fieldLabel || 'Field';
    input.setCustomValidity(`${fieldLabel} must be a valid number.`);
  }

  function sanitizeNumberInput(input) {
    const separator = decimalSeparator(input.value);
    const sanitized = sanitizeNumberText(input.value);
    if (input.value !== sanitized) {
      input.value = sanitized;
    }
    const numericValue = parseNumericValue(input.value);
    setNumberValidity(input, numericValue);
    if (numericValue === null) {
      return;
    }

    const clampedValue = clampNumericValue(input, numericValue);
    if (clampedValue !== numericValue) {
      input.value = formatNumericValue(clampedValue, separator);
      input.setCustomValidity('');
    }
  }

  function finalizeNumberInput(input) {
    const separator = decimalSeparator(input.value);
    const sanitized = sanitizeNumberText(input.value);
    if (input.value !== sanitized) {
      input.value = sanitized;
    }
    const numericValue = parseNumericValue(input.value);
    setNumberValidity(input, numericValue);
    if (numericValue === null) {
      return;
    }

    let finalValue = clampNumericValue(input, numericValue);
    const precision = parsePrecision(input.dataset.precision);
    if (precision !== null) {
      const multiplier = 10 ** precision;
      finalValue = Math.round(finalValue * multiplier) / multiplier;
    }
    input.value = formatNumericValue(finalValue, separator, precision);
    input.setCustomValidity('');
  }

  function initializeNumberControls(root = document) {
    const scope = root?.querySelectorAll ? root : document;
    scope.querySelectorAll(numberControlSelector).forEach((input) => {
      if (boundNumberInputs.has(input)) {
        return;
      }
      boundNumberInputs.add(input);
      input.addEventListener('input', () => sanitizeNumberInput(input));
      input.addEventListener('focusout', () => finalizeNumberInput(input));
    });
  }

  function applySubmittedDiffNumberMarkers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: numberControlSelector,
      changedClassName: 'is-changed-from-submitted-input',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const inputName = String(node.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  initializeNumberControls();

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.number = {
    initializeNumberControls,
    applySubmittedDiffNumberMarkers,
  };
})();
