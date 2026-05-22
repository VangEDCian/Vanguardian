(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};

  function createValidationModule(deps) {
    const { fieldScope, showNotification, parseNumericValue } = deps;
    const dateTextControlModule = window.DatacaptureSubjectDetailModules?.controls?.dateText || {};

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

    function validateDateTextInputs() {
      const dateTextContainers = fieldScope.querySelectorAll('[data-field-key]');
      for (const container of dateTextContainers) {
        if (!container.querySelector('[data-date-text-input]')) {
          continue;
        }
        const validation = dateTextControlModule.validateDateTextInput?.(container) || {
          ok: true,
          message: '',
          focusEl: null,
        };
        if (!validation.ok) {
          return validation;
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

      const dateTextValidation = validateDateTextInputs();
      if (!dateTextValidation.ok) {
        if (dateTextValidation.focusEl) {
          dateTextValidation.focusEl.focus();
        }
        showNotification(dateTextValidation.message, 'error');
        return false;
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

    return {
      validateBeforePersist,
      validateDateParts,
      validateDateTextInputs,
      validateNumberInput,
    };
  }

  window.DatacaptureSubjectDetailModules.validation = {
    createValidationModule,
  };
})();
