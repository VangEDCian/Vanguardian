(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};
  const applySubmittedDiffControlMarkers = sharedControlModule.applySubmittedDiffControlMarkers || function () {};

  function applySubmittedDiffRadioMarkers(context) {
    const {
      fieldScope,
    } = context;

    if (!fieldScope) {
      return;
    }

    applySubmittedDiffControlMarkers({
      ...context,
      markerSelector: '[data-radio-option]',
      changedClassName: 'is-changed-from-submitted-control',
      includeContainerAsMarker: true,
      resolveKeyCandidates: ({ container, fieldKey }) => {
        const radios = Array.from(container.querySelectorAll('input[type="radio"]'));
        if (!radios.length) {
          return [];
        }
        const radioName = String(radios[0].name || '').trim();
        return [radioName, fieldKey];
      },
    });

    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      container.querySelectorAll('[data-radio-option-label]').forEach((labelNode) => {
        labelNode.classList.remove('is-changed-from-submitted');
      });
      if (!container.classList.contains('is-changed-from-submitted-control')) {
        return;
      }

      const radios = Array.from(container.querySelectorAll('input[type="radio"]'));
      const checkedRadio = radios.find((radio) => radio.checked);
      if (!checkedRadio) {
        container.classList.remove('is-changed-from-submitted-control');
        return;
      }
      const checkedLabel = checkedRadio.closest('label')?.querySelector('[data-radio-option-label]');
      if (checkedLabel) {
        checkedLabel.classList.add('is-changed-from-submitted');
      }
      container.classList.remove('is-changed-from-submitted-control');
    });
  }

  function dispatchRadioClearEvents(radio) {
    radio.dispatchEvent(new Event('input', { bubbles: true }));
    radio.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function clearRadioGroup(button) {
    if (!button || button.disabled) {
      return;
    }
    const container = button.closest('[data-submitted-diff-control="radio"]');
    if (!container) {
      return;
    }
    const checkedRadios = Array.from(container.querySelectorAll('input[type="radio"]:checked'));
    checkedRadios.forEach((radio) => {
      radio.checked = false;
      dispatchRadioClearEvents(radio);
    });
  }

  function initializeRadioClearControls(root) {
    const scope = root || document;
    if (scope.dataset?.radioClearInitialized === '1') {
      return;
    }
    if (scope.dataset) {
      scope.dataset.radioClearInitialized = '1';
    }
    scope.addEventListener('click', (event) => {
      const button = event.target?.closest?.('[data-radio-clear]');
      if (!button || !scope.contains(button)) {
        return;
      }
      clearRadioGroup(button);
    });
  }

  initializeRadioClearControls(document);

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.radio = {
    applySubmittedDiffRadioMarkers,
    initializeRadioClearControls,
  };
})();
