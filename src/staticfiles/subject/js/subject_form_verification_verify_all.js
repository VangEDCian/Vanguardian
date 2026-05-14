(function () {
  const button = document.querySelector('[data-form-verification-verify-all]');
  if (!button) {
    return;
  }
  const postUrl = String(button.dataset.postUrl || '').trim();
  if (!postUrl) {
    return;
  }

  const loadingOverlay = document.querySelector('[data-form-verification-loading]');
  const loadingMessageNode = document.querySelector('[data-form-verification-loading-message]');
  const notificationDurationMs = 2600;
  const notificationHost = document.createElement('div');
  notificationHost.className = 'subject-detail-screen__notifications';
  notificationHost.setAttribute('data-form-verification-notifications', '');
  document.body.appendChild(notificationHost);
  const defaultLoadingMessage = loadingOverlay
    ? String(loadingOverlay.dataset.defaultMessage || 'Processing verification...')
    : 'Processing verification...';

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
    if (!loadingOverlay) {
      return;
    }
    loadingOverlay.hidden = true;
  }

  function normalizeErrorMessage(result) {
    var errs = result && result.data && result.data.error;
    var serverErrors = Array.isArray(errs) ? errs.join(', ') : '';
    if (serverErrors) {
      return serverErrors;
    }
    if (result && result.status >= 500) {
      return 'Server error.';
    }
    return 'Request failed.';
  }

  function showNotification(message, tone) {
    if (!message || !notificationHost) {
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

  button.addEventListener('click', function () {
    const root = document.querySelector('.subject-form-verification-review');
    if (!root) {
      showNotification('Review panel not found.', 'error');
      return;
    }
    const checked = Array.from(root.querySelectorAll('input[name="verify_field"]:checked'))
      .map(function (el) {
        return parseInt(String(el.value || '').trim(), 10);
      })
      .filter(function (n) {
        return !Number.isNaN(n);
      });

    button.disabled = true;
    showLoading(defaultLoadingMessage);

    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_template_ids: checked }),
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
        const blockers = Array.isArray(result.data.blocking_reasons)
          ? result.data.blocking_reasons
          : [];
        const msg =
          result.data.all_verified === true
            ? 'All fields verified.'
            : blockers.length > 0
              ? 'Saved. Pending blockers: ' + blockers.join(', ')
              : 'Saved.';
        showNotification(msg, 'success');
      })
      .catch(function () {
        showNotification('Network error.', 'error');
      })
      .finally(function () {
        hideLoading();
        button.disabled = false;
      });
  });
})();
