(function () {
  const button = document.querySelector('[data-form-verification-verify-all]');
  if (!button) {
    return;
  }
  const postUrl = String(button.dataset.postUrl || '').trim();
  if (!postUrl) {
    return;
  }

  function showInlineMessage(text, isError) {
    let host = document.querySelector('[data-form-verification-verify-message]');
    if (!host) {
      host = document.createElement('p');
      host.setAttribute('data-form-verification-verify-message', '');
      host.className = 'subject-form-verification-review__verify-message';
      const footer = button.closest('.subject-detail-screen__footer');
      if (footer) {
        footer.appendChild(host);
      }
    }
    host.textContent = text || '';
    host.classList.toggle('subject-form-verification-review__verify-message--error', Boolean(isError));
  }

  button.addEventListener('click', function () {
    const root = document.querySelector('.subject-form-verification-review');
    if (!root) {
      showInlineMessage('Review panel not found.', true);
      return;
    }
    const checked = Array.from(root.querySelectorAll('input[name="verify_field"]:checked'))
      .map(function (el) {
        return parseInt(String(el.value || '').trim(), 10);
      })
      .filter(function (n) {
        return !Number.isNaN(n);
      });

    let reloadScheduled = false;
    button.disabled = true;
    showInlineMessage('', false);

    window
      .fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_template_ids: checked }),
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
        var errs = result.data && result.data.error;
        var serverErrors = Array.isArray(errs) ? errs.join(', ') : '';
        if (!result.ok) {
          const msg =
            serverErrors ||
            (result.status >= 500 ? 'Server error.' : 'Request failed.');
          showInlineMessage(msg, true);
          return;
        }
        if (!result.data || result.data.ok !== true) {
          showInlineMessage(
            serverErrors || 'Unexpected response from server (not saved). Check the Network tab for the POST request.',
            true,
          );
          return;
        }
        const msg =
          result.data.all_verified === true ? 'All fields verified.' : 'Saved.';
        showInlineMessage(msg, false);
        reloadScheduled = true;
        window.setTimeout(function () {
          window.location.reload();
        }, 400);
      })
      .catch(function () {
        showInlineMessage('Network error.', true);
      })
      .finally(function () {
        if (!reloadScheduled) {
          button.disabled = false;
        }
      });
  });
})();
