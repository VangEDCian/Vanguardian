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

  function applySubmittedDiffControlMarkers(context) {
    const {
      fieldScope,
      previousSubmittedPayload,
      currentPayload,
      initialCurrentPayload,
      canonicalFieldKey,
      normalizeComparableValue,
      markerSelector,
      changedClassName,
      resolveKeyCandidates,
      includeContainerAsMarker = false,
      verifiedFieldKeySet,
    } = context;

    if (!fieldScope || !markerSelector || !changedClassName || typeof resolveKeyCandidates !== 'function') {
      return;
    }

    if (!previousSubmittedPayload) {
      fieldScope.querySelectorAll(markerSelector).forEach((node) => {
        node.classList.remove(changedClassName);
      });
      return;
    }

    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const fieldKey = canonicalFieldKey(container.dataset.fieldKey || '');
      const markerNodes = includeContainerAsMarker
        ? [container]
        : Array.from(container.querySelectorAll(markerSelector));
      if (!markerNodes.length) {
        return;
      }
      if (verifiedFieldKeySet instanceof Set && verifiedFieldKeySet.size > 0 && !verifiedFieldKeySet.has(fieldKey)) {
        markerNodes.forEach((node) => {
          node.classList.remove(changedClassName);
        });
        return;
      }

      markerNodes.forEach((node) => {
        const candidates = resolveKeyCandidates({ container, fieldKey, node }) || [];
        const previousValueResult = resolvePayloadValue(previousSubmittedPayload, candidates);
        let currentValueResult = resolvePayloadValue(currentPayload, candidates);
        if (!currentValueResult.found) {
          currentValueResult = resolvePayloadValue(initialCurrentPayload, candidates);
        }

        if (!previousValueResult.found) {
          node.classList.remove(changedClassName);
          return;
        }

        const isChanged =
          normalizeComparableValue(previousValueResult.value) !== normalizeComparableValue(currentValueResult.value);
        node.classList.toggle(changedClassName, isChanged);
      });
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.shared = {
    resolvePayloadValue,
    applySubmittedDiffControlMarkers,
  };
})();
