(function () {
  window.DatacaptureSubjectDetailModules = window.DatacaptureSubjectDetailModules || {};

  function createReasonModalModule(deps) {
    const {
      reasonModalBackdrop,
      reasonRowsHost,
      reasonSubmitButton,
      reasonCancelButton,
      showNotification,
      canonicalFieldKey,
      formatEntryDate,
    } = deps;

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

    return { openChangeReasonModal };
  }

  window.DatacaptureSubjectDetailModules.reasonModal = {
    createReasonModalModule,
  };
})();
