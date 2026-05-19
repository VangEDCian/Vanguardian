(function () {
  const modal = document.querySelector('[data-query-modal]');
  const openQueryModal = document.querySelector('[data-open-query-modal]');
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
  const closeButton = modal.querySelector('[data-query-modal-close]');
  const messagesNode = modal.querySelector('[data-query-modal-messages]');
  const emptyNode = modal.querySelector('[data-query-modal-empty]');
  const languageCode = String(modal.dataset.languageCode || '').trim().toLowerCase();
  const openLanguageCode = String(openQueryModal?.dataset.languageCode || languageCode).trim().toLowerCase();
  const postUrl = String(modal.dataset.queryThreadUrl || '').trim();
  const openPostUrl = String(openQueryModal?.dataset.openQueryUrl || '').trim();
  const openTitleEnPrefix = String(openQueryModal?.dataset.titleEnPrefix || 'Open Query for field').trim();
  const openTitleViPrefix = String(openQueryModal?.dataset.titleViPrefix || 'Mo Cau hoi cho truong').trim();
  const queriesEnPrefix = String(modal.dataset.queriesEnPrefix || 'Queries for field').trim();
  const queriesViPrefix = String(modal.dataset.queriesViPrefix || 'Cau hoi cho truong').trim();
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

  function buildMessageNode(message) {
    const item = document.createElement('article');
    item.className = 'subject-form-verification-query-modal__message';
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
    text.textContent = String(message.text || '').trim();
    item.appendChild(text);
    return item;
  }

  function setThreadActionsEnabled(enabled) {
    [replyButton, replyCloseButton].forEach(function (button) {
      if (button instanceof HTMLButtonElement) {
        button.disabled = !enabled;
      }
    });
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
    node.dataset.messageOpenedBy = String(message.openedBy || '');
    node.dataset.messageOpenedAt = String(message.openedAt || '');
    source.insertBefore(node, source.firstChild);
    Array.from(source.querySelectorAll('[data-query-message]'))
      .slice(10)
      .forEach(function (oldNode) {
        oldNode.remove();
      });
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
          openedBy: node.dataset.messageOpenedBy,
          openedAt: node.dataset.messageOpenedAt,
          dataqueryId: node.dataset.messageDataqueryId,
        },
        'append',
      );
    });
    updateEmptyState();
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
    };
    setText(titleNode, `${titlePrefix} ${titleField}`.trim());
    setText(briefNode, fieldLabel || fieldKey || '-');
    setText(valueNode, fieldValue || '-');
    if (input instanceof HTMLTextAreaElement) {
      input.value = '';
    }
    loadMessages(trigger);
    setThreadActionsEnabled(!!activeContext.dataqueryId && !!postUrl);
    modal.hidden = false;
    if (input instanceof HTMLTextAreaElement) {
      input.focus();
    }
  }

  function closeModal() {
    modal.hidden = true;
    activeContext = null;
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

  function postThreadAction(closeQuery) {
    if (!activeContext || !postUrl || !(input instanceof HTMLTextAreaElement)) {
      return;
    }
    const messageText = String(input.value || '').trim();
    if (!messageText) {
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
        appendMessage(
          {
            text: result.data.message_text,
            status: result.data.message_type,
            openedAt: result.data.created_at,
          },
          'prepend',
        );
        input.value = '';
        const badge = activeContext.trigger.querySelector('[data-query-thread-badge]');
        if (badge) {
          badge.remove();
        }
        if (result.data.closed === true && activeContext.trigger instanceof HTMLButtonElement) {
          activeContext.trigger.disabled = true;
          activeContext.trigger.setAttribute('aria-disabled', 'true');
          activeContext.trigger.hidden = true;
          const row = activeContext.trigger.closest('[data-query-field-container]') || activeContext.trigger.closest('tr');
          const openTrigger = row ? row.querySelector('[data-query-modal-trigger]') : null;
          if (openTrigger instanceof HTMLButtonElement) {
            openTrigger.hidden = false;
            openTrigger.disabled = false;
            openTrigger.removeAttribute('aria-disabled');
          }
          const checkbox = row ? row.querySelector('input[name="verify_field"]') : null;
          if (
            checkbox instanceof HTMLInputElement &&
            String(checkbox.dataset.fieldVerified || '').trim().toLowerCase() !== 'true'
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
      })
      .catch(function () {
        appendMessage({ text: 'Network error.', status: 'error' }, 'prepend');
      })
      .finally(function () {
        if (activeContext && !(activeContext.trigger instanceof HTMLButtonElement && activeContext.trigger.disabled)) {
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
  });

  if (replyButton instanceof HTMLElement) {
    replyButton.addEventListener('click', function () {
      postThreadAction(false);
    });
  }

  if (replyCloseButton instanceof HTMLElement) {
    replyCloseButton.addEventListener('click', function () {
      postThreadAction(true);
    });
  }

  if (closeButton instanceof HTMLElement) {
    closeButton.addEventListener('click', closeModal);
  }

  if (openCloseButton instanceof HTMLElement) {
    openCloseButton.addEventListener('click', closeOpenQueryModal);
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
  });
})();
