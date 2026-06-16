(() => {
  const DISPLAY_DURATION_MS = 2100;

  function hideFeedbackMessages() {
    const containers = document.querySelectorAll('.request-feedback');
    containers.forEach((container) => {
      window.setTimeout(() => {
        container.classList.add('is-hidden');
      }, DISPLAY_DURATION_MS);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideFeedbackMessages, { once: true });
    return;
  }
  hideFeedbackMessages();
})();
