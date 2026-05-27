(function () {
  const modal = document.querySelector('[data-query-modal]');
  const openQueryModal = document.querySelector('[data-open-query-modal]');
  const historyModal = document.querySelector('[data-query-history-modal]');
  if (!(modal instanceof HTMLElement)) {
    return;
  }

  const openTitleNode = openQueryModal?.querySelector('[data-open-query-modal-title]');
  const openBriefNode = openQueryModal?.querySelector('[data-open-query-modal-brief]');
  const openValueNode = openQueryModal?.querySelector('[data-open-query-modal-value]');
  const openInput = openQueryModal?.querySelector('[data-open-query-modal-comment-input]');
  const openSubmitButton = openQueryModal?.querySelector('[data-open-query-modal-submit]');
  const openCloseButton = openQueryModal?.querySelector('[data-open-query-modal-close]');
  const titleNode = modal.querySelector('[data-query-modal-title]');
  const briefNode = modal.querySelector('[data-query-modal-brief]');
  const valueNode = modal.querySelector('[data-query-modal-value]');
  const input = modal.querySelector('[data-query-modal-comment-input]');
  const replyButton = modal.querySelector('[data-query-modal-reply]');
  const replyCloseButton = modal.querySelector('[data-query-modal-reply-close]');
  const cancelButton = modal.querySelector('[data-query-modal-cancel]');
  const resolvedWrap = modal.querySelector('[data-query-modal-resolved-wrap]');
  const resolvedInput = modal.querySelector('[data-query-modal-resolved-input]');
  const closeButton = modal.querySelector('[data-query-modal-close]');
  const messagesNode = modal.querySelector('[data-query-modal-messages]');
  const emptyNode = modal.querySelector('[data-query-modal-empty]');
  const historyTitleNode = historyModal?.querySelector('[data-query-history-modal-title]');
  const historyBriefNode = historyModal?.querySelector('[data-query-history-modal-brief]');
  const historyValueNode = historyModal?.querySelector('[data-query-history-modal-value]');
  const historyListNode = historyModal?.querySelector('[data-query-history-modal-list]');
  const historyMessagesNode = historyModal?.querySelector('[data-query-history-modal-messages]');
  const historyEmptyNode = historyModal?.querySelector('[data-query-history-modal-empty]');
  const historyCloseButton = historyModal?.querySelector('[data-query-history-modal-close]');
  const languageCode = String(modal.dataset.languageCode || '').trim().toLowerCase();
  const openLanguageCode = String(openQueryModal?.dataset.languageCode || languageCode).trim().toLowerCase();
  const historyLanguageCode = String(historyModal?.dataset.languageCode || languageCode).trim().toLowerCase();
  const postUrl = String(modal.dataset.queryThreadUrl || '').trim();
  const openPostUrl = String(openQueryModal?.dataset.openQueryUrl || '').trim();
  const openTitleEnPrefix = String(openQueryModal?.dataset.titleEnPrefix || 'Open Query for field').trim();
  const openTitleViPrefix = String(openQueryModal?.dataset.titleViPrefix || 'Mo Cau hoi cho truong').trim();
  const queriesEnPrefix = String(modal.dataset.queriesEnPrefix || 'Queries for field').trim();
  const queriesViPrefix = String(modal.dataset.queriesViPrefix || 'Cau hoi cho truong').trim();
  const historyEnPrefix = String(historyModal?.dataset.historyEnPrefix || 'Queries History for field').trim();
  const historyViPrefix = String(historyModal?.dataset.historyViPrefix || 'Lich su cau hoi cho truong').trim();
  const notificationDurationMs = 2600;
  const notificationHost = document.createElement('div');
  notificationHost.className = 'subject-detail-screen__notifications';
  notificationHost.setAttribute('data-form-verification-query-notifications', '');
  document.body.appendChild(notificationHost);
  let activeContext = null;
  let activeOpenContext = null;

  function isVietnamese(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized === 'vi' || normalized.startsWith('vi-');
  }

  function setText(node, value) {
    if (node) {
      node.textContent = String(value || '');
    }
  }

  function showNotification(message, tone) {
    if (!message || !notificationHost) {
      return;
    }
    const normalizedTone = tone === 'error' ? 'error' : 'success';
    const notice = document.createElement('div');
    notice.className = `subject-detail-screen__notification subject-detail-screen__notification--${normalizedTone}`;
    notice.textContent = String(message);
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

  function clearMessages() {
    if (!messagesNode) {
      return;
    }
    Array.from(messagesNode.querySelectorAll('[data-query-modal-message]')).forEach(function (node) {
      node.remove();
    });
  }

  function updateEmptyState() {
    if (!emptyNode || !messagesNode) {
      return;
    }
    emptyNode.hidden = messagesNode.querySelector('[data-query-modal-message]') !== null;
  }

  function clearHistoryMessages() {
    if (!historyMessagesNode) {
      return;
    }
    Array.from(historyMessagesNode.querySelectorAll('[data-query-modal-message]')).forEach(function (node) {
      node.remove();
    });
  }

  function updateHistoryEmptyState() {
    if (!historyEmptyNode || !historyMessagesNode) {
      return;
    }
    historyEmptyNode.hidden = historyMessagesNode.querySelector('[data-query-modal-message]') !== null;
  }

  function buildMessageNode(message) {
    const item = document.createElement('article');
    item.className = 'subject-form-verification-query-modal__message';
    const tone = String(message.tone || '').trim().toLowerCase();
    const statusTone = String(message.status || '').trim().toLowerCase();
    if (tone === 'warning' || statusTone === 'warning') {
      item.classList.add('subject-form-verification-query-modal__message--warning');
    }
    item.setAttribute('data-query-modal-message', '');

    const meta = document.createElement('div');
    meta.className = 'subject-form-verification-query-modal__message-meta';
    const openedBy = String(message.openedBy || '').trim();
    const openedAt = String(message.openedAt || '').trim();
    const status = String(message.status || '').trim();
    [openedBy, openedAt, status].filter(Boolean).forEach(function (value) {
      const span = document.createElement('span');
      span.textContent = value;
      meta.appendChild(span);
    });
    if (meta.childNodes.length > 0) {
      item.appendChild(meta);
    }

    const text = document.createElement('p');
    text.className = 'subject-form-verification-query-modal__message-text';
    appendFormattedMessageText(text, message.text);
    item.appendChild(text);
    return item;
  }

  function appendFormattedMessageText(node, rawText) {
    const text = String(rawText || '').trim();
    text.split(/(\*\*[^*]+\*\*)/g).forEach(function (part) {
      if (!part) {
        return;
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        const strong = document.createElement('strong');
        strong.textContent = part.slice(2, -2);
        node.appendChild(strong);
        return;
      }
      node.appendChild(document.createTextNode(part));
    });
  }

  function setThreadActionsEnabled(enabled) {
    const canRespond = activeContext && activeContext.canRespond === true;
    [replyButton, replyCloseButton, cancelButton].forEach(function (button) {
      if (button instanceof HTMLButtonElement) {
        button.disabled = !enabled || !canRespond;
      }
    });
  }

  function setThreadResponseControlsVisible(visible) {
    if (input instanceof HTMLTextAreaElement) {
      input.hidden = !visible;
      input.disabled = !visible;
    }
    [replyButton, replyCloseButton, cancelButton].forEach(function (button) {
      if (button instanceof HTMLButtonElement) {
        button.hidden = !visible;
      }
    });
    if (!visible && resolvedWrap instanceof HTMLElement) {
      resolvedWrap.hidden = true;
    }
  }

  function isResolvedChecked() {
    return resolvedInput instanceof HTMLInputElement && resolvedInput.checked;
  }

  function updateResolvedControls() {
    const canRespond = activeContext && activeContext.canRespond === true;
    const canResolve = canRespond && activeContext && activeContext.isAnswered === true;
    if (resolvedWrap instanceof HTMLElement) {
      resolvedWrap.hidden = !canResolve;
    }
    if (resolvedInput instanceof HTMLInputElement && !canResolve) {
      resolvedInput.checked = false;
    }
    if (replyCloseButton instanceof HTMLButtonElement && resolvedInput instanceof HTMLInputElement) {
      replyCloseButton.hidden = !(canResolve && resolvedInput.checked);
    }
  }

  function setOpenActionsEnabled(enabled) {
    if (openSubmitButton instanceof HTMLButtonElement) {
      openSubmitButton.disabled = !enabled;
    }
  }

  function appendMessage(message, placement) {
    if (!messagesNode) {
      return;
    }
    const node = buildMessageNode(message);
    const firstMessage = messagesNode.querySelector('[data-query-modal-message]');
    if (placement === 'prepend' && firstMessage) {
      messagesNode.insertBefore(node, firstMessage);
    } else if (placement === 'prepend' && emptyNode) {
      messagesNode.insertBefore(node, emptyNode);
    } else {
      messagesNode.appendChild(node);
    }
    Array.from(messagesNode.querySelectorAll('[data-query-modal-message]'))
      .slice(10)
      .forEach(function (oldNode) {
        oldNode.remove();
      });
    updateEmptyState();
  }

  function appendHistoryMessage(message) {
    if (!historyMessagesNode) {
      return;
    }
    const node = buildMessageNode(message);
    if (historyEmptyNode) {
      historyMessagesNode.insertBefore(node, historyEmptyNode);
    } else {
      historyMessagesNode.appendChild(node);
    }
    updateHistoryEmptyState();
  }

  function appendSourceMessage(row, message) {
    if (!row) {
      return;
    }
    const source = row.querySelector('[data-query-message-source]');
    if (!source) {
      return;
    }
    const node = document.createElement('div');
    node.hidden = true;
    node.setAttribute('data-query-message', '');
    node.dataset.messageDataqueryId = String(message.dataqueryId || '');
    node.dataset.messageText = String(message.text || '');
    node.dataset.messageStatus = String(message.status || '');
    node.dataset.messageTone = String(message.tone || '');
    node.dataset.messageOpenedBy = String(message.openedBy || '');
    node.dataset.messageOpenedAt = String(message.openedAt || '');
    source.insertBefore(node, source.firstChild);
    Array.from(source.querySelectorAll('[data-query-message]'))
      .slice(10)
      .forEach(function (oldNode) {
        oldNode.remove();
      });
  }

  function promoteCurrentQueryToHistory(row, trigger, closedAt) {
    if (!row || !(trigger instanceof HTMLElement)) {
      return;
    }
    const historySource = row.querySelector('[data-query-history-source]');
    const messageSource = row.querySelector('[data-query-message-source]');
    if (!historySource || !messageSource) {
      return;
    }
    const dataqueryId = String(trigger.dataset.activeQueryId || '').trim();
    if (!dataqueryId) {
      return;
    }
    const historyNode = document.createElement('div');
    historyNode.setAttribute('data-query-history', '');
    historyNode.dataset.historyDataqueryId = dataqueryId;
    historyNode.dataset.historyLabel = `Query #${dataqueryId}`;
    historyNode.dataset.historyClosedAt = String(closedAt || '');

    Array.from(messageSource.querySelectorAll('[data-query-message]'))
      .filter(function (node) {
        return node.dataset.messageDataqueryId === dataqueryId;
      })
      .slice(0, 10)
      .forEach(function (node) {
        const messageNode = document.createElement('div');
        messageNode.setAttribute('data-query-history-message', '');
        messageNode.dataset.messageDataqueryId = String(node.dataset.messageDataqueryId || '');
        messageNode.dataset.messageText = String(node.dataset.messageText || '');
        messageNode.dataset.messageStatus = String(node.dataset.messageStatus || '');
        messageNode.dataset.messageTone = String(node.dataset.messageTone || '');
        messageNode.dataset.messageOpenedBy = String(node.dataset.messageOpenedBy || '');
        messageNode.dataset.messageOpenedAt = String(node.dataset.messageOpenedAt || '');
        historyNode.appendChild(messageNode);
      });

    historySource.insertBefore(historyNode, historySource.firstChild);
    const historyTrigger = row.querySelector('[data-query-history-modal-trigger]');
    if (historyTrigger instanceof HTMLButtonElement) {
      historyTrigger.hidden = false;
    }
  }

  function loadMessages(trigger) {
    clearMessages();
    const container = trigger.closest('[data-query-field-container]') || trigger.closest('tr');
    const source = container ? container.querySelector('[data-query-message-source]') : null;
    if (!source) {
      updateEmptyState();
      return;
    }
    Array.from(source.querySelectorAll('[data-query-message]')).slice(0, 10).forEach(function (node) {
      appendMessage(
        {
          text: node.dataset.messageText,
          status: node.dataset.messageStatus,
          tone: node.dataset.messageTone,
          openedBy: node.dataset.messageOpenedBy,
          openedAt: node.dataset.messageOpenedAt,
          dataqueryId: node.dataset.messageDataqueryId,
        },
        'append',
      );
    });
    updateEmptyState();
  }

  function historySourceItems(trigger) {
    const container = trigger.closest('[data-query-field-container]') || trigger.closest('tr');
    const source = container ? container.querySelector('[data-query-history-source]') : null;
    if (!source) {
      return [];
    }
    return Array.from(source.children).filter(function (node) {
      return node instanceof HTMLElement && node.hasAttribute('data-query-history');
    });
  }

  function selectHistorySource(sourceNode) {
    if (!(sourceNode instanceof HTMLElement) || !historyListNode) {
      return;
    }
    Array.from(historyListNode.querySelectorAll('[data-query-history-item]')).forEach(function (node) {
      node.setAttribute(
        'aria-selected',
        node instanceof HTMLElement && node.dataset.historyDataqueryId === sourceNode.dataset.historyDataqueryId
          ? 'true'
          : 'false',
      );
    });
    clearHistoryMessages();
    Array.from(sourceNode.querySelectorAll('[data-query-history-message]')).slice(0, 10).forEach(function (node) {
      appendHistoryMessage({
        text: node.dataset.messageText,
        status: node.dataset.messageStatus,
        tone: node.dataset.messageTone,
        openedBy: node.dataset.messageOpenedBy,
        openedAt: node.dataset.messageOpenedAt,
        dataqueryId: node.dataset.messageDataqueryId,
      });
    });
    updateHistoryEmptyState();
  }

  function loadHistoryList(trigger) {
    if (!historyListNode) {
      return;
    }
    historyListNode.replaceChildren();
    const sources = historySourceItems(trigger);
    sources.forEach(function (sourceNode, index) {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'subject-form-verification-query-modal__history-item';
      item.setAttribute('data-query-history-item', '');
      item.setAttribute('aria-selected', index === 0 ? 'true' : 'false');
      item.dataset.historyDataqueryId = String(sourceNode.dataset.historyDataqueryId || '');

      const label = document.createElement('span');
      label.className = 'subject-form-verification-query-modal__history-item-label';
      label.textContent = String(sourceNode.dataset.historyLabel || sourceNode.dataset.historyDataqueryId || '');
      item.appendChild(label);

      const date = document.createElement('span');
      date.className = 'subject-form-verification-query-modal__history-item-date';
      date.textContent = String(sourceNode.dataset.historyClosedAt || sourceNode.dataset.historyOpenedAt || '');
      item.appendChild(date);

      item.addEventListener('click', function () {
        selectHistorySource(sourceNode);
      });
      historyListNode.appendChild(item);
    });
    selectHistorySource(sources[0]);
  }

  function openNewQueryModal(trigger) {
    if (!(openQueryModal instanceof HTMLElement)) {
      return;
    }
    if (String(trigger.dataset.fieldVerified || '').trim().toLowerCase() === 'true') {
      showNotification('Dữ liệu đã được verify không thể tạo Query', 'error');
      return;
    }
    const fieldLabel = String(trigger.dataset.fieldLabel || '').trim();
    const fieldKey = String(trigger.dataset.fieldKey || '').trim();
    const fieldValue = String(trigger.dataset.fieldValue || '').trim();
    const titleField = isVietnamese(openLanguageCode) ? fieldKey || fieldLabel : fieldLabel || fieldKey;
    const titlePrefix = isVietnamese(openLanguageCode) ? openTitleViPrefix : openTitleEnPrefix;
    activeOpenContext = {
      trigger: trigger,
      fieldTemplateId: String(trigger.dataset.fieldTemplateId || '').trim(),
      fieldKey: String(trigger.dataset.fieldKey || '').trim(),
    };
    setText(openTitleNode, `${titlePrefix} ${titleField}`.trim());
    setText(openBriefNode, fieldLabel || fieldKey || '-');
    setText(openValueNode, fieldValue || '-');
    if (openInput instanceof HTMLTextAreaElement) {
      openInput.value = '';
    }
    setOpenActionsEnabled(!!activeOpenContext.fieldTemplateId && !!openPostUrl);
    openQueryModal.hidden = false;
    if (openInput instanceof HTMLTextAreaElement) {
      openInput.focus();
    }
  }

  function openModal(trigger) {
    const fieldLabel = String(trigger.dataset.fieldLabel || '').trim();
    const fieldKey = String(trigger.dataset.fieldKey || '').trim();
    const fieldValue = String(trigger.dataset.fieldValue || '').trim();
    const titleField = isVietnamese(languageCode) ? fieldKey || fieldLabel : fieldLabel || fieldKey;
    const titlePrefix = isVietnamese(languageCode) ? queriesViPrefix : queriesEnPrefix;
    activeContext = {
      trigger: trigger,
      dataqueryId: String(trigger.dataset.activeQueryId || '').trim(),
      fieldTemplateId: String(trigger.dataset.fieldTemplateId || '').trim(),
      isAnswered: String(trigger.dataset.queryAnswered || '').trim().toLowerCase() === 'true',
      canRespond: String(trigger.dataset.queryCanRespond || 'true').trim().toLowerCase() !== 'false',
    };
    setText(titleNode, `${titlePrefix} ${titleField}`.trim());
    setText(briefNode, fieldLabel || fieldKey || '-');
    setText(valueNode, fieldValue || '-');
    if (input instanceof HTMLTextAreaElement) {
      input.value = '';
    }
    if (resolvedInput instanceof HTMLInputElement) {
      resolvedInput.checked = false;
    }
    setThreadResponseControlsVisible(activeContext.canRespond);
    updateResolvedControls();
    loadMessages(trigger);
    setThreadActionsEnabled(activeContext.canRespond && !!activeContext.dataqueryId && !!postUrl);
    modal.hidden = false;
    if (activeContext.canRespond && input instanceof HTMLTextAreaElement) {
      input.focus();
    }
  }

  function openHistoryModal(trigger) {
    if (!(historyModal instanceof HTMLElement)) {
      return;
    }
    const fieldLabel = String(trigger.dataset.fieldLabel || '').trim();
    const fieldKey = String(trigger.dataset.fieldKey || '').trim();
    const fieldValue = String(trigger.dataset.fieldValue || '').trim();
    const titleField = isVietnamese(historyLanguageCode) ? fieldKey || fieldLabel : fieldLabel || fieldKey;
    const titlePrefix = isVietnamese(historyLanguageCode) ? historyViPrefix : historyEnPrefix;
    setText(historyTitleNode, `${titlePrefix} ${titleField}`.trim());
    setText(historyBriefNode, fieldLabel || fieldKey || '-');
    setText(historyValueNode, fieldValue || '-');
    loadHistoryList(trigger);
    historyModal.hidden = false;
  }

  function closeModal() {
    modal.hidden = true;
    activeContext = null;
  }

  function closeHistoryModal() {
    if (historyModal instanceof HTMLElement) {
      historyModal.hidden = true;
    }
  }

  function closeOpenQueryModal() {
    if (openQueryModal instanceof HTMLElement) {
      openQueryModal.hidden = true;
    }
    activeOpenContext = null;
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

  function releaseQueryRow(row, trigger) {
    if (trigger instanceof HTMLButtonElement) {
      trigger.disabled = true;
      trigger.setAttribute('aria-disabled', 'true');
      trigger.hidden = true;
    }
    const openTrigger = row ? row.querySelector('[data-query-modal-trigger]') : null;
    if (openTrigger instanceof HTMLButtonElement) {
      openTrigger.hidden = false;
      openTrigger.disabled = false;
      openTrigger.removeAttribute('aria-disabled');
    }
    const checkbox = row ? row.querySelector('input[name="verify_field"]') : null;
    if (
      checkbox instanceof HTMLInputElement &&
      String(checkbox.dataset.fieldVerified || '').trim().toLowerCase() !== 'true' &&
      String(checkbox.dataset.blockedByValidationIssue || '').trim().toLowerCase() !== 'true'
    ) {
      checkbox.dataset.blockedByOpenQuery = 'false';
      checkbox.disabled = false;
      checkbox.removeAttribute('aria-disabled');
    }
    if (row instanceof HTMLElement) {
      row.classList.remove('subject-form-field--has-open-query');
    }
    const countCell = row ? row.querySelector('[data-open-query-count]') : null;
    if (countCell) {
      const current = parseInt(String(countCell.textContent || '0').trim(), 10);
      countCell.textContent = String(Number.isNaN(current) ? 0 : Math.max(0, current - 1));
    }
  }

  function postThreadAction(closeQuery, cancelQuery) {
    if (!activeContext || !postUrl || !(input instanceof HTMLTextAreaElement)) {
      return;
    }
    const messageText = String(input.value || '').trim();
    if (!messageText && cancelQuery !== true) {
      return;
    }
    setThreadActionsEnabled(false);
    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataquery_id: parseInt(activeContext.dataqueryId, 10),
          field_template_id: parseInt(activeContext.fieldTemplateId, 10),
          message_text: messageText,
          close_query: closeQuery === true,
          cancel_query: cancelQuery === true,
          is_resolved: closeQuery === true && isResolvedChecked(),
        }),
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
          appendMessage({ text: normalizeErrorMessage(result), status: 'error' }, 'prepend');
          return;
        }
        const row = activeContext.trigger.closest('[data-query-field-container]') || activeContext.trigger.closest('tr');
        if (result.data.message_text) {
          const message = {
            dataqueryId: activeContext.dataqueryId,
            text: result.data.message_text,
            status: result.data.message_type,
            openedAt: result.data.created_at,
          };
          appendMessage(message, 'prepend');
          appendSourceMessage(row, message);
        }
        input.value = '';
        const badge = activeContext.trigger.querySelector('[data-query-thread-badge]');
        if (badge) {
          badge.remove();
        }
        if (result.data.closed === true && activeContext.trigger instanceof HTMLButtonElement) {
          promoteCurrentQueryToHistory(row, activeContext.trigger, result.data.created_at);
          releaseQueryRow(row, activeContext.trigger);
        }
        if (result.data.cancelled === true && activeContext.trigger instanceof HTMLButtonElement) {
          releaseQueryRow(row, activeContext.trigger);
          closeModal();
        }
        if (
          result.data.closed !== true &&
          result.data.cancelled !== true &&
          activeContext &&
          activeContext.trigger instanceof HTMLElement
        ) {
          activeContext.trigger.dataset.queryAnswered = 'true';
          activeContext.isAnswered = true;
          updateResolvedControls();
        }
      })
      .catch(function () {
        appendMessage({ text: 'Network error.', status: 'error' }, 'prepend');
      })
      .finally(function () {
        if (
          activeContext &&
          activeContext.canRespond === true &&
          !(activeContext.trigger instanceof HTMLButtonElement && activeContext.trigger.disabled)
        ) {
          setThreadActionsEnabled(true);
        }
      });
  }

  function postOpenQuery() {
    if (!activeOpenContext || !openPostUrl || !(openInput instanceof HTMLTextAreaElement)) {
      return;
    }
    const messageText = String(openInput.value || '').trim();
    if (!messageText) {
      return;
    }
    setOpenActionsEnabled(false);
    window
      .fetch(openPostUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_template_id: parseInt(activeOpenContext.fieldTemplateId, 10),
          field_key: activeOpenContext.fieldKey,
          message_text: messageText,
        }),
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
        const row = activeOpenContext.trigger.closest('tr');
        const currentTrigger = row ? row.querySelector('[data-query-thread-modal-trigger]') : null;
        appendSourceMessage(row, {
          dataqueryId: result.data.dataquery_id,
          text: result.data.message_text,
          status: result.data.message_type,
          openedAt: result.data.created_at,
        });
        if (currentTrigger instanceof HTMLButtonElement) {
          currentTrigger.dataset.activeQueryId = String(result.data.dataquery_id || '');
          currentTrigger.dataset.queryCanRespond = 'true';
          currentTrigger.hidden = false;
          currentTrigger.disabled = false;
          currentTrigger.removeAttribute('aria-disabled');
          const badge = currentTrigger.querySelector('[data-query-thread-badge]');
          if (badge) {
            badge.remove();
          }
        }
        activeOpenContext.trigger.hidden = true;
        const checkbox = row ? row.querySelector('input[name="verify_field"]') : null;
        if (checkbox instanceof HTMLInputElement) {
          checkbox.checked = false;
          checkbox.dataset.blockedByOpenQuery = 'true';
          checkbox.disabled = true;
          checkbox.setAttribute('aria-disabled', 'true');
        }
        const countCell = row ? row.querySelector('[data-open-query-count]') : null;
        if (countCell) {
          const current = parseInt(String(countCell.textContent || '0').trim(), 10);
          countCell.textContent = String(Number.isNaN(current) ? 1 : current + 1);
        }
        closeOpenQueryModal();
      })
      .finally(function () {
        setOpenActionsEnabled(true);
      });
  }

  document.addEventListener('click', function (event) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    const threadTrigger = target.closest('[data-query-thread-modal-trigger]');
    if (threadTrigger instanceof HTMLButtonElement) {
      if (threadTrigger.disabled) {
        return;
      }
      openModal(threadTrigger);
      return;
    }
    const historyTrigger = target.closest('[data-query-history-modal-trigger]');
    if (historyTrigger instanceof HTMLButtonElement) {
      if (historyTrigger.disabled) {
        return;
      }
      openHistoryModal(historyTrigger);
      return;
    }
    const trigger = target.closest('[data-query-modal-trigger]');
    if (trigger instanceof HTMLButtonElement) {
      if (trigger.disabled) {
        return;
      }
      openNewQueryModal(trigger);
      return;
    }
    if (target === modal) {
      closeModal();
    }
    if (target === openQueryModal) {
      closeOpenQueryModal();
    }
    if (target === historyModal) {
      closeHistoryModal();
    }
  });

  if (replyButton instanceof HTMLElement) {
    replyButton.addEventListener('click', function () {
      postThreadAction(false);
    });
  }

  if (replyCloseButton instanceof HTMLElement) {
    replyCloseButton.addEventListener('click', function () {
      postThreadAction(true, false);
    });
  }

  if (cancelButton instanceof HTMLElement) {
    cancelButton.addEventListener('click', function () {
      postThreadAction(false, true);
    });
  }

  if (resolvedInput instanceof HTMLElement) {
    resolvedInput.addEventListener('change', updateResolvedControls);
  }

  if (closeButton instanceof HTMLElement) {
    closeButton.addEventListener('click', closeModal);
  }

  if (openCloseButton instanceof HTMLElement) {
    openCloseButton.addEventListener('click', closeOpenQueryModal);
  }

  if (historyCloseButton instanceof HTMLElement) {
    historyCloseButton.addEventListener('click', closeHistoryModal);
  }

  if (openSubmitButton instanceof HTMLElement) {
    openSubmitButton.addEventListener('click', postOpenQuery);
  }

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') {
      return;
    }
    if (!modal.hidden) {
      closeModal();
    }
    if (openQueryModal instanceof HTMLElement && !openQueryModal.hidden) {
      closeOpenQueryModal();
    }
    if (historyModal instanceof HTMLElement && !historyModal.hidden) {
      closeHistoryModal();
    }
  });
})();
