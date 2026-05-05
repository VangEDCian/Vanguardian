(function () {
  const formPanel = document.querySelector('.subject-form-panel');
  const fieldScope = formPanel || document;
  const notificationDurationMs = 2600;
  const datePartSuffixes = ['__day', '__month', '__year', '__time'];
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
  const deleteDraftButton = document.querySelector('[data-datacapture-delete-draft]');
  const formRoot = document.querySelector('[data-datacapture-form-root]');
  const loadingOverlay = document.querySelector('[data-datacapture-loading]');
  const loadingMessage = document.querySelector('[data-datacapture-loading-message]');
  const reasonModalBackdrop = document.querySelector('[data-datacapture-reason-modal]');
  const reasonRowsHost = document.querySelector('[data-datacapture-reason-rows]');
  const reasonSubmitButton = document.querySelector('[data-datacapture-reason-submit]');
  const reasonCancelButton = document.querySelector('[data-datacapture-reason-cancel]');
  const notificationHost = document.createElement('div');
  notificationHost.className = 'subject-detail-screen__notifications';
  notificationHost.setAttribute('data-datacapture-notifications', '');
  document.body.appendChild(notificationHost);

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
          } else if (input.classList.contains('subject-date-picker__input--time')) {
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

  if (!formRoot) {
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      input.disabled = true;
      if (
        input instanceof HTMLInputElement ||
        input instanceof HTMLTextAreaElement
      ) {
        if (
          input.type !== 'checkbox' &&
          input.type !== 'radio' &&
          input.type !== 'hidden' &&
          'readOnly' in input
        ) {
          input.readOnly = true;
        }
      }
    });
    return;
  }

  const shouldUnlockFields = formPanel && !isPageLocked(pageStatus);
  if (shouldUnlockFields) {
    ensureEditableInputs();
  }

  if (!saveButton || !resetButton || !submitButton) {
    return;
  }

  pageStatus = normalizePageStatus(formRoot.dataset.pageStatus);

  const saveUrl = formRoot.dataset.saveUrl;
  const submitUrl = formRoot.dataset.submitUrl;
  const deleteDraftUrl = formRoot.dataset.deleteDraftUrl;
  const currentEntryId = Number.parseInt(formRoot.dataset.currentEntryId || '', 10);
  const confirmationMessage =
    formRoot.dataset.confirmationMessage ||
    'This page was already submitted. Saving will create a correction version. Continue?';
  const deleteDraftConfirmationMessage =
    formRoot.dataset.deleteDraftConfirmationMessage ||
    'Delete current draft version? This action marks it as canceled.';

  function setButtonsEnabled(enabled) {
    saveButton.disabled = !enabled;
    submitButton.disabled = !enabled;
    resetButton.disabled = !enabled;
    if (deleteDraftButton) {
      deleteDraftButton.disabled = !enabled;
    }
  }

  function setButtonPending(button, pendingText) {
    if (!button.dataset.originalText) {
      button.dataset.originalText = button.textContent.trim();
    }
    button.textContent = pendingText;
    button.classList.add('is-pending');
  }

  function clearButtonPending(button) {
    const originalText = button.dataset.originalText || button.textContent.trim();
    button.classList.remove('is-pending');
    button.textContent = originalText;
  }

  function showLoading(message) {
    if (!loadingOverlay) {
      return;
    }
    if (loadingMessage) {
      loadingMessage.textContent =
        message || loadingOverlay.dataset.defaultMessage || 'Processing...';
    }
    loadingOverlay.hidden = false;
  }

  function hideLoading() {
    if (!loadingOverlay) {
      return;
    }
    loadingOverlay.hidden = true;
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

    window.setTimeout(() => {
      notice.classList.add('is-leaving');
      window.setTimeout(() => {
        if (notice.parentNode) {
          notice.parentNode.removeChild(notice);
        }
      }, 220);
    }, notificationDurationMs);
  }

  function parseNumericValue(rawValue) {
    const normalized = String(rawValue ?? '').trim().replace(',', '.');
    if (!normalized) {
      return null;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function normalizeEntryStatus(value) {
    return String(value ?? '')
      .trim()
      .toLowerCase();
  }

  function shouldReloadWithLatestEntry(result) {
    const latestEntry = result?.latest_page_entry;
    if (!latestEntry) {
      return false;
    }
    const latestStatus = normalizeEntryStatus(latestEntry.status);
    if (latestStatus !== 'draft' && latestStatus !== 'submitted') {
      return false;
    }
    if (result?.created_new_entry === true) {
      return true;
    }
    const latestEntryId = Number.parseInt(String(latestEntry.id ?? ''), 10);
    if (!Number.isFinite(latestEntryId)) {
      return false;
    }
    return Number.isFinite(currentEntryId) && latestEntryId !== currentEntryId;
  }

  function validateNumberInput(input) {
    const rawValue = String(input.value ?? '').trim();
    if (!rawValue) {
      return { ok: !input.required, message: `${input.dataset.fieldLabel || 'Field'} is required.` };
    }

    const numericValue = parseNumericValue(rawValue);
    const fieldLabel = input.dataset.fieldLabel || 'Field';
    if (numericValue === null) {
      return { ok: false, message: `${fieldLabel} must be a valid number.` };
    }

    const minValue = parseNumericValue(input.dataset.rangeMin);
    if (minValue !== null && numericValue < minValue) {
      return { ok: false, message: `${fieldLabel} must be greater than or equal to ${input.dataset.rangeMin}.` };
    }

    const maxValue = parseNumericValue(input.dataset.rangeMax);
    if (maxValue !== null && numericValue > maxValue) {
      return { ok: false, message: `${fieldLabel} must be less than or equal to ${input.dataset.rangeMax}.` };
    }

    return { ok: true, message: '' };
  }

  function validateDateParts() {
    const dateContainers = fieldScope.querySelectorAll('[data-field-key]');
    for (const container of dateContainers) {
      const dayInput = container.querySelector('.subject-date-picker__input--day');
      const monthSelect = container.querySelector('.subject-date-picker__input--month');
      const yearInput = container.querySelector('.subject-date-picker__input--year');
      if (!dayInput || !monthSelect || !yearInput) {
        continue;
      }
      if (dayInput.disabled || monthSelect.disabled || yearInput.disabled) {
        continue;
      }

      const day = String(dayInput.value || '').trim();
      const month = String(monthSelect.value || '').trim();
      const year = String(yearInput.value || '').trim();

      if (!day || !month || !year) {
        continue;
      }

      const dayInt = Number.parseInt(day, 10);
      const monthInt = Number.parseInt(month, 10);
      const yearInt = Number.parseInt(year, 10);
      const composedDate = new Date(yearInt, monthInt - 1, dayInt);
      const isValidDate =
        composedDate.getFullYear() === yearInt &&
        composedDate.getMonth() === monthInt - 1 &&
        composedDate.getDate() === dayInt;

      if (!isValidDate) {
        const fieldLabel = dayInput.dataset.fieldLabel || container.dataset.fieldKey || 'Date';
        return {
          ok: false,
          message: `${fieldLabel} is not a valid date.`,
          focusEl: dayInput,
        };
      }
    }
    return { ok: true, message: '', focusEl: null };
  }

  function validateBeforePersist() {
    const controls = fieldScope.querySelectorAll('input, textarea, select');
    for (const control of controls) {
      if (!control.name || control.disabled || control.type === 'hidden') {
        continue;
      }
      if (control.dataset.validatorType === 'number') {
        const numberValidation = validateNumberInput(control);
        if (!numberValidation.ok) {
          control.focus();
          showNotification(numberValidation.message, 'error');
          return false;
        }
        continue;
      }

      if (!control.checkValidity()) {
        const fieldLabel = control.dataset.fieldLabel || control.name || 'Field';
        const customMessage = control.dataset.validationMessage || '';
        const message = customMessage || `${fieldLabel} is invalid.`;
        control.focus();
        showNotification(message, 'error');
        return false;
      }
    }

    const dateValidation = validateDateParts();
    if (!dateValidation.ok) {
      if (dateValidation.focusEl) {
        dateValidation.focusEl.focus();
      }
      showNotification(dateValidation.message, 'error');
      return false;
    }

    return true;
  }

  function collectFormPayloadObject() {
    const payload = {};
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      if (!input.name || input.disabled) {
        return;
      }
      if (input.type === 'checkbox') {
        payload[input.name] = input.checked;
        return;
      }
      if (input.type === 'radio') {
        if (!input.checked) {
          return;
        }
        payload[input.name] = input.value;
        return;
      }
      payload[input.name] = input.value;
    });
    return payload;
  }

  function collectFormPayload() {
    return JSON.stringify(collectFormPayloadObject());
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
      if (input.type === 'radio') {
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

  function canonicalFieldKey(rawKey) {
    const normalized = String(rawKey ?? '').trim();
    for (const suffix of datePartSuffixes) {
      if (normalized.endsWith(suffix)) {
        return normalized.slice(0, -suffix.length);
      }
    }
    return normalized;
  }

  function normalizeComparableValue(rawValue) {
    if (rawValue === null || rawValue === undefined) {
      return '';
    }
    if (typeof rawValue === 'boolean') {
      return rawValue;
    }
    return String(rawValue);
  }

  function resolveCanonicalValue(payload, key) {
    const dateKeys = datePartSuffixes.map((suffix) => `${key}${suffix}`);
    const hasDatePart = dateKeys.some((dateKey) => Object.prototype.hasOwnProperty.call(payload, dateKey));
    if (hasDatePart) {
      return {
        __day: normalizeComparableValue(payload[`${key}__day`]),
        __month: normalizeComparableValue(payload[`${key}__month`]),
        __year: normalizeComparableValue(payload[`${key}__year`]),
        __time: normalizeComparableValue(payload[`${key}__time`]),
      };
    }
    return normalizeComparableValue(payload[key]);
  }

  function resolveChangedFieldKeys(previousPayload, currentPayload) {
    const canonicalKeys = new Set();
    Object.keys(previousPayload || {}).forEach((key) => {
      const canonical = canonicalFieldKey(key);
      if (canonical) {
        canonicalKeys.add(canonical);
      }
    });
    Object.keys(currentPayload || {}).forEach((key) => {
      const canonical = canonicalFieldKey(key);
      if (canonical) {
        canonicalKeys.add(canonical);
      }
    });

    const changed = [];
    Array.from(canonicalKeys)
      .sort()
      .forEach((key) => {
        const beforeValue = resolveCanonicalValue(previousPayload || {}, key);
        const afterValue = resolveCanonicalValue(currentPayload || {}, key);
        if (JSON.stringify(beforeValue) !== JSON.stringify(afterValue)) {
          changed.push(key);
        }
      });
    return changed;
  }

  function resolveFieldLabelMap() {
    const labels = new Map();
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const fieldKey = canonicalFieldKey(container.dataset.fieldKey || '');
      const fieldId = String(container.dataset.fieldId || '').trim();
      const labelNode = container.querySelector('.subject-form-flat-field__label');
      const rawLabel = labelNode ? String(labelNode.textContent || '') : fieldKey;
      const cleanedLabel = rawLabel.replace(/\*/g, '').trim() || fieldKey;
      if (fieldKey) {
        labels.set(fieldKey, cleanedLabel);
      }
      if (fieldId) {
        labels.set(`field_${fieldId}`, cleanedLabel);
      }
    });
    return labels;
  }

  function loadPreviousSubmittedPayload() {
    const payloadNode = document.getElementById('datacapture-previous-submitted-payload');
    if (!payloadNode) {
      return null;
    }
    try {
      const parsed = JSON.parse(payloadNode.textContent || '{}');
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (error) {
      console.error(error);
      return null;
    }
  }

  function formatEntryDate(now) {
    const pad = (value) => String(value).padStart(2, '0');
    const day = pad(now.getDate());
    const month = pad(now.getMonth() + 1);
    const year = now.getFullYear();
    const hour = pad(now.getHours());
    const minute = pad(now.getMinutes());
    return `${day}-${month}-${year} ${hour}:${minute}`;
  }

  function openChangeReasonModal(changedFieldKeys, fieldLabelMap) {
    if (
      !reasonModalBackdrop ||
      !reasonRowsHost ||
      !reasonSubmitButton ||
      !reasonCancelButton ||
      changedFieldKeys.length === 0
    ) {
      return Promise.resolve([]);
    }

    const nowLabel = formatEntryDate(new Date());
    reasonRowsHost.innerHTML = '';
    changedFieldKeys.forEach((fieldKey) => {
      const row = document.createElement('tr');

      const dateCell = document.createElement('td');
      dateCell.textContent = nowLabel;

      const fieldCell = document.createElement('td');
      fieldCell.textContent = fieldLabelMap.get(fieldKey) || fieldKey;

      const reasonCell = document.createElement('td');
      const reasonInput = document.createElement('input');
      reasonInput.className = 'subject-detail-screen__reason-input';
      reasonInput.type = 'text';
      reasonInput.setAttribute('data-field-key', fieldKey);
      reasonInput.required = true;
      reasonCell.appendChild(reasonInput);

      row.appendChild(dateCell);
      row.appendChild(fieldCell);
      row.appendChild(reasonCell);
      reasonRowsHost.appendChild(row);
    });

    reasonModalBackdrop.hidden = false;

    return new Promise((resolve) => {
      const cleanup = () => {
        reasonSubmitButton.removeEventListener('click', onSubmit);
        reasonCancelButton.removeEventListener('click', onCancel);
        reasonModalBackdrop.removeEventListener('click', onBackdropClick);
      };

      const closeWith = (value) => {
        cleanup();
        reasonModalBackdrop.hidden = true;
        reasonRowsHost.innerHTML = '';
        resolve(value);
      };

      const onCancel = () => {
        closeWith(null);
      };

      const onBackdropClick = (event) => {
        if (event.target === reasonModalBackdrop) {
          closeWith(null);
        }
      };

      const onSubmit = () => {
        const rows = reasonRowsHost.querySelectorAll('input[data-field-key]');
        const reasons = [];
        for (const input of rows) {
          const reason = String(input.value || '').trim();
          if (!reason) {
            input.focus();
            showNotification('Please enter reason for every changed field.', 'error');
            return;
          }
          const fieldKey = canonicalFieldKey(input.dataset.fieldKey || '');
          reasons.push({
            field_key: fieldKey,
            field_label: fieldLabelMap.get(fieldKey) || fieldKey,
            reason,
          });
        }
        closeWith(reasons);
      };

      reasonSubmitButton.addEventListener('click', onSubmit);
      reasonCancelButton.addEventListener('click', onCancel);
      reasonModalBackdrop.addEventListener('click', onBackdropClick);
    });
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

    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }

    if (!response.ok) {
      let message = 'Request failed';
      if (payload && Array.isArray(payload.error) && payload.error.length > 0) {
        message = payload.error.join(' ');
      }
      throw new Error(message);
    }

    return payload;
  }

  saveButton.addEventListener('click', async () => {
    const requiresConfirmation = pageStatus === 'submitted';
    if (requiresConfirmation && !window.confirm(confirmationMessage)) {
      showNotification('Cancelled', 'error');
      return;
    }
    if (!validateBeforePersist()) {
      return;
    }
    showLoading(loadingOverlay?.dataset.saveMessage);
    setButtonsEnabled(false);
    setButtonPending(saveButton, 'Saving...');
    try {
      const result = await postJson(saveUrl, collectFormPayload());
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      showNotification('Saved successfully.', 'success');
      if (shouldReloadWithLatestEntry(result)) {
        window.setTimeout(() => {
          window.location.reload();
        }, 120);
        return;
      }
      if (applyLockState()) {
        return;
      }
    } catch (error) {
      showNotification(error?.message || 'Save failed.', 'error');
      console.error(error);
    } finally {
      hideLoading();
      clearButtonPending(saveButton);
      if (!isPageLocked(pageStatus)) {
        setButtonsEnabled(true);
      }
    }
  });

  resetButton.addEventListener('click', () => {
    resetInputs();
    showNotification('Reset done.', 'success');
  });

  submitButton.addEventListener('click', async () => {
    if (!validateBeforePersist()) {
      return;
    }

    const payloadObject = collectFormPayloadObject();
    const previousSubmittedPayload = loadPreviousSubmittedPayload();
    let submitReasons = [];

    if (previousSubmittedPayload) {
      const changedFieldKeys = resolveChangedFieldKeys(previousSubmittedPayload, payloadObject);
      if (changedFieldKeys.length > 0) {
        const fieldLabelMap = resolveFieldLabelMap();
        const modalReasons = await openChangeReasonModal(changedFieldKeys, fieldLabelMap);
        if (modalReasons === null) {
          showNotification('Cancelled', 'error');
          return;
        }
        submitReasons = modalReasons;
      }
    }

    showLoading(loadingOverlay?.dataset.submitMessage);
    setButtonsEnabled(false);
    setButtonPending(submitButton, 'Submitting...');
    try {
      const submitPayload = JSON.stringify({
        data: payloadObject,
        change_reasons: submitReasons,
      });
      const result = await postJson(submitUrl, submitPayload);
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      showNotification('Submitted successfully.', 'success');
      if (shouldReloadWithLatestEntry(result)) {
        window.setTimeout(() => {
          window.location.reload();
        }, 120);
        return;
      }
      if (applyLockState()) {
        return;
      }
    } catch (error) {
      showNotification(error?.message || 'Submit failed.', 'error');
      console.error(error);
    } finally {
      hideLoading();
      clearButtonPending(submitButton);
      if (!isPageLocked(pageStatus)) {
        setButtonsEnabled(true);
      }
    }
  });

  if (deleteDraftButton && deleteDraftUrl) {
    deleteDraftButton.addEventListener('click', async () => {
      if (!window.confirm(deleteDraftConfirmationMessage)) {
        showNotification('Cancelled', 'error');
        return;
      }
      showLoading(loadingOverlay?.dataset.deleteMessage);
      setButtonsEnabled(false);
      setButtonPending(deleteDraftButton, 'Deleting...');
      try {
        const result = await postJson(deleteDraftUrl, '{}');
        pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
        formRoot.dataset.pageStatus = pageStatus;
        showNotification('Draft deleted successfully.', 'success');
        window.setTimeout(() => {
          window.location.reload();
        }, 120);
      } catch (error) {
        showNotification(error?.message || 'Delete draft failed.', 'error');
        console.error(error);
      } finally {
        hideLoading();
        clearButtonPending(deleteDraftButton);
        if (!isPageLocked(pageStatus)) {
          setButtonsEnabled(true);
        }
      }
    });
  }
})();
