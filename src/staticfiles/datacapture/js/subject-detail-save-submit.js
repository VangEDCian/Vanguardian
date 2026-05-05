(function () {
  const formPanel = document.querySelector('.subject-form-panel');
  const fieldScope = formPanel || document;
  const feedbackDurationMs = 1200;
  /* Keep in sync with STABLE_EDIT_STATUSES in domain page_capture_save_submit.py */
  const lockStatuses = new Set(['in_review', 'verified', 'finalized', 'locked']);

  function normalizePageStatus(value) {
    return String(value ?? '')
      .trim()
      .toLowerCase();
  }

  function isPageLocked(status) {
    return lockStatuses.has(normalizePageStatus(status));
  }

  const saveButton = document.querySelector('[data-datacapture-save]');
  const resetButton = document.querySelector('[data-datacapture-reset]');
  const submitButton = document.querySelector('[data-datacapture-submit]');
  const formRoot = document.querySelector('[data-datacapture-form-root]');

  let pageStatus = formRoot ? normalizePageStatus(formRoot.dataset.pageStatus) : '';

  function ensureEditableInputs() {
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const fieldKey = (container.dataset.fieldKey || '').trim();
      if (!fieldKey) {
        return;
      }
      container.querySelectorAll('input, textarea, select').forEach((input) => {
        if (!input.name) {
          if (input.classList.contains('subject-date-picker__input--day')) {
            input.name = `${fieldKey}__day`;
          } else if (input.classList.contains('subject-date-picker__input--month')) {
            input.name = `${fieldKey}__month`;
          } else if (input.classList.contains('subject-date-picker__input--year')) {
            input.name = `${fieldKey}__year`;
          } else if (input.classList.contains('subject-datetime-control__time')) {
            input.name = `${fieldKey}__time`;
          } else {
            input.name = fieldKey;
          }
        }
        input.disabled = false;
        input.removeAttribute('disabled');
        if ('readOnly' in input) {
          input.readOnly = false;
        }
        input.removeAttribute('readonly');
      });
    });
  }

  const shouldUnlockFields = formPanel && !(formRoot && isPageLocked(pageStatus));
  if (shouldUnlockFields) {
    ensureEditableInputs();
  }

  if (!saveButton || !resetButton || !submitButton || !formRoot) {
    return;
  }

  pageStatus = normalizePageStatus(formRoot.dataset.pageStatus);

  const saveUrl = formRoot.dataset.saveUrl;
  const submitUrl = formRoot.dataset.submitUrl;
  const confirmationMessage =
    formRoot.dataset.confirmationMessage ||
    'This page was already submitted. Saving will create a correction version. Continue?';

  function setButtonsEnabled(enabled) {
    saveButton.disabled = !enabled;
    submitButton.disabled = !enabled;
    resetButton.disabled = !enabled;
  }

  function setButtonPending(button, pendingText) {
    if (!button.dataset.originalText) {
      button.dataset.originalText = button.textContent.trim();
    }
    button.textContent = pendingText;
    button.classList.add('is-pending');
  }

  function flashButtonState(button, state, stateText) {
    const originalText = button.dataset.originalText || button.textContent.trim();
    button.classList.remove('is-pending', 'is-success', 'is-error', 'is-idle');
    button.classList.add(state);
    button.textContent = stateText;
    window.setTimeout(() => {
      button.classList.remove(state);
      button.classList.add('is-idle');
      button.textContent = originalText;
    }, feedbackDurationMs);
  }

  function collectFormPayload() {
    const payload = {};
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      if (!input.name || input.disabled) {
        return;
      }
      if (input.type === 'checkbox') {
        payload[input.name] = input.checked;
        return;
      }
      payload[input.name] = input.value;
    });
    return JSON.stringify(payload);
  }

  function resetInputs() {
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      if (input.disabled) {
        return;
      }
      if (input.type === 'checkbox') {
        input.checked = false;
        return;
      }
      if (input.tagName === 'SELECT') {
        input.selectedIndex = 0;
        return;
      }
      input.value = '';
    });
  }

  function applyLockState() {
    if (!isPageLocked(pageStatus)) {
      return false;
    }
    setButtonsEnabled(false);
    fieldScope.querySelectorAll('input, textarea, select, button').forEach((el) => {
      if (el === saveButton || el === submitButton) {
        return;
      }
      el.disabled = true;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
        if (el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'hidden' && 'readOnly' in el) {
          el.readOnly = true;
        }
      }
    });
    return true;
  }

  if (applyLockState()) {
    return;
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body,
    });
    if (!response.ok) {
      throw new Error('Request failed');
    }
    return response.json();
  }

  saveButton.addEventListener('click', async () => {
    const requiresConfirmation = pageStatus === 'submitted';
    if (requiresConfirmation && !window.confirm(confirmationMessage)) {
      flashButtonState(saveButton, 'is-error', 'Cancelled');
      return;
    }
    setButtonsEnabled(false);
    setButtonPending(saveButton, 'Saving...');
    try {
      const result = await postJson(saveUrl, collectFormPayload());
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      flashButtonState(saveButton, 'is-success', 'Saved');
      if (applyLockState()) {
        return;
      }
    } catch (error) {
      flashButtonState(saveButton, 'is-error', 'Save failed');
      console.error(error);
    } finally {
      if (!isPageLocked(pageStatus)) {
        setButtonsEnabled(true);
      }
    }
  });

  resetButton.addEventListener('click', () => {
    resetInputs();
    flashButtonState(resetButton, 'is-success', 'Reset done');
  });

  submitButton.addEventListener('click', async () => {
    setButtonsEnabled(false);
    setButtonPending(submitButton, 'Submitting...');
    try {
      const result = await postJson(submitUrl, collectFormPayload());
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      flashButtonState(submitButton, 'is-success', 'Submitted');
      if (applyLockState()) {
        return;
      }
    } catch (error) {
      flashButtonState(submitButton, 'is-error', 'Submit failed');
      console.error(error);
    } finally {
      if (!isPageLocked(pageStatus)) {
        setButtonsEnabled(true);
      }
    }
  });
})();
