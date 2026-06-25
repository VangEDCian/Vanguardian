(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};

  function normalizeLabel(rawValue) {
    return String(rawValue ?? '').trim();
  }

  function normalizeStoredValue(rawLabel) {
    return normalizeLabel(rawLabel).toUpperCase();
  }

  function findSelect2Containers(scope) {
    return Array.from((scope || document).querySelectorAll('[data-field-key]')).filter((container) =>
      container.querySelector('[data-field-lookup-label-input][data-field-lookup-key]'),
    );
  }

  function syncSelect2LookupControls(scope) {
    findSelect2Containers(scope).forEach((container) => {
      const labelInput = container.querySelector('[data-field-lookup-label-input]');
      const valueInput = container.querySelector('[data-field-lookup-value-input]');
      if (!labelInput || !valueInput) {
        return;
      }
      const dataListId = labelInput.getAttribute('list');
      const dataList = dataListId ? document.getElementById(dataListId) : null;
      const matchedOption = dataList
        ? Array.from(dataList.options || []).find((option) => normalizeLabel(option.value) === normalizeLabel(labelInput.value))
        : null;
      valueInput.value = matchedOption
        ? normalizeLabel(matchedOption.dataset.lookupValue || matchedOption.value)
        : normalizeStoredValue(labelInput.value);
    });
  }

  function collectLookupLabels(scope) {
    const labels = {};
    findSelect2Containers(scope).forEach((container) => {
      const fieldKey = String(container.dataset.fieldKey || '').trim();
      const labelInput = container.querySelector('[data-field-lookup-label-input]');
      if (!fieldKey || !labelInput) {
        return;
      }
      labels[fieldKey] = normalizeLabel(labelInput.value);
    });
    return labels;
  }

  function applyPayloadToSelect2Controls(scope, payload) {
    findSelect2Containers(scope).forEach((container) => {
      const fieldKey = String(container.dataset.fieldKey || '').trim();
      const labelInput = container.querySelector('[data-field-lookup-label-input]');
      const valueInput = container.querySelector('[data-field-lookup-value-input]');
      if (!fieldKey || !labelInput || !valueInput || !payload || typeof payload !== 'object') {
        return;
      }
      if (!Object.prototype.hasOwnProperty.call(payload, fieldKey)) {
        return;
      }
      const value = String(payload[fieldKey] ?? '');
      valueInput.value = value;
      labelInput.value = value;
    });
  }

  async function fetchLookupOptions(input) {
    const lookupKey = String(input.dataset.fieldLookupKey || '').trim();
    const url = String(input.dataset.fieldLookupUrl || '').trim();
    const query = normalizeLabel(input.value);
    if (!lookupKey || !url) {
      return null;
    }
    const endpoint = new URL(url, window.location.origin);
    endpoint.searchParams.set('lookup', lookupKey);
    endpoint.searchParams.set('q', query);
    const response = await fetch(endpoint.toString(), {
      headers: {
        Accept: 'application/json',
      },
      credentials: 'same-origin',
    });
    if (!response.ok) {
      return [];
    }
    const payload = await response.json();
    return Array.isArray(payload.results) ? payload.results : [];
  }

  function renderLookupOptions(input, results) {
    const listId = input.getAttribute('list');
    if (!listId) {
      return;
    }
    const dataList = document.getElementById(listId);
    if (!dataList) {
      return;
    }
    dataList.textContent = '';
    results.forEach((item) => {
      const label = normalizeLabel(item.label || item.text || item.value);
      if (!label) {
        return;
      }
      const option = document.createElement('option');
      option.value = label;
      option.dataset.lookupValue = normalizeLabel(item.value || item.id || label);
      dataList.appendChild(option);
    });
  }

  function initializeSelect2LookupControls(scope) {
    findSelect2Containers(scope).forEach((container) => {
      const input = container.querySelector('[data-field-lookup-label-input]');
      if (!input || input.dataset.fieldLookupInitialized === '1') {
        return;
      }
      input.dataset.fieldLookupInitialized = '1';
      let pendingTimer = null;
      input.addEventListener('input', () => {
        syncSelect2LookupControls(container);
        if (pendingTimer) {
          window.clearTimeout(pendingTimer);
        }
        pendingTimer = window.setTimeout(async () => {
          const results = await fetchLookupOptions(input);
          if (Array.isArray(results)) {
            renderLookupOptions(input, results);
          }
        }, 180);
      });
      input.addEventListener('change', () => {
        syncSelect2LookupControls(container);
      });
      const valueInput = container.querySelector('[data-field-lookup-value-input]');
      if (valueInput && !normalizeLabel(valueInput.value) && normalizeLabel(input.value)) {
        syncSelect2LookupControls(container);
      }
    });
  }

  function applySubmittedDiffSelect2Markers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: 'input[data-submitted-diff-select2][data-submitted-diff-control="select2"]',
      changedClassName: 'is-changed-from-submitted-input',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const valueInput = node.closest('[data-field-key]')?.querySelector('[data-field-lookup-value-input]');
        const inputName = String(valueInput?.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.select2 = {
    initializeSelect2LookupControls,
    syncSelect2LookupControls,
    collectLookupLabels,
    applyPayloadToSelect2Controls,
    applySubmittedDiffSelect2Markers,
  };
})();
