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
  const select2ControlModule = (modules.controls || {}).select2 || {};
  const multiSelectControlModule = (modules.controls || {}).multiSelect || {};
  const datePickerControlModule = (modules.controls || {}).datePicker || {};
  const dateTextControlModule = (modules.controls || {}).dateText || {};
  const datetimeControlModule = (modules.controls || {}).datetime || {};

  const formPanel = document.querySelector('.subject-form-panel');
  const fieldScope = formPanel || document;
  const notificationDurationMs = 2600;
  const datePartSuffixes = shared.datePartSuffixes || ['__day', '__month', '__year', '__time'];
  /* Editable until terminal states. */
  const lockStatuses = new Set(['verified', 'finalized', 'locked']);

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
  const repeatTableTemplateRows = new WeakMap();
  const repeatSectionTemplates = new Map();

  function ensureEditableInputs() {
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const fieldKey = (container.dataset.fieldKey || '').trim();
      if (!fieldKey) {
        return;
      }
      container.querySelectorAll('input, textarea, select').forEach((input) => {
        if (!input.name) {
          if (input.hasAttribute('data-field-lookup-label-input')) {
            input.disabled = false;
            input.removeAttribute('disabled');
            if ('readOnly' in input) {
              input.readOnly = false;
            }
            input.removeAttribute('readonly');
            return;
          }
          if (
            input.hasAttribute('data-date-text-input') ||
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
    select2ControlModule.initializeSelect2LookupControls?.(fieldScope);
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
  const unsavedChangesMessage =
    formRoot.dataset.unsavedChangesMessage ||
    'You have unsaved changes. Are you sure you want to leave this page?';
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

  function mergeLabelOnlyFieldValuesIntoPayload(payload) {
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      const controlType = String(container.dataset.fieldControlType || '').trim().toLowerCase();
      if (controlType !== 'label_only') {
        return;
      }
      const fieldKey = String(container.dataset.fieldKey || '').trim();
      if (!fieldKey) {
        return;
      }
      const controls = container.querySelectorAll('input, textarea, select');
      let raw = '';
      for (let i = 0; i < controls.length; i += 1) {
        const el = controls[i];
        if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement)) {
          continue;
        }
        if (el instanceof HTMLInputElement) {
          const t = el.type;
          if (t === 'hidden' || t === 'button' || t === 'submit' || t === 'checkbox' || t === 'radio') {
            continue;
          }
        }
        raw = el.value;
        break;
      }
      const trimmed = String(raw ?? '').trim();
      if (!trimmed) {
        payload[fieldKey] = null;
        return;
      }
      const numeric = parseNumericValue(trimmed);
      payload[fieldKey] = numeric !== null ? numeric : trimmed;
    });
  }

  function collectFormPayloadObject(options = {}) {
    fieldScope.querySelectorAll('[data-field-key]').forEach((container) => {
      datePickerControlModule.syncDateCompositeInput?.(container);
      dateTextControlModule.syncDateTextInput?.(container);
      datetimeControlModule.syncDatetimeCompositeInput?.(container);
    });
    select2ControlModule.syncSelect2LookupControls?.(fieldScope);
    const payload = {};
    const handledCheckboxNames = new Set();
    fieldScope.querySelectorAll('input, textarea, select').forEach((input) => {
      if (!input.name) {
        return;
      }
      const disabledReason = String(input.dataset.datacaptureDisabledReason || '').trim();
      if (input.disabled && disabledReason !== 'readonly') {
        return;
      }
      if (input.type === 'checkbox') {
        if (handledCheckboxNames.has(input.name)) {
          return;
        }
        const checkboxes = Array.from(fieldScope.querySelectorAll('input[type="checkbox"]')).filter(
          (checkbox) => checkbox.name === input.name,
        );
        handledCheckboxNames.add(input.name);
        if (checkboxes.length > 1) {
          payload[input.name] = checkboxes
            .filter((checkbox) => checkbox.checked)
            .map((checkbox) => String(checkbox.value ?? ''))
            .filter((value) => value)
            .join(',');
          return;
        }
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
    mergeLabelOnlyFieldValuesIntoPayload(payload);
    if (options.includeLookupMetadata) {
      payload._field_lookup_labels = select2ControlModule.collectLookupLabels?.(fieldScope) || {};
    }
    return payload;
  }

  function collectFormPayload() {
    return JSON.stringify(collectFormPayloadObject({ includeLookupMetadata: true }));
  }

  function stablePayloadString(value) {
    if (Array.isArray(value)) {
      return `[${value.map((item) => stablePayloadString(item)).join(',')}]`;
    }
    if (value && typeof value === 'object') {
      return `{${Object.keys(value)
        .sort()
        .map((key) => `${JSON.stringify(key)}:${stablePayloadString(value[key])}`)
        .join(',')}}`;
    }
    return JSON.stringify(value ?? null);
  }

  function collectDirtyPayloadObject() {
    return collectFormPayloadObject();
  }

  let allowNavigationWithoutPrompt = false;
  let dirtyBaselinePayloadString = stablePayloadString({});

  function currentDirtyPayloadString() {
    return stablePayloadString(collectDirtyPayloadObject());
  }

  function hasUnsavedChanges() {
    return currentDirtyPayloadString() !== dirtyBaselinePayloadString;
  }

  function markCurrentPayloadClean() {
    dirtyBaselinePayloadString = currentDirtyPayloadString();
  }

  function allowNextNavigation() {
    allowNavigationWithoutPrompt = true;
  }

  function confirmDiscardUnsavedChanges() {
    if (allowNavigationWithoutPrompt || !hasUnsavedChanges()) {
      return true;
    }
    if (!window.confirm(unsavedChangesMessage)) {
      return false;
    }
    allowNextNavigation();
    return true;
  }

  function isGuardedNavigationLink(link) {
    if (!link || !link.href) {
      return false;
    }
    if (link.target && link.target.toLowerCase() !== '_self') {
      return false;
    }
    if (link.hasAttribute('download')) {
      return false;
    }
    if (link.hasAttribute('data-eventinstance-file-preview-link')) {
      return false;
    }
    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
      return false;
    }
    return true;
  }

  function bindUnsavedChangesGuard() {
    window.DatacaptureUnsavedChangesGuard = {
      hasUnsavedChanges,
      confirmDiscardUnsavedChanges,
      allowNextNavigation,
      markCurrentPayloadClean,
    };

    window.addEventListener('beforeunload', (event) => {
      if (allowNavigationWithoutPrompt || !hasUnsavedChanges()) {
        return;
      }
      event.preventDefault();
      event.returnValue = '';
    });

    document.addEventListener('click', (event) => {
      const link = event.target?.closest?.('a[href]');
      if (!isGuardedNavigationLink(link)) {
        return;
      }
      if (confirmDiscardUnsavedChanges()) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
    }, true);

    document.addEventListener('submit', (event) => {
      if (confirmDiscardUnsavedChanges()) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
    }, true);
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

      if (input.matches('input[type="hidden"][data-date-text-composite-input]')) {
        const container = input.closest('[data-field-key]');
        const compositeValue = payloadValue == null ? '' : String(payloadValue);
        dateTextControlModule.applyDateTextCompositeValue?.(container, compositeValue);
        dateTextControlModule.syncDateTextInput?.(container);
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
      dateTextControlModule.syncDateTextInput?.(container);
      datetimeControlModule.syncDatetimeCompositeInput?.(container);
    });
    select2ControlModule.applyPayloadToSelect2Controls?.(fieldScope, payload);
    select2ControlModule.syncSelect2LookupControls?.(fieldScope);
  }

  function baseRepeatFieldKey(rawKey) {
    return String(rawKey || '').replace(/__repeat_\d+$/, '').trim();
  }

  function reasonRequiredLookupKeys(rawKey) {
    const normalized = String(rawKey || '').trim();
    const withoutDatePart = datePartSuffixes.reduce((value, suffix) => (
      value.endsWith(suffix) ? value.slice(0, -suffix.length) : value
    ), normalized);
    const withoutRepeat = baseRepeatFieldKey(withoutDatePart);
    return new Set([normalized, withoutDatePart, withoutRepeat, canonicalFieldKey(withoutRepeat)].filter((key) => key));
  }

  function repeatFieldKey(baseKey, repeatIndex) {
    const normalizedBaseKey = baseRepeatFieldKey(baseKey);
    if (!normalizedBaseKey) {
      return '';
    }
    if (repeatIndex <= 1) {
      return normalizedBaseKey;
    }
    return `${normalizedBaseKey}__repeat_${repeatIndex}`;
  }

  function parseRepeatMax(rawValue) {
    const parsed = Number.parseInt(String(rawValue || '').trim(), 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === 'function') {
      return window.CSS.escape(value);
    }
    return String(value || '').replace(/["\\]/g, '\\$&');
  }

  function clearClonedInput(input) {
    if (input instanceof HTMLInputElement) {
      if (input.type === 'checkbox' || input.type === 'radio') {
        input.checked = false;
        return;
      }
      if (input.type !== 'button' && input.type !== 'submit') {
        input.value = '';
      }
      return;
    }
    if (input instanceof HTMLSelectElement) {
      Array.from(input.options).forEach((option) => {
        option.selected = false;
      });
      input.selectedIndex = 0;
      return;
    }
    if (input instanceof HTMLTextAreaElement) {
      input.value = '';
    }
  }

  function rewriteClonedIds(section, repeatIndex) {
    const idMap = new Map();
    section.querySelectorAll('[id]').forEach((node) => {
      const oldId = node.id;
      const newId = `${oldId}__repeat_${repeatIndex}`;
      idMap.set(oldId, newId);
      node.id = newId;
    });
    idMap.forEach((newId, oldId) => {
      section.querySelectorAll(`[list="${cssEscape(oldId)}"]`).forEach((node) => {
        node.setAttribute('list', newId);
      });
      section.querySelectorAll(`[aria-labelledby="${cssEscape(oldId)}"]`).forEach((node) => {
        node.setAttribute('aria-labelledby', newId);
      });
    });
  }

  function rewriteClonedSectionFields(section, repeatIndex) {
    section.classList.remove('subject-form-field--has-open-query');
    section.querySelectorAll('.subject-form-field--has-open-query').forEach((node) => {
      node.classList.remove('subject-form-field--has-open-query');
    });
    section.querySelectorAll('[data-query-thread-modal-trigger], [data-query-thread-badge]').forEach((node) => {
      node.remove();
    });
    section.querySelectorAll('[data-repeat-table-row-delete]').forEach((node) => {
      node.removeAttribute('data-repeat-table-delete-bound');
    });
    section.querySelectorAll('[data-repeat-section-delete]').forEach((node) => {
      node.removeAttribute('data-repeat-section-delete-bound');
    });
    rewriteClonedIds(section, repeatIndex);
    section.querySelectorAll('[data-field-key]').forEach((container) => {
      const baseKey = baseRepeatFieldKey(
        container.dataset.repeatBaseFieldKey ||
        container.dataset.fieldKey ||
        '',
      );
      const repeatedKey = repeatFieldKey(baseKey, repeatIndex);
      if (!repeatedKey) {
        return;
      }
      container.dataset.repeatBaseFieldKey = baseKey;
      container.dataset.fieldKey = repeatedKey;
      container.querySelectorAll('input, textarea, select').forEach((input) => {
        if (input.hasAttribute('data-field-lookup-label-input')) {
          input.removeAttribute('name');
          clearClonedInput(input);
          return;
        }
        if (
          input.hasAttribute('data-date-text-input') ||
          input.classList.contains('subject-date-picker__input--day') ||
          input.classList.contains('subject-date-picker__input--month') ||
          input.classList.contains('subject-date-picker__input--year') ||
          input.classList.contains('subject-date-picker__input--time')
        ) {
          input.removeAttribute('name');
          clearClonedInput(input);
          return;
        }
        input.name = repeatedKey;
        clearClonedInput(input);
      });
    });
  }

  function updateRepeatSectionButton(button, currentCount, maxRepeats) {
    if (!button) {
      return;
    }
    button.dataset.currentRepeats = String(currentCount);
    if (maxRepeats !== null && currentCount >= maxRepeats) {
      button.hidden = true;
      button.disabled = true;
      return;
    }
    button.hidden = false;
    button.disabled = false;
  }

  function repeatTableRows(sourceSection) {
    const tableBody = sourceSection.querySelector('[data-repeat-table-body]');
    if (!tableBody) {
      return [];
    }
    return Array.from(tableBody.querySelectorAll('[data-repeat-table-row]'));
  }

  function repeatTableVisibleRowCount(sourceSection) {
    return repeatTableRows(sourceSection).length;
  }

  function repeatTableMaxRepeatIndex(sourceSection) {
    return repeatTableRows(sourceSection).reduce((maxValue, row) => {
      const repeatIndex = Number.parseInt(row.dataset.repeatInstanceIndex || '0', 10);
      if (!Number.isFinite(repeatIndex)) {
        return maxValue;
      }
      return Math.max(maxValue, repeatIndex);
    }, 0);
  }

  function initializeRepeatTableState(sourceSection) {
    if (!sourceSection || sourceSection.dataset.sectionLayoutType !== 'repeat_table') {
      return;
    }
    const rows = repeatTableRows(sourceSection);
    if (rows.length && !repeatTableTemplateRows.has(sourceSection)) {
      repeatTableTemplateRows.set(sourceSection, rows[0].cloneNode(true));
    }
    const highestRenderedIndex = repeatTableMaxRepeatIndex(sourceSection);
    const configuredCurrentRepeats = Number.parseInt(sourceSection.dataset.currentRepeats || '0', 10);
    const lastRepeatIndex = Math.max(
      highestRenderedIndex,
      Number.isFinite(configuredCurrentRepeats) ? configuredCurrentRepeats : 0,
    );
    if (!sourceSection.dataset.nextRepeatIndex) {
      sourceSection.dataset.nextRepeatIndex = String(lastRepeatIndex + 1);
    }
    sourceSection.dataset.currentRepeats = String(rows.length);
    const button = sourceSection.querySelector('[data-repeat-section-add]');
    updateRepeatSectionButton(button, rows.length, parseRepeatMax(sourceSection.dataset.maxRepeats));
  }

  function initializeRepeatTableStates() {
    fieldScope
      .querySelectorAll('[data-section-layout-type="repeat_table"]')
      .forEach((section) => initializeRepeatTableState(section));
  }

  function nextRepeatTableIndex(sourceSection) {
    const cachedNextIndex = Number.parseInt(sourceSection.dataset.nextRepeatIndex || '0', 10);
    if (Number.isFinite(cachedNextIndex) && cachedNextIndex > 0) {
      return cachedNextIndex;
    }
    return Math.max(repeatTableMaxRepeatIndex(sourceSection), 0) + 1;
  }

  function renumberRepeatTableDisplayRows(sourceSection) {
    repeatTableRows(sourceSection).forEach((row, index) => {
      const indexCell = row.querySelector('.subject-form-repeat-table-row__index');
      if (indexCell) {
        indexCell.textContent = String(index + 1);
      }
    });
  }

  function appendRepeatTableRow(sourceSection, button, nextRepeatIndex, maxRepeats) {
    const tableBody = sourceSection.querySelector('[data-repeat-table-body]');
    if (!tableBody) {
      return false;
    }
    const rows = Array.from(tableBody.querySelectorAll('[data-repeat-table-row]'));
    const sourceRow = rows[rows.length - 1] || repeatTableTemplateRows.get(sourceSection);
    if (!sourceRow) {
      return false;
    }

    const clonedRow = sourceRow.cloneNode(true);
    clonedRow.dataset.repeatInstanceIndex = String(nextRepeatIndex);
    const indexCell = clonedRow.querySelector('.subject-form-repeat-table-row__index');
    if (indexCell) {
      indexCell.textContent = String(rows.length + 1);
    }
    rewriteClonedSectionFields(clonedRow, nextRepeatIndex);
    tableBody.appendChild(clonedRow);

    sourceSection.dataset.currentRepeats = String(rows.length + 1);
    sourceSection.dataset.nextRepeatIndex = String(nextRepeatIndex + 1);
    dateTextControlModule.initializeDateTextControls?.(clonedRow);
    updateRepeatSectionButton(button, rows.length + 1, maxRepeats);
    return true;
  }

  function bindRepeatTableRowDeleteButtons() {
    fieldScope.querySelectorAll('[data-repeat-table-row-delete]').forEach((button) => {
      if (button.dataset.repeatTableDeleteBound === '1') {
        return;
      }
      button.dataset.repeatTableDeleteBound = '1';
      button.addEventListener('click', () => {
        const row = button.closest('[data-repeat-table-row]');
        const sourceSection = button.closest('[data-section-layout-type="repeat_table"]');
        if (!row || !sourceSection) {
          return;
        }
        if (!repeatTableTemplateRows.has(sourceSection)) {
          repeatTableTemplateRows.set(sourceSection, row.cloneNode(true));
        }
        row.remove();
        const visibleRowCount = repeatTableVisibleRowCount(sourceSection);
        sourceSection.dataset.currentRepeats = String(visibleRowCount);
        renumberRepeatTableDisplayRows(sourceSection);
        updateRepeatSectionButton(
          sourceSection.querySelector('[data-repeat-section-add]'),
          visibleRowCount,
          parseRepeatMax(sourceSection.dataset.maxRepeats),
        );
      });
    });
  }

  function standardRepeatSectionId(section) {
    return String(section?.dataset?.sectionTemplateId || '').trim();
  }

  function standardRepeatSections(templateId, options = {}) {
    if (!templateId) {
      return [];
    }
    const includeDeleted = Boolean(options.includeDeleted);
    return Array.from(
      fieldScope.querySelectorAll(
        `.subject-form-section[data-section-template-id="${cssEscape(templateId)}"]`,
      ),
    ).filter((section) => (
      section.dataset.sectionLayoutType !== 'repeat_table' &&
      (includeDeleted || section.dataset.repeatDeleted !== '1')
    ));
  }

  function storeRepeatSectionTemplate(section) {
    const templateId = standardRepeatSectionId(section);
    if (!templateId || repeatSectionTemplates.has(templateId)) {
      return;
    }
    const template = section.cloneNode(true);
    template.classList.remove('subject-form-section--repeat-deleted');
    template.removeAttribute('data-repeat-deleted');
    template.querySelectorAll('[data-repeat-section-bound], [data-repeat-section-delete-bound]').forEach((node) => {
      node.removeAttribute('data-repeat-section-bound');
      node.removeAttribute('data-repeat-section-delete-bound');
    });
    repeatSectionTemplates.set(templateId, template);
  }

  function standardRepeatSectionMaxIndex(templateId) {
    return standardRepeatSections(templateId, { includeDeleted: true }).reduce((maxValue, section) => {
      const repeatIndex = Number.parseInt(section.dataset.repeatInstanceIndex || '0', 10);
      if (!Number.isFinite(repeatIndex)) {
        return maxValue;
      }
      return Math.max(maxValue, repeatIndex);
    }, 0);
  }

  function standardRepeatSectionNextIndex(section) {
    const templateId = standardRepeatSectionId(section);
    const cachedNextIndex = Number.parseInt(section.dataset.nextRepeatIndex || '0', 10);
    if (Number.isFinite(cachedNextIndex) && cachedNextIndex > 0) {
      return cachedNextIndex;
    }
    return standardRepeatSectionMaxIndex(templateId) + 1;
  }

  function syncStandardRepeatSectionState(templateId, nextRepeatIndex = null) {
    const sections = standardRepeatSections(templateId, { includeDeleted: true });
    const visibleCount = standardRepeatSections(templateId).length;
    const resolvedNextRepeatIndex = nextRepeatIndex || standardRepeatSectionMaxIndex(templateId) + 1;
    sections.forEach((section) => {
      section.dataset.currentRepeats = String(visibleCount);
      section.dataset.nextRepeatIndex = String(resolvedNextRepeatIndex);
      const button = section.querySelector('[data-repeat-section-add]');
      updateRepeatSectionButton(button, visibleCount, parseRepeatMax(section.dataset.maxRepeats));
    });
  }

  function initializeStandardRepeatSectionStates() {
    const templateIds = new Set();
    fieldScope.querySelectorAll('.subject-form-section[data-section-template-id]').forEach((section) => {
      if (section.dataset.sectionLayoutType === 'repeat_table') {
        return;
      }
      if (!section.querySelector('[data-repeat-section-delete]')) {
        return;
      }
      storeRepeatSectionTemplate(section);
      const templateId = standardRepeatSectionId(section);
      if (templateId) {
        templateIds.add(templateId);
      }
    });
    templateIds.forEach((templateId) => syncStandardRepeatSectionState(templateId));
  }

  function disableRepeatSectionForPayload(section) {
    section.dataset.repeatDeleted = '1';
    section.classList.add('subject-form-section--repeat-deleted');
    section.querySelectorAll('input, textarea, select').forEach((input) => {
      clearClonedInput(input);
      input.disabled = true;
      input.dataset.datacaptureDisabledReason = 'deleted-repeat-section';
    });
  }

  function restoreRepeatSectionFromTemplate(placeholder, nextRepeatIndex, maxRepeats) {
    const templateId = standardRepeatSectionId(placeholder);
    const template = repeatSectionTemplates.get(templateId);
    if (!template) {
      return false;
    }
    const restoredSection = template.cloneNode(true);
    restoredSection.classList.remove('subject-form-section--repeat-deleted');
    restoredSection.removeAttribute('data-repeat-deleted');
    restoredSection.dataset.repeatInstanceIndex = String(nextRepeatIndex);
    restoredSection.dataset.currentRepeats = '1';
    restoredSection.dataset.nextRepeatIndex = String(nextRepeatIndex + 1);
    rewriteClonedSectionFields(restoredSection, nextRepeatIndex);
    const restoredButton = restoredSection.querySelector('[data-repeat-section-add]');
    updateRepeatSectionButton(restoredButton, 1, maxRepeats);
    placeholder.insertAdjacentElement('beforebegin', restoredSection);
    placeholder.remove();
    dateTextControlModule.initializeDateTextControls?.(restoredSection);
    ensureEditableInputs();
    select2ControlModule.initializeSelect2LookupControls?.(restoredSection);
    syncStandardRepeatSectionState(templateId, nextRepeatIndex + 1);
    bindRepeatSectionDeleteButtons();
    bindRepeatSectionButtons();
    return true;
  }

  function bindRepeatSectionDeleteButtons() {
    fieldScope.querySelectorAll('[data-repeat-section-delete]').forEach((button) => {
      if (button.dataset.repeatSectionDeleteBound === '1') {
        return;
      }
      button.dataset.repeatSectionDeleteBound = '1';
      button.addEventListener('click', () => {
        const section = button.closest('.subject-form-section');
        if (!section || section.dataset.sectionLayoutType === 'repeat_table') {
          return;
        }
        const templateId = standardRepeatSectionId(section);
        storeRepeatSectionTemplate(section);
        const visibleSections = standardRepeatSections(templateId);
        const addButton = section.querySelector('[data-repeat-section-add]');
        if (visibleSections.length <= 1) {
          disableRepeatSectionForPayload(section);
          if (addButton) {
            addButton.removeAttribute('data-repeat-section-bound');
          }
          syncStandardRepeatSectionState(templateId);
          bindRepeatSectionButtons();
          return;
        }

        if (addButton) {
          const remainingSections = visibleSections.filter((node) => node !== section);
          const lastRemainingSection = remainingSections[remainingSections.length - 1];
          if (lastRemainingSection) {
            addButton.removeAttribute('data-repeat-section-bound');
            lastRemainingSection.appendChild(addButton);
          }
        }
        section.remove();
        syncStandardRepeatSectionState(templateId);
        bindRepeatSectionButtons();
      });
    });
  }

  function bindRepeatSectionButtons() {
    fieldScope.querySelectorAll('[data-repeat-section-add]').forEach((button) => {
      if (button.dataset.repeatSectionBound === '1') {
        return;
      }
      button.dataset.repeatSectionBound = '1';
      button.addEventListener('click', () => {
        const sourceSection = button.closest('.subject-form-section');
        if (!sourceSection) {
          return;
        }
        const currentCount = Number.parseInt(button.dataset.currentRepeats || sourceSection.dataset.currentRepeats || '1', 10);
        const maxRepeats = parseRepeatMax(button.dataset.maxRepeats || sourceSection.dataset.maxRepeats);
        if (maxRepeats !== null && currentCount >= maxRepeats) {
          updateRepeatSectionButton(button, currentCount, maxRepeats);
          return;
        }
        if (sourceSection.dataset.sectionLayoutType === 'repeat_table') {
          const visibleRowCount = repeatTableVisibleRowCount(sourceSection);
          if (maxRepeats !== null && visibleRowCount >= maxRepeats) {
            updateRepeatSectionButton(button, visibleRowCount, maxRepeats);
            return;
          }
          const nextRepeatIndex = nextRepeatTableIndex(sourceSection);
          if (appendRepeatTableRow(sourceSection, button, nextRepeatIndex, maxRepeats)) {
            ensureEditableInputs();
            select2ControlModule.initializeSelect2LookupControls?.(sourceSection);
            dateTextControlModule.initializeDateTextControls?.(sourceSection);
            bindRepeatTableRowDeleteButtons();
            bindRepeatSectionButtons();
            return;
          }
        }
        const templateId = standardRepeatSectionId(sourceSection);
        const visibleSectionCount = standardRepeatSections(templateId).length;
        if (maxRepeats !== null && visibleSectionCount >= maxRepeats) {
          updateRepeatSectionButton(button, visibleSectionCount, maxRepeats);
          return;
        }
        const nextRepeatIndex = standardRepeatSectionNextIndex(sourceSection);
        if (sourceSection.dataset.repeatDeleted === '1') {
          restoreRepeatSectionFromTemplate(sourceSection, nextRepeatIndex, maxRepeats);
          return;
        }
        const clonedSection = sourceSection.cloneNode(true);
        const clonedButton = clonedSection.querySelector('[data-repeat-section-add]');
        button.remove();
        if (clonedButton) {
          clonedButton.removeAttribute('data-repeat-section-bound');
        }

        clonedSection.dataset.repeatInstanceIndex = String(nextRepeatIndex);
        clonedSection.dataset.currentRepeats = String(visibleSectionCount + 1);
        clonedSection.dataset.nextRepeatIndex = String(nextRepeatIndex + 1);
        rewriteClonedSectionFields(clonedSection, nextRepeatIndex);
        updateRepeatSectionButton(clonedButton, visibleSectionCount + 1, maxRepeats);

        sourceSection.insertAdjacentElement('afterend', clonedSection);
        dateTextControlModule.initializeDateTextControls?.(clonedSection);
        syncStandardRepeatSectionState(templateId, nextRepeatIndex + 1);
        ensureEditableInputs();
        select2ControlModule.initializeSelect2LookupControls?.(clonedSection);
        bindRepeatSectionDeleteButtons();
        bindRepeatSectionButtons();
      });
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
  const reasonRequiredFieldKeysPayload =
    shared.loadPayloadByScriptId?.('datacapture-reason-required-field-keys-payload') || [];
  const reasonRequiredFieldKeySet = new Set(
    Array.isArray(reasonRequiredFieldKeysPayload)
      ? reasonRequiredFieldKeysPayload
        .map((key) => canonicalFieldKey(key))
        .filter((key) => key)
      : [],
  );
  const resetTrackpointDataPayload =
    clonePayloadObject(resetTrackpointPayloadSource) ||
    clonePayloadObject(initialCurrentDataPayload);

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

  initializeRepeatTableStates();
  initializeStandardRepeatSectionStates();
  bindRepeatTableRowDeleteButtons();
  bindRepeatSectionDeleteButtons();
  bindRepeatSectionButtons();
  markCurrentPayloadClean();
  bindUnsavedChangesGuard();

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
      markCurrentPayloadClean();
      showNotification('Saved successfully.', 'success');
      if (shouldReloadWithLatestEntry(result)) {
        allowNextNavigation();
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
    markCurrentPayloadClean();
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

    if (previousSubmittedPayload && reasonRequiredFieldKeySet.size > 0) {
      const changedFieldKeys = resolveChangedFieldKeys(previousSubmittedPayload, payloadObject);
      const reasonRequiredChangedFieldKeys = changedFieldKeys.filter((fieldKey) =>
        Array.from(reasonRequiredLookupKeys(fieldKey)).some((lookupKey) =>
          reasonRequiredFieldKeySet.has(lookupKey),
        ),
      );
      if (reasonRequiredChangedFieldKeys.length > 0) {
        const fieldLabelMap = resolveFieldLabelMap(fieldScope);
        const modalReasons = await reasonModal?.openChangeReasonModal?.(
          reasonRequiredChangedFieldKeys,
          fieldLabelMap,
        );
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
        data: collectFormPayloadObject({ includeLookupMetadata: true }),
        change_reasons: submitReasons,
      });
      const result = await network.postJson(submitUrl, submitPayload);
      pageStatus = normalizePageStatus(result.page_status ?? pageStatus);
      formRoot.dataset.pageStatus = pageStatus;
      allowNextNavigation();
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
        allowNextNavigation();
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
      verifiedFieldKeySet: reasonRequiredFieldKeySet,
    };
    radioControlModule.applySubmittedDiffRadioMarkers?.(markerContext);
    textControlModule.applySubmittedDiffTextMarkers?.(markerContext);
    numberControlModule.applySubmittedDiffNumberMarkers?.(markerContext);
    textareaControlModule.applySubmittedDiffTextareaMarkers?.(markerContext);
    selectControlModule.applySubmittedDiffSelectMarkers?.(markerContext);
    select2ControlModule.applySubmittedDiffSelect2Markers?.(markerContext);
    multiSelectControlModule.applySubmittedDiffMultiSelectMarkers?.(markerContext);
  }

  refreshSubmittedDiffMarkers();
  fieldScope.addEventListener('input', refreshSubmittedDiffMarkers);
  fieldScope.addEventListener('change', refreshSubmittedDiffMarkers);
})();
