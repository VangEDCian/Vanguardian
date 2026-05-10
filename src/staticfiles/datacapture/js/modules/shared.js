(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};

  const datePartSuffixes = ['__day', '__month', '__year', '__time'];

  function canonicalFieldKey(rawKey) {
    const normalized = String(rawKey ?? '').trim();
    for (const suffix of datePartSuffixes) {
      if (normalized.endsWith(suffix)) {
        return normalized.slice(0, -suffix.length);
      }
    }
    return normalized;
  }

  function normalizeComparableValue(rawValue) {
    if (rawValue === null || rawValue === undefined) {
      return '';
    }
    if (typeof rawValue === 'boolean') {
      return rawValue;
    }
    return String(rawValue);
  }

  function resolveCanonicalValue(payload, key) {
    const dateKeys = datePartSuffixes.map((suffix) => `${key}${suffix}`);
    const hasDatePart = dateKeys.some((dateKey) => Object.prototype.hasOwnProperty.call(payload, dateKey));
    if (hasDatePart) {
      return {
        __day: normalizeComparableValue(payload[`${key}__day`]),
        __month: normalizeComparableValue(payload[`${key}__month`]),
        __year: normalizeComparableValue(payload[`${key}__year`]),
        __time: normalizeComparableValue(payload[`${key}__time`]),
      };
    }
    return normalizeComparableValue(payload[key]);
  }

  function resolveChangedFieldKeys(previousPayload, currentPayload) {
    const canonicalKeys = new Set();
    Object.keys(previousPayload || {}).forEach((key) => {
      const canonical = canonicalFieldKey(key);
      if (canonical) {
        canonicalKeys.add(canonical);
      }
    });
    Object.keys(currentPayload || {}).forEach((key) => {
      const canonical = canonicalFieldKey(key);
      if (canonical) {
        canonicalKeys.add(canonical);
      }
    });

    const changed = [];
    Array.from(canonicalKeys)
      .sort()
      .forEach((key) => {
        const beforeValue = resolveCanonicalValue(previousPayload || {}, key);
        const afterValue = resolveCanonicalValue(currentPayload || {}, key);
        if (JSON.stringify(beforeValue) !== JSON.stringify(afterValue)) {
          changed.push(key);
        }
      });
    return changed;
  }

  function resolveFieldLabelMap(fieldScope) {
    const labels = new Map();
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const fieldKey = canonicalFieldKey(container.dataset.fieldKey || '');
      const fieldId = String(container.dataset.fieldId || '').trim();
      const labelNode = container.querySelector('.subject-form-flat-field__label');
      const rawLabel = labelNode ? String(labelNode.textContent || '') : fieldKey;
      const cleanedLabel = rawLabel.replace(/\*/g, '').trim() || fieldKey;
      if (fieldKey) {
        labels.set(fieldKey, cleanedLabel);
      }
      if (fieldId) {
        labels.set(`field_${fieldId}`, cleanedLabel);
      }
    });
    return labels;
  }

  function loadPayloadByScriptId(scriptId) {
    const payloadNode = document.getElementById(scriptId);
    if (!payloadNode) {
      return null;
    }
    try {
      const parsed = JSON.parse(payloadNode.textContent || '{}');
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (error) {
      console.error(error);
      return null;
    }
  }

  function loadPreviousSubmittedPayload() {
    return loadPayloadByScriptId('datacapture-previous-submitted-payload');
  }

  function loadCurrentDataPayload() {
    const payload = loadPayloadByScriptId('datacapture-current-data-payload');
    return payload && typeof payload === 'object' ? payload : {};
  }

  function loadPreviousDataPayload() {
    const payload = loadPayloadByScriptId('datacapture-previous-data-payload');
    if (payload && typeof payload === 'object') {
      return payload;
    }
    return null;
  }

  function formatEntryDate(now) {
    const pad = (value) => String(value).padStart(2, '0');
    const day = pad(now.getDate());
    const month = pad(now.getMonth() + 1);
    const year = now.getFullYear();
    const hour = pad(now.getHours());
    const minute = pad(now.getMinutes());
    return `${day}-${month}-${year} ${hour}:${minute}`;
  }

  window.DatacaptureSubjectDetailModules.shared = {
    datePartSuffixes,
    canonicalFieldKey,
    normalizeComparableValue,
    resolveChangedFieldKeys,
    resolveFieldLabelMap,
    loadPayloadByScriptId,
    loadPreviousSubmittedPayload,
    loadCurrentDataPayload,
    loadPreviousDataPayload,
    formatEntryDate,
  };
})();
