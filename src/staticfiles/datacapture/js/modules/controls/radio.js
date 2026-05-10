(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};

  function resolvePayloadValue(payload, keys) {
    if (!payload || typeof payload !== 'object') {
      return { found: false, value: '' };
    }
    for (const key of keys) {
      const normalizedKey = String(key || '').trim();
      if (!normalizedKey) {
        continue;
      }
      if (Object.prototype.hasOwnProperty.call(payload, normalizedKey)) {
        return { found: true, value: payload[normalizedKey] };
      }
    }
    return { found: false, value: '' };
  }

  function applySubmittedDiffRadioMarkers(context) {
    const {
      fieldScope,
      previousSubmittedPayload,
      currentPayload,
      initialCurrentPayload,
      canonicalFieldKey,
      normalizeComparableValue,
    } = context;

    if (!fieldScope) {
      return;
    }

    if (!previousSubmittedPayload) {
      fieldScope.querySelectorAll('[data-radio-option-label]').forEach((labelNode) => {
        labelNode.classList.remove('is-changed-from-submitted');
      });
      return;
    }

    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const radios = Array.from(container.querySelectorAll('input[type="radio"]'));
      if (!radios.length) {
        return;
      }

      const fieldKey = canonicalFieldKey(container.dataset.fieldKey || '');
      const radioName = String(radios[0].name || '').trim();

      const previousValueResult = resolvePayloadValue(previousSubmittedPayload, [radioName, fieldKey]);
      let currentValueResult = resolvePayloadValue(currentPayload, [radioName, fieldKey]);
      if (!currentValueResult.found) {
        currentValueResult = resolvePayloadValue(initialCurrentPayload, [radioName, fieldKey]);
      }
      if (!previousValueResult.found) {
        container.querySelectorAll('[data-radio-option-label]').forEach((labelNode) => {
          labelNode.classList.remove('is-changed-from-submitted');
        });
        return;
      }
      const isChanged =
        normalizeComparableValue(previousValueResult.value) !== normalizeComparableValue(currentValueResult.value);

      container.querySelectorAll('[data-radio-option-label]').forEach((labelNode) => {
        labelNode.classList.remove('is-changed-from-submitted');
      });
      if (!isChanged) {
        return;
      }

      const checkedRadio = radios.find((radio) => radio.checked);
      if (!checkedRadio) {
        return;
      }
      const checkedLabel = checkedRadio.closest('label')?.querySelector('[data-radio-option-label]');
      if (checkedLabel) {
        checkedLabel.classList.add('is-changed-from-submitted');
      }
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.radio = {
    applySubmittedDiffRadioMarkers,
  };
})();
