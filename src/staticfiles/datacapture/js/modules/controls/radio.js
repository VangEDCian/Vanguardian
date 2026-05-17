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

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.radio = {
    applySubmittedDiffRadioMarkers,
  };
})();
