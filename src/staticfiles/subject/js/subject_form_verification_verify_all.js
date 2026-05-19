(function () {
  const button = document.querySelector(
    '[data-form-verification-verify-all], [data-form-verification-reopen]',
  );
  if (!button) {
    return;
  }
  const postUrl = String(button.dataset.postUrl || '').trim();
  if (!postUrl) {
    return;
  }
  const isReopenAction = button.hasAttribute('data-form-verification-reopen');

  const loadingOverlay = document.querySelector('[data-form-verification-loading]');
  const loadingMessageNode = document.querySelector('[data-form-verification-loading-message]');
  const reopenReasonModal = document.querySelector('[data-form-verification-reopen-reason-modal]');
  const reopenReasonInput = document.querySelector('[data-form-verification-reopen-reason-input]');
  const reopenReasonSubmit = document.querySelector('[data-form-verification-reopen-reason-submit]');
  const reopenReasonCancel = document.querySelector('[data-form-verification-reopen-reason-cancel]');
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

  function openReopenReasonModal() {
    if (!(reopenReasonModal instanceof HTMLElement)) {
      showNotification('Reopen reason form not found.', 'error');
      return;
    }
    if (reopenReasonInput instanceof HTMLTextAreaElement) {
      reopenReasonInput.value = '';
    }
    reopenReasonModal.hidden = false;
    if (reopenReasonInput instanceof HTMLTextAreaElement) {
      reopenReasonInput.focus();
    }
  }

  function closeReopenReasonModal() {
    if (reopenReasonModal instanceof HTMLElement) {
      reopenReasonModal.hidden = true;
    }
  }

  function submitVerificationRequest(payload) {
    const root = document.querySelector('.subject-form-verification-review');
    if (!isReopenAction && !root) {
      showNotification('Review panel not found.', 'error');
      return;
    }

    button.disabled = true;
    showLoading(defaultLoadingMessage);

    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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
        const msg = isReopenAction
          ? 'Form reopened.'
          : result.data.all_verified === true
            ? 'All fields verified.'
            : blockers.length > 0
              ? 'Saved. Pending blockers: ' + blockers.join(', ')
              : 'Saved.';
        showNotification(msg, 'success');
        if (isReopenAction) {
          window.setTimeout(function () {
            window.location.reload();
          }, 250);
          return;
        }
        const verifiedCheckedEnabled = Array.from(
          root.querySelectorAll('input[name="verify_field"]:checked:not(:disabled)'),
        );
        verifiedCheckedEnabled.forEach(function (el) {
          el.disabled = true;
          el.setAttribute('aria-disabled', 'true');
        });
      })
      .catch(function () {
        showNotification('Network error.', 'error');
      })
      .finally(function () {
        hideLoading();
        button.disabled = false;
      });
  }

  button.addEventListener('click', function () {
    if (isReopenAction) {
      openReopenReasonModal();
      return;
    }
    const root = document.querySelector('.subject-form-verification-review');
    if (!root) {
      showNotification('Review panel not found.', 'error');
      return;
    }
    const checked = Array.from(root.querySelectorAll('input[name="verify_field"]:checked:not(:disabled)'))
      .map(function (el) {
        return parseInt(String(el.value || '').trim(), 10);
      })
      .filter(function (n) {
        return !Number.isNaN(n);
      });
    submitVerificationRequest({ field_template_ids: checked });
  });

  if (reopenReasonSubmit instanceof HTMLElement) {
    reopenReasonSubmit.addEventListener('click', function () {
      const reasonText =
        reopenReasonInput instanceof HTMLTextAreaElement
          ? String(reopenReasonInput.value || '').trim()
          : '';
      if (!reasonText) {
        showNotification('Reopen reason is required.', 'error');
        return;
      }
      closeReopenReasonModal();
      submitVerificationRequest({ reason_text: reasonText });
    });
  }

  if (reopenReasonCancel instanceof HTMLElement) {
    reopenReasonCancel.addEventListener('click', closeReopenReasonModal);
  }
})();
