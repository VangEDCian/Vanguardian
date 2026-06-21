(function () {
  const policyNodes = Array.from(document.querySelectorAll('[data-event-attestation-policy]'));
  if (policyNodes.length === 0) {
    return;
  }

  const loadingOverlay = document.querySelector('[data-form-verification-loading]');
  const loadingMessageNode = document.querySelector('[data-form-verification-loading-message]');
  const notificationHost = document.createElement('div');
  notificationHost.className = 'subject-detail-screen__notifications';
  notificationHost.setAttribute('data-event-attestation-notifications', '');
  document.body.appendChild(notificationHost);

  function showLoading(message) {
    if (!loadingOverlay) {
      return;
    }
    if (loadingMessageNode) {
      loadingMessageNode.textContent = message || 'Processing attestation...';
    }
    loadingOverlay.hidden = false;
  }

  function hideLoading() {
    if (loadingOverlay) {
      loadingOverlay.hidden = true;
    }
  }

  function showNotification(message, tone) {
    const notice = document.createElement('div');
    const normalizedTone = tone === 'error' ? 'error' : 'success';
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
    }, 2600);
  }

  function errorMessage(result) {
    const errors = result && result.data && result.data.error;
    if (Array.isArray(errors) && errors.length > 0) {
      return errors.join(', ');
    }
    if (result && result.status >= 500) {
      return 'Server error.';
    }
    return 'Request failed.';
  }

  function postJson(url, payload) {
    return window.fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
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
    });
  }

  function setPolicyDisabled(policyNode, disabled) {
    Array.from(policyNode.querySelectorAll('button')).forEach(function (button) {
      button.disabled = disabled;
    });
  }

  function submitAttestation(policyNode, button) {
    const postUrl = String(button.dataset.postUrl || '').trim();
    const confirmInput = policyNode.querySelector('[data-event-attestation-confirm]');
    if (confirmInput && !confirmInput.checked) {
      showNotification('Confirmation is required.', 'error');
      return;
    }
    if (!postUrl) {
      showNotification('Action URL not found.', 'error');
      return;
    }
    setPolicyDisabled(policyNode, true);
    showLoading('Processing attestation...');
    postJson(postUrl, { confirmation_accepted: !confirmInput || confirmInput.checked })
      .then(function (result) {
        if (!result.ok || !result.data || result.data.ok !== true) {
          showNotification(errorMessage(result), 'error');
          return;
        }
        showNotification(button.dataset.successMessage || 'Attestation saved.', 'success');
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
        setPolicyDisabled(policyNode, false);
      });
  }

  function revokeAttestation(policyNode, button) {
    const postUrl = String(button.dataset.postUrl || '').trim();
    if (!postUrl) {
      showNotification('Action URL not found.', 'error');
      return;
    }
    const reason = window.prompt('Reason for revocation');
    if (!reason || !reason.trim()) {
      return;
    }
    setPolicyDisabled(policyNode, true);
    showLoading('Revoking attestation...');
    postJson(postUrl, { reason_text: reason.trim() })
      .then(function (result) {
        if (!result.ok || !result.data || result.data.ok !== true) {
          showNotification(errorMessage(result), 'error');
          return;
        }
        showNotification('Attestation revoked.', 'success');
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
        setPolicyDisabled(policyNode, false);
      });
  }

  policyNodes.forEach(function (policyNode) {
    const submitButton = policyNode.querySelector('[data-event-attestation-submit]');
    const revokeButton = policyNode.querySelector('[data-event-attestation-revoke]');
    if (submitButton) {
      submitButton.addEventListener('click', function () {
        submitAttestation(policyNode, submitButton);
      });
    }
    if (revokeButton) {
      revokeButton.addEventListener('click', function () {
        revokeAttestation(policyNode, revokeButton);
      });
    }
  });
})();
