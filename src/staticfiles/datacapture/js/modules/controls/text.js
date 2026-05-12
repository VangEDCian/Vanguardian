(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};

  function applySubmittedDiffTextMarkers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: 'input[data-submitted-diff-input][data-submitted-diff-control="text"]',
      changedClassName: 'is-changed-from-submitted-input',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const inputName = String(node.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.text = {
    applySubmittedDiffTextMarkers,
  };
})();
