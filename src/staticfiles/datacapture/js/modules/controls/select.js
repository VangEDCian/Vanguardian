(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};

  function applySubmittedDiffSelectMarkers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: 'select[data-submitted-diff-select][data-submitted-diff-control="select"]',
      changedClassName: 'is-changed-from-submitted-input',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const inputName = String(node.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.select = {
    applySubmittedDiffSelectMarkers,
  };
})();
