(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};

  function applySubmittedDiffMultiSelectMarkers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: '[data-submitted-diff-multi-select][data-submitted-diff-control="multi-select"]',
      changedClassName: 'is-changed-from-submitted-choice-list',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const firstCheckbox = node.querySelector('input[type="checkbox"]');
        const inputName = String(firstCheckbox?.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.multiSelect = {
    applySubmittedDiffMultiSelectMarkers,
  };
})();
