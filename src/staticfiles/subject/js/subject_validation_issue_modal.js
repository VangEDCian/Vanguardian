(function () {
  const modal = document.querySelector('[data-validation-issue-modal]');
  if (!(modal instanceof HTMLElement)) {
    return;
  }

  const titleNode = modal.querySelector('[data-validation-issue-modal-title]');
  const briefNode = modal.querySelector('[data-validation-issue-modal-brief]');
  const valueNode = modal.querySelector('[data-validation-issue-modal-value]');
  const listNode = modal.querySelector('[data-validation-issue-modal-list]');
  const submitButton = modal.querySelector('[data-validation-issue-modal-submit]');
  const closeButton = modal.querySelector('[data-validation-issue-modal-close]');
  const acknowledgeUrl = String(modal.dataset.acknowledgeUrl || '').trim();
  const languageCode = String(modal.dataset.languageCode || '').trim().toLowerCase();
  const titleEnPrefix = String(modal.dataset.titleEnPrefix || 'Validation issues for field').trim();
  const titleViPrefix = String(modal.dataset.titleViPrefix || 'Canh bao validation cho truong').trim();
  const notificationDurationMs = 2600;
  let activeTrigger = null;

  function isVietnamese(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized === 'vi' || normalized.startsWith('vi-');
  }

  function setText(node, value) {
    if (node) {
      node.textContent = String(value || '');
    }
  }

  function notificationHost() {
    let host = document.querySelector('[data-validation-issue-notifications]');
    if (host instanceof HTMLElement) {
      return host;
    }
    host = document.createElement('div');
    host.className = 'subject-detail-screen__notifications';
    host.setAttribute('data-validation-issue-notifications', '');
    document.body.appendChild(host);
    return host;
  }

  function showNotification(message, tone) {
    const text = String(message || '').trim();
    if (!text) {
      return;
    }
    const notice = document.createElement('div');
    notice.className = `subject-detail-screen__notification subject-detail-screen__notification--${tone === 'error' ? 'error' : 'success'}`;
    notice.textContent = text;
    notificationHost().appendChild(notice);
    window.setTimeout(function () {
      notice.classList.add('is-leaving');
      window.setTimeout(function () {
        notice.remove();
      }, 220);
    }, notificationDurationMs);
  }

  function sourceItems(trigger) {
    const container = trigger.closest('[data-query-field-container]') || trigger.closest('tr');
    const source = container ? container.querySelector('[data-validation-issue-source]') : null;
    if (!source) {
      return [];
    }
    return Array.from(source.querySelectorAll('[data-validation-issue]')).filter(function (node) {
      return node instanceof HTMLElement;
    });
  }

  function clearRows() {
    if (listNode) {
      listNode.replaceChildren();
    }
  }

  function buildRow(sourceNode) {
    const row = document.createElement('tr');
    row.className = 'subject-form-validation-issue-modal__row';
    row.setAttribute('data-validation-issue-modal-row', '');
    row.dataset.issueId = String(sourceNode.dataset.issueId || '');

    const checkCell = document.createElement('td');
    checkCell.className = 'subject-form-validation-issue-modal__check';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    checkbox.setAttribute('data-validation-issue-modal-check', '');
    checkCell.appendChild(checkbox);

    const contentCell = document.createElement('td');
    contentCell.className = 'subject-form-validation-issue-modal__content';
    const question = document.createElement('p');
    question.className = 'subject-form-validation-issue-modal__question';
    question.textContent = String(sourceNode.dataset.issueMessage || '');
    contentCell.appendChild(question);

    const meta = document.createElement('div');
    meta.className = 'subject-form-validation-issue-modal__meta';
    [sourceNode.dataset.issueSeverity, sourceNode.dataset.issueMode, sourceNode.dataset.issueStatus]
      .filter(Boolean)
      .forEach(function (value) {
        const item = document.createElement('span');
        item.textContent = String(value);
        meta.appendChild(item);
      });
    if (meta.childNodes.length > 0) {
      contentCell.appendChild(meta);
    }

    const textarea = document.createElement('textarea');
    textarea.className = 'subject-form-validation-issue-modal__textarea';
    textarea.rows = 3;
    textarea.setAttribute('data-validation-issue-modal-comment', '');
    contentCell.appendChild(textarea);

    checkbox.addEventListener('change', function () {
      textarea.disabled = !checkbox.checked;
      if (!checkbox.checked) {
        textarea.value = '';
      }
    });

    row.appendChild(checkCell);
    row.appendChild(contentCell);
    return row;
  }

  function setSubmitEnabled(enabled) {
    if (submitButton instanceof HTMLButtonElement) {
      submitButton.disabled = !enabled;
    }
  }

  function openModal(trigger) {
    const fieldLabel = String(trigger.dataset.fieldLabel || '').trim();
    const fieldKey = String(trigger.dataset.fieldKey || '').trim();
    const fieldValue = String(trigger.dataset.fieldValue || '').trim();
    const titleField = isVietnamese(languageCode) ? fieldKey || fieldLabel : fieldLabel || fieldKey;
    const titlePrefix = isVietnamese(languageCode) ? titleViPrefix : titleEnPrefix;
    activeTrigger = trigger;
    setText(titleNode, `${titlePrefix} ${titleField}`.trim());
    setText(briefNode, fieldLabel || fieldKey || '-');
    setText(valueNode, fieldValue || '-');
    clearRows();
    sourceItems(trigger).forEach(function (sourceNode) {
      listNode?.appendChild(buildRow(sourceNode));
    });
    setSubmitEnabled(!!acknowledgeUrl && !!listNode?.querySelector('[data-validation-issue-modal-row]'));
    modal.hidden = false;
    const firstTextarea = modal.querySelector('[data-validation-issue-modal-comment]');
    if (firstTextarea instanceof HTMLTextAreaElement) {
      firstTextarea.focus();
    }
  }

  function closeModal() {
    modal.hidden = true;
    activeTrigger = null;
    clearRows();
  }

  function normalizeErrorMessage(result) {
    const errs = result && result.data && result.data.error;
    if (Array.isArray(errs) && errs.length > 0) {
      return errs.join(', ');
    }
    if (result && result.status >= 500) {
      return 'Server error.';
    }
    return 'Request failed.';
  }

  function selectedAcknowledgements() {
    const rows = Array.from(modal.querySelectorAll('[data-validation-issue-modal-row]'));
    const out = [];
    for (const row of rows) {
      if (!(row instanceof HTMLElement)) {
        continue;
      }
      const checkbox = row.querySelector('[data-validation-issue-modal-check]');
      const textarea = row.querySelector('[data-validation-issue-modal-comment]');
      if (!(checkbox instanceof HTMLInputElement) || !checkbox.checked) {
        continue;
      }
      const comment = textarea instanceof HTMLTextAreaElement ? String(textarea.value || '').trim() : '';
      if (!comment) {
        if (textarea instanceof HTMLTextAreaElement) {
          textarea.focus();
        }
        showNotification('Acknowledgement comment is required.', 'error');
        return null;
      }
      out.push({
        issue_id: parseInt(row.dataset.issueId || '', 10),
        comment: comment,
      });
    }
    return out;
  }

  function removeAcknowledgedIssues(issueIds) {
    if (!(activeTrigger instanceof HTMLElement)) {
      return;
    }
    const idSet = new Set(issueIds.map(function (issueId) {
      return String(issueId);
    }));
    const container = activeTrigger.closest('[data-query-field-container]') || activeTrigger.closest('tr');
    const source = container ? container.querySelector('[data-validation-issue-source]') : null;
    if (source) {
      Array.from(source.querySelectorAll('[data-validation-issue]')).forEach(function (node) {
        if (node instanceof HTMLElement && idSet.has(String(node.dataset.issueId || ''))) {
          node.remove();
        }
      });
    }
    const remaining = source ? source.querySelectorAll('[data-validation-issue]').length : 0;
    const badge = activeTrigger.querySelector('[data-validation-issue-badge]');
    if (badge) {
      badge.textContent = String(remaining);
    }
    if (remaining <= 0) {
      activeTrigger.remove();
      if (source) {
        source.remove();
      }
      if (container instanceof HTMLElement && !container.querySelector('[data-query-thread-modal-trigger]')) {
        container.classList.remove('subject-form-field--has-open-query');
      }
    }
  }

  function submitAcknowledgements() {
    if (!acknowledgeUrl) {
      return;
    }
    const issues = selectedAcknowledgements();
    if (issues === null) {
      return;
    }
    if (issues.length === 0) {
      closeModal();
      return;
    }
    setSubmitEnabled(false);
    window
      .fetch(acknowledgeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issues: issues }),
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
        removeAcknowledgedIssues(result.data.acknowledged_issue_ids || []);
        closeModal();
      })
      .catch(function () {
        showNotification('Network error.', 'error');
      })
      .finally(function () {
        setSubmitEnabled(true);
      });
  }

  document.addEventListener('click', function (event) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    const trigger = target.closest('[data-validation-issue-modal-trigger]');
    if (trigger instanceof HTMLButtonElement) {
      openModal(trigger);
      return;
    }
    if (target === modal) {
      closeModal();
    }
  });

  if (closeButton instanceof HTMLElement) {
    closeButton.addEventListener('click', closeModal);
  }

  if (submitButton instanceof HTMLElement) {
    submitButton.addEventListener('click', submitAcknowledgements);
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.hidden) {
      closeModal();
    }
  });
})();
