(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};
  const sharedControlModule = (window.DatacaptureSubjectDetailModules.controls || {}).shared || {};

  function applySubmittedDiffTextareaMarkers(context) {
    sharedControlModule.applySubmittedDiffControlMarkers?.({
      ...context,
      markerSelector: 'textarea[data-submitted-diff-textarea][data-submitted-diff-control="textarea"]',
      changedClassName: 'is-changed-from-submitted-textarea',
      resolveKeyCandidates: ({ fieldKey, node }) => {
        const inputName = String(node.name || '').trim();
        return [inputName, fieldKey];
      },
    });
  }

  window.DatacaptureSubjectDetailModules.controls = window.DatacaptureSubjectDetailModules.controls || {};
  window.DatacaptureSubjectDetailModules.controls.textarea = {
    applySubmittedDiffTextareaMarkers,
  };
})();
