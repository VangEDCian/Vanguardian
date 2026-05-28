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
  const revertReasonModal = document.querySelector('[data-form-verification-revert-reason-modal]');
  const revertReasonFields = document.querySelector('[data-form-verification-revert-reason-fields]');
  const revertReasonSubmit = document.querySelector('[data-form-verification-revert-reason-submit]');
  const revertReasonCancel = document.querySelector('[data-form-verification-revert-reason-cancel]');
  let pendingRevertPayload = null;
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

  function fieldLabelForCheckbox(checkbox) {
    const row = checkbox.closest('tr[data-field-template-id]');
    if (!(row instanceof HTMLElement)) {
      return String(checkbox.value || '').trim();
    }
    const label = row.querySelector('.subject-form-verification-review__field-label');
    if (label instanceof HTMLElement) {
      const text = String(label.textContent || '').trim();
      if (text) {
        return text;
      }
    }
    return String(row.dataset.fieldKey || checkbox.value || '').trim();
  }

  function formatDateOfEntry(date) {
    const pad = function (value) {
      return String(value).padStart(2, '0');
    };
    return [
      pad(date.getDate()),
      pad(date.getMonth() + 1),
      date.getFullYear(),
    ].join('-') + ' ' + [pad(date.getHours()), pad(date.getMinutes())].join(':');
  }

  function openRevertReasonModal(fields) {
    if (
      !(revertReasonModal instanceof HTMLElement) ||
      !(revertReasonFields instanceof HTMLElement)
    ) {
      showNotification('Revert verification reason form not found.', 'error');
      return false;
    }
    revertReasonFields.innerHTML = '';
    const entryDateLabel = formatDateOfEntry(new Date());
    fields.forEach(function (field) {
      const row = document.createElement('tr');
      const dateCell = document.createElement('td');
      const fieldCell = document.createElement('td');
      const reasonCell = document.createElement('td');
      const reasonInput = document.createElement('input');

      dateCell.textContent = entryDateLabel;
      fieldCell.textContent = field.label || String(field.id || '');
      reasonInput.type = 'text';
      reasonInput.required = true;
      reasonInput.className = 'subject-detail-screen__reason-input';
      reasonInput.dataset.fieldTemplateId = String(field.id || '');
      reasonInput.dataset.fieldLabel = field.label || String(field.id || '');
      reasonInput.setAttribute('data-form-verification-revert-reason-input', '');
      reasonCell.appendChild(reasonInput);

      row.appendChild(dateCell);
      row.appendChild(fieldCell);
      row.appendChild(reasonCell);
      revertReasonFields.appendChild(row);
    });
    revertReasonModal.hidden = false;
    const firstInput = revertReasonFields.querySelector('[data-form-verification-revert-reason-input]');
    if (firstInput instanceof HTMLInputElement) {
      firstInput.focus();
    }
    return true;
  }

  function closeRevertReasonModal() {
    if (revertReasonModal instanceof HTMLElement) {
      revertReasonModal.hidden = true;
    }
    if (revertReasonFields instanceof HTMLElement) {
      revertReasonFields.innerHTML = '';
    }
    pendingRevertPayload = null;
  }

  function submitVerificationRequest(payload) {
    const root = document.querySelector('.subject-form-verification-review');
    if (!isReopenAction && !root) {
      showNotification('Review panel not found.', 'error');
      return;
    }
    const requestPayload = { ...payload };
    if (!isReopenAction && root instanceof HTMLElement) {
      requestPayload.review_page_entry_id = String(root.dataset.reviewPageEntryId || '').trim();
      requestPayload.review_entry_version = String(root.dataset.reviewEntryVersion || '').trim();
      requestPayload.review_page_status = String(root.dataset.reviewPageStatus || '').trim();
    }

    button.disabled = true;
    showLoading(defaultLoadingMessage);

    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
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
        if (isReopenAction || result.data.all_verified === true) {
          window.setTimeout(function () {
            window.location.reload();
          }, 250);
          return;
        }
        if (root instanceof HTMLElement) {
          root.dataset.reviewPageStatus = String(result.data.page_status || root.dataset.reviewPageStatus || '');
        }
        const verifiedCheckedEnabled = Array.from(
          root.querySelectorAll('input[name="verify_field"]:checked:not(:disabled)'),
        );
        verifiedCheckedEnabled.forEach(function (el) {
          el.dataset.fieldVerified = 'true';
          el.setAttribute('data-field-verified', 'true');
          const row = el.closest('tr[data-field-template-id]');
          if (row instanceof HTMLElement) {
            row.dataset.fieldVerified = 'true';
            row.setAttribute('data-field-verified', 'true');
          }
        });
        const unverifiedIds = Array.isArray(result.data.unverified_field_template_ids)
          ? result.data.unverified_field_template_ids
          : Array.isArray(payload.unverified_field_template_ids)
            ? payload.unverified_field_template_ids
            : [];
        unverifiedIds.forEach(function (fieldTemplateId) {
          const selector = `input[name="verify_field"][value="${String(fieldTemplateId)}"]`;
          const el = root.querySelector(selector);
          if (!(el instanceof HTMLInputElement)) {
            return;
          }
          el.checked = false;
          el.dataset.fieldVerified = 'false';
          el.setAttribute('data-field-verified', 'false');
          const row = el.closest('tr[data-field-template-id]');
          if (row instanceof HTMLElement) {
            row.dataset.fieldVerified = 'false';
            row.setAttribute('data-field-verified', 'false');
          }
        });
        root.dispatchEvent(new CustomEvent('verification:items-updated'));
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
    const enabledCheckboxes = Array.from(root.querySelectorAll('input[name="verify_field"]:not(:disabled)'));
    const checked = enabledCheckboxes
      .filter(function (el) {
        return el.checked;
      })
      .map(function (el) {
        return parseInt(String(el.value || '').trim(), 10);
      })
      .filter(function (n) {
        return !Number.isNaN(n);
      });
    const uncheckedVerified = enabledCheckboxes
      .filter(function (el) {
        return !el.checked && String(el.dataset.fieldVerified || '').trim().toLowerCase() === 'true';
      })
      .map(function (el) {
        return parseInt(String(el.value || '').trim(), 10);
      })
      .filter(function (n) {
        return !Number.isNaN(n);
      });
    const payload = {
      field_template_ids: Array.from(new Set(checked)),
      unverified_field_template_ids: Array.from(new Set(uncheckedVerified)),
    };
    if (payload.unverified_field_template_ids.length > 0) {
      const fields = enabledCheckboxes
        .filter(function (el) {
          const fieldTemplateId = parseInt(String(el.value || '').trim(), 10);
          return payload.unverified_field_template_ids.indexOf(fieldTemplateId) !== -1;
        })
        .map(function (el) {
          return {
            id: parseInt(String(el.value || '').trim(), 10),
            label: fieldLabelForCheckbox(el),
          };
        });
      pendingRevertPayload = payload;
      if (!openRevertReasonModal(fields)) {
        pendingRevertPayload = null;
      }
      return;
    }
    submitVerificationRequest(payload);
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

  if (revertReasonSubmit instanceof HTMLElement) {
    revertReasonSubmit.addEventListener('click', function () {
      if (!pendingRevertPayload) {
        closeRevertReasonModal();
        return;
      }
      const reasonInputs =
        revertReasonFields instanceof HTMLElement
          ? Array.from(revertReasonFields.querySelectorAll('[data-form-verification-revert-reason-input]'))
          : [];
      if (reasonInputs.length === 0) {
        showNotification('Revert verification reason form not found.', 'error');
        return;
      }
      const reasonRows = reasonInputs.map(function (input) {
        return {
          fieldLabel: String(input.dataset.fieldLabel || '').trim(),
          input: input,
          reason: input instanceof HTMLInputElement ? String(input.value || '').trim() : '',
        };
      });
      const missingReasonRow = reasonRows.find(function (row) {
        return !row.reason;
      });
      if (missingReasonRow) {
        showNotification('Reason for revert verification is required.', 'error');
        if (missingReasonRow.input instanceof HTMLInputElement) {
          missingReasonRow.input.focus();
        }
        return;
      }
      const reasonText =
        reasonRows.length === 1
          ? reasonRows[0].reason
          : reasonRows
              .map(function (row) {
                return `${row.fieldLabel || 'Field'}: ${row.reason}`;
              })
              .join('\n');
      const payload = {
        ...pendingRevertPayload,
        reason_text: reasonText,
      };
      closeRevertReasonModal();
      submitVerificationRequest(payload);
    });
  }

  if (revertReasonCancel instanceof HTMLElement) {
    revertReasonCancel.addEventListener('click', closeRevertReasonModal);
  }
})();
