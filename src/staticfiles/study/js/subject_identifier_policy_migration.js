(function () {
  "use strict";

  var modal = document.getElementById("modal-subject-identifier-migration");
  if (!modal) return;

  var title = modal.querySelector(".modal__title");
  var summary = modal.querySelector("[data-identifier-migration-summary]");
  var counts = modal.querySelector("[data-identifier-migration-counts]");
  var issues = modal.querySelector("[data-identifier-migration-issues]");
  var codeInput = modal.querySelector(
    "[data-identifier-migration-confirmation-code]"
  );
  var error = modal.querySelector("[data-identifier-migration-error]");
  var confirmButton = modal.querySelector("[data-identifier-migration-confirm]");
  var pendingAction = null;

  function fieldValue(form, name) {
    var field = form.elements[name];
    return field ? String(field.value || "").trim() : "";
  }

  function policyChanged(form) {
    return (
      fieldValue(form, "subject_identifier_mode") !==
        form.dataset.currentSubjectIdentifierMode ||
      fieldValue(form, "subject_code_pattern") !==
        form.dataset.currentSubjectCodePattern ||
      fieldValue(form, "subject_code_uniqueness_scope") !==
        form.dataset.currentSubjectCodeUniquenessScope
    );
  }

  function csrfToken(form) {
    var source = form || document;
    var token = source.querySelector('input[name="csrfmiddlewaretoken"]');
    return token ? token.value : "";
  }

  function setHidden(form, name, value) {
    var field = form.querySelector('input[name="' + name + '"]');
    if (!field) {
      field = document.createElement("input");
      field.type = "hidden";
      field.name = name;
      form.appendChild(field);
    }
    field.value = value;
  }

  function escapeHtml(value) {
    var element = document.createElement("div");
    element.textContent = String(value == null ? "" : value);
    return element.innerHTML;
  }

  function issueList(label, rows, className) {
    if (!rows || !rows.length) return "";
    return (
      '<section class="' +
      className +
      '"><strong>' +
      escapeHtml(label) +
      "</strong><ul>" +
      rows
        .map(function (row) {
          return "<li>" + escapeHtml(row.message) + "</li>";
        })
        .join("") +
      "</ul></section>"
    );
  }

  function showPreview(preview, action) {
    pendingAction = action;
    var isRollback = action.type === "rollback";
    title.textContent = isRollback
      ? "Rollback Subject Code migration"
      : "Subject Code migration warning";
    summary.textContent = isRollback
      ? "This restores the latest migration snapshot. Codes exported, printed, or sent externally cannot be recalled."
      : "Saving this policy will migrate every Subject in the Study within one transaction.";
    counts.innerHTML =
      "<dt>Total Subjects</dt><dd>" +
      preview.total_subjects +
      "</dd><dt>Enrolled Subjects</dt><dd>" +
      preview.enrolled_subjects +
      "</dd><dt>Subject Codes changed</dt><dd>" +
      preview.changed_subjects +
      "</dd><dt>Subject Codes cleared</dt><dd>" +
      preview.cleared_subject_codes +
      "</dd><dt>Kit Codes changed</dt><dd>" +
      preview.changed_period_kit_codes +
      "</dd>";
    issues.innerHTML =
      issueList("Blocked", preview.blockers, "identifier-migration-blockers") +
      issueList("Warnings", preview.warnings, "identifier-migration-warnings");
    codeInput.value = "";
    error.hidden = true;
    confirmButton.disabled = !preview.can_execute;
    codeInput.disabled = !preview.can_execute;
    confirmButton.textContent = isRollback
      ? "Confirm rollback"
      : "Confirm migration";
    modal.classList.add("is-open");
    if (preview.can_execute) codeInput.focus();
  }

  function showRequestError(message) {
    pendingAction = null;
    title.textContent = "Subject Code migration unavailable";
    summary.textContent = message;
    counts.innerHTML = "";
    issues.innerHTML = "";
    codeInput.disabled = true;
    confirmButton.disabled = true;
    error.hidden = true;
    modal.classList.add("is-open");
  }

  function parseResponse(response) {
    return response.json().then(function (payload) {
      if (!response.ok) {
        var firstBlocker = payload.blockers && payload.blockers[0];
        throw new Error(
          payload.detail ||
            (firstBlocker && firstBlocker.message) ||
            "Subject data changed. Preview the operation again."
        );
      }
      return payload;
    });
  }

  document
    .querySelectorAll("[data-subject-identifier-policy-form]")
    .forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (form.dataset.identifierMigrationApproved === "true") return;
        if (!policyChanged(form)) return;

        event.preventDefault();
        var body = new FormData(form);
        body.delete("subject_identifier_migration_plan_hash");
        body.delete("subject_identifier_migration_confirmation_code");
        fetch(form.dataset.identifierPolicyPreviewUrl, {
          method: "POST",
          body: body,
          headers: { "X-CSRFToken": csrfToken(form) },
          credentials: "same-origin",
        })
          .then(parseResponse)
          .then(function (preview) {
            if (preview.can_execute && !preview.requires_confirmation) {
              form.dataset.identifierMigrationApproved = "true";
              form.submit();
              return;
            }
            showPreview(preview, {
              type: "migrate",
              form: form,
              preview: preview,
              studyCode: form.dataset.currentStudyCode,
            });
          })
          .catch(function (requestError) {
            showRequestError(requestError.message);
          });
      });
    });

  document
    .querySelectorAll("[data-subject-identifier-rollback]")
    .forEach(function (button) {
      button.addEventListener("click", function () {
        fetch(button.dataset.rollbackPreviewUrl, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken(document) },
          credentials: "same-origin",
        })
          .then(parseResponse)
          .then(function (preview) {
            showPreview(preview, {
              type: "rollback",
              preview: preview,
              rollbackUrl: button.dataset.rollbackUrl,
              studyCode: button.dataset.studyCode,
            });
          })
          .catch(function (requestError) {
            showRequestError(requestError.message);
          });
      });
    });

  confirmButton.addEventListener("click", function () {
    if (!pendingAction || !pendingAction.preview.can_execute) return;
    if (codeInput.value.trim() !== pendingAction.studyCode) {
      error.textContent = "Study Code does not match.";
      error.hidden = false;
      return;
    }

    if (pendingAction.type === "migrate") {
      setHidden(
        pendingAction.form,
        "subject_identifier_migration_plan_hash",
        pendingAction.preview.plan_hash
      );
      setHidden(
        pendingAction.form,
        "subject_identifier_migration_confirmation_code",
        codeInput.value.trim()
      );
      pendingAction.form.dataset.identifierMigrationApproved = "true";
      modal.classList.remove("is-open");
      pendingAction.form.submit();
      return;
    }

    var body = new FormData();
    body.append("plan_hash", pendingAction.preview.plan_hash);
    body.append("confirmation_code", codeInput.value.trim());
    fetch(pendingAction.rollbackUrl, {
      method: "POST",
      body: body,
      headers: { "X-CSRFToken": csrfToken(document) },
      credentials: "same-origin",
    })
      .then(parseResponse)
      .then(function (payload) {
        window.location.assign(payload.redirect_url || window.location.href);
      })
      .catch(function (requestError) {
        showRequestError(requestError.message);
      });
  });
})();
