(function () {
  const buttons = Array.from(document.querySelectorAll('[data-form-verification-page-action]'));
  if (buttons.length === 0) {
    return;
  }

  const loadingOverlay = document.querySelector('[data-form-verification-loading]');
  const loadingMessageNode = document.querySelector('[data-form-verification-loading-message]');
  const defaultLoadingMessage = loadingOverlay
    ? String(loadingOverlay.dataset.defaultMessage || 'Processing verification...')
    : 'Processing verification...';
  const notificationHost = document.createElement('div');
  notificationHost.className = 'subject-detail-screen__notifications';
  notificationHost.setAttribute('data-form-verification-page-action-notifications', '');
  document.body.appendChild(notificationHost);
  const notificationDurationMs = 2600;

  function showLoading(message) {
    if (!loadingOverlay) {
      return;
    }
    if (loadingMessageNode) {
      loadingMessageNode.textContent = String(message || defaultLoadingMessage);
    }
    loadingOverlay.hidden = false;
  }

  function hideLoading() {
    if (loadingOverlay) {
      loadingOverlay.hidden = true;
    }
  }

  function showNotification(message, tone) {
    if (!message) {
      return;
    }
    const normalizedTone = tone === 'error' ? 'error' : 'success';
    const notice = document.createElement('div');
    notice.className = `subject-detail-screen__notification subject-detail-screen__notification--${normalizedTone}`;
    notice.textContent = message;
    notificationHost.appendChild(notice);

    window.setTimeout(function () {
      notice.classList.add('is-leaving');
      window.setTimeout(function () {
        if (notice.parentNode) {
          notice.parentNode.removeChild(notice);
        }
      }, 220);
    }, notificationDurationMs);
  }

  function normalizeErrorMessage(result) {
    const errs = result && result.data && result.data.error;
    const serverErrors = Array.isArray(errs) ? errs.join(', ') : '';
    if (serverErrors) {
      return serverErrors;
    }
    if (result && result.status >= 500) {
      return 'Server error.';
    }
    return 'Request failed.';
  }

  function setDisabled(disabled) {
    buttons.forEach(function (button) {
      button.disabled = disabled;
    });
  }

  function submitPageAction(button) {
    const postUrl = String(button.dataset.postUrl || '').trim();
    if (!postUrl) {
      showNotification('Action URL not found.', 'error');
      return;
    }

    setDisabled(true);
    showLoading(button.dataset.loadingMessage || defaultLoadingMessage);

    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      .then(function (response) {
        return response.text().then(function (text) {
          let data = {};
          if (text) {
            try {
              data = JSON.parse(text);
            } catch (_) {
              data = {};
            }
          }
          return { ok: response.ok, status: response.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data || result.data.ok !== true) {
          showNotification(normalizeErrorMessage(result), 'error');
          return;
        }
        showNotification(button.dataset.successMessage || 'Saved.', 'success');
        if (result.data.reload_required !== false) {
          window.setTimeout(function () {
            window.location.reload();
          }, 250);
        }
      })
      .catch(function () {
        showNotification('Network error.', 'error');
      })
      .finally(function () {
        hideLoading();
        setDisabled(false);
      });
  }

  buttons.forEach(function (button) {
    button.addEventListener('click', function () {
      submitPageAction(button);
    });
  });
})();
