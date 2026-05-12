(function () {
  const modules = window.DatacaptureSubjectDetailModules || {};
  const shared = modules.shared || {};
  const validationModuleFactory = modules.validation;
  const reasonModalModuleFactory = modules.reasonModal;
  const network = modules.network || {};
  const radioControlModule = (modules.controls || {}).radio || {};
  const textControlModule = (modules.controls || {}).text || {};
  const numberControlModule = (modules.controls || {}).number || {};
  const textareaControlModule = (modules.controls || {}).textarea || {};
  const selectControlModule = (modules.controls || {}).select || {};
  const multiSelectControlModule = (modules.controls || {}).multiSelect || {};
  const datePickerControlModule = (modules.controls || {}).datePicker || {};
  const datetimeControlModule = (modules.controls || {}).datetime || {};

  const formPanel = document.querySelector('.subject-form-panel');
  const fieldScope = formPanel || document;
  const notificationDurationMs = 2600;
  const datePartSuffixes = shared.datePartSuffixes || ['__day', '__month', '__year', '__time'];
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
          if (
            input.classList.contains('subject-date-picker__input--day') ||
            input.classList.contains('subject-date-picker__input--month') ||
            input.classList.contains('subject-date-picker__input--year') ||
            input.classList.contains('subject-date-picker__input--time')
          ) {
            return;
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

  function collectFormPayloadObject() {
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      datePickerControlModule.syncDateCompositeInput?.(container);
      datetimeControlModule.syncDatetimeCompositeInput?.(container);
    });
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

  function clonePayloadObject(source) {
    if (!source || typeof source !== 'object') {
      return null;
    }
    try {
      return JSON.parse(JSON.stringify(source));
    } catch (error) {
      console.error(error);
      return { ...source };
    }
  }

  function resolvePayloadValue(inputName, payload) {
    if (!payload || !Object.prototype.hasOwnProperty.call(payload, inputName)) {
      return null;
    }
    return payload[inputName];
  }

  function isTruthyCheckboxValue(rawValue) {
    if (typeof rawValue === 'boolean') {
      return rawValue;
    }
    if (typeof rawValue === 'number') {
      return rawValue !== 0;
    }
    const normalized = String(rawValue ?? '')
      .trim()
      .toLowerCase();
    return ['1', 'true', 'yes', 'on'].includes(normalized);
  }

  function toCheckboxValueSet(rawValue) {
    if (Array.isArray(rawValue)) {
      return new Set(rawValue.map((item) => String(item ?? '')));
    }
    if (typeof rawValue === 'string') {
      return new Set(
        rawValue
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item),
      );
    }
    return new Set();
  }

  function applyPayloadToInputs(payload) {
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      if (!input.name || input.disabled) {
        return;
      }

      const payloadValue = resolvePayloadValue(input.name, payload);

      if (input.matches('input[type="hidden"][data-date-composite-input]')) {
        const container = input.closest('[data-field-key]');
        const compositeType = String(input.dataset.dateCompositeType || '').trim().toLowerCase();
        const compositeValue = payloadValue == null ? '' : String(payloadValue);
        if (compositeType === 'datetime') {
          datetimeControlModule.applyDatetimeCompositeValue?.(container, compositeValue);
          datetimeControlModule.syncDatetimeCompositeInput?.(container);
        } else {
          datePickerControlModule.applyDateCompositeValue?.(container, compositeValue);
          datePickerControlModule.syncDateCompositeInput?.(container);
        }
        return;
      }

      if (input.type === 'radio') {
        input.checked = payloadValue !== null && String(payloadValue ?? '') === String(input.value ?? '');
        return;
      }

      if (input.type === 'checkbox') {
        const checkboxes = Array.from(fieldScope.querySelectorAll('input[type="checkbox"]')).filter(
          (checkbox) => checkbox.name === input.name,
        );
        if (checkboxes.length > 1) {
          const selectedValues = toCheckboxValueSet(payloadValue);
          input.checked = selectedValues.has(String(input.value ?? ''));
          return;
        }
        input.checked = payloadValue !== null ? isTruthyCheckboxValue(payloadValue) : false;
        return;
      }

      if (input instanceof HTMLSelectElement && input.multiple) {
        const selectedValues = toCheckboxValueSet(payloadValue);
        Array.from(input.options).forEach((option) => {
          option.selected = selectedValues.has(String(option.value ?? ''));
        });
        return;
      }

      if (payloadValue === null || payloadValue === undefined) {
        input.value = '';
        return;
      }
      input.value = String(payloadValue);
    });
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      datePickerControlModule.syncDateCompositeInput?.(container);
      datetimeControlModule.syncDatetimeCompositeInput?.(container);
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

  const canonicalFieldKey = shared.canonicalFieldKey || ((raw) => String(raw ?? '').trim());
  const normalizeComparableValue = shared.normalizeComparableValue || ((raw) => String(raw ?? ''));
  const resolveChangedFieldKeys = shared.resolveChangedFieldKeys || (() => []);
  const resolveFieldLabelMap = shared.resolveFieldLabelMap || (() => new Map());
  const loadCurrentDataPayload = shared.loadCurrentDataPayload || (() => ({}));
  const loadPreviousDataPayload = shared.loadPreviousDataPayload || (() => null);
  const formatEntryDate = shared.formatEntryDate || (() => '');

  const initialCurrentDataPayload = loadCurrentDataPayload();
  const initialPreviousDataPayload = loadPreviousDataPayload();
  const resetTrackpointPayloadSource = shared.loadPayloadByScriptId?.(
    'datacapture-reset-trackpoint-data-payload',
  );
  const resetTrackpointDataPayload =
    clonePayloadObject(resetTrackpointPayloadSource) ||
    clonePayloadObject(initialCurrentDataPayload);
  console.log('initialCurrentDataPayload', initialCurrentDataPayload);
  console.log('initialPreviousDataPayload', initialPreviousDataPayload);
  console.log('resetTrackpointDataPayload', resetTrackpointDataPayload);

  const validation = validationModuleFactory?.createValidationModule({
    fieldScope,
    showNotification,
    parseNumericValue,
  });

  const reasonModal = reasonModalModuleFactory?.createReasonModalModule({
    reasonModalBackdrop,
    reasonRowsHost,
    reasonSubmitButton,
    reasonCancelButton,
    showNotification,
    canonicalFieldKey,
    formatEntryDate,
  });

  if (applyLockState()) {
    return;
  }

  saveButton.addEventListener('click', async () => {
    const requiresConfirmation = pageStatus === 'submitted';
    if (requiresConfirmation && !window.confirm(confirmationMessage)) {
      showNotification('Cancelled', 'error');
      return;
    }
    if (!validation?.validateBeforePersist?.()) {
      return;
    }
    showLoading(loadingOverlay?.dataset.saveMessage);
    setButtonsEnabled(false);
    setButtonPending(saveButton, 'Saving...');
    try {
      const result = await network.postJson(saveUrl, collectFormPayload());
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
    if (resetTrackpointDataPayload) {
      applyPayloadToInputs(resetTrackpointDataPayload);
    } else {
      resetInputs();
    }
    refreshRadioDiffMarkers();
    showNotification('Reset done.', 'success');
  });

  submitButton.addEventListener('click', async () => {
    if (!validation?.validateBeforePersist?.()) {
      return;
    }

    const payloadObject = collectFormPayloadObject();
    const previousSubmittedPayload = initialPreviousDataPayload;
    let submitReasons = [];

    if (previousSubmittedPayload) {
      const changedFieldKeys = resolveChangedFieldKeys(previousSubmittedPayload, payloadObject);
      if (changedFieldKeys.length > 0) {
        const fieldLabelMap = resolveFieldLabelMap(fieldScope);
        const modalReasons = await reasonModal?.openChangeReasonModal?.(changedFieldKeys, fieldLabelMap);
        if (modalReasons === null) {
          showNotification('Cancelled', 'error');
          return;
        }
        submitReasons = modalReasons || [];
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
      const result = await network.postJson(submitUrl, submitPayload);
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      showNotification('Submitted successfully.', 'success');
      window.setTimeout(() => {
        window.location.reload();
      }, 120);
      return;
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
        const result = await network.postJson(deleteDraftUrl, '{}');
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

  function refreshSubmittedDiffMarkers() {
    const markerContext = {
      fieldScope,
      previousSubmittedPayload: initialPreviousDataPayload,
      currentPayload: collectFormPayloadObject(),
      initialCurrentPayload: initialCurrentDataPayload,
      canonicalFieldKey,
      normalizeComparableValue,
      datePartSuffixes,
    };
    radioControlModule.applySubmittedDiffRadioMarkers?.(markerContext);
    textControlModule.applySubmittedDiffTextMarkers?.(markerContext);
    numberControlModule.applySubmittedDiffNumberMarkers?.(markerContext);
    textareaControlModule.applySubmittedDiffTextareaMarkers?.(markerContext);
    selectControlModule.applySubmittedDiffSelectMarkers?.(markerContext);
    multiSelectControlModule.applySubmittedDiffMultiSelectMarkers?.(markerContext);
  }

  refreshSubmittedDiffMarkers();
  fieldScope.addEventListener('input', refreshSubmittedDiffMarkers);
  fieldScope.addEventListener('change', refreshSubmittedDiffMarkers);
})();
