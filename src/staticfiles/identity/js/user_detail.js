(function () {
    const $ = window.jQuery;
    if (!$ || !$.fn.select2) {
        return;
    }

    $(function () {
        $('.old-select2-single-choice').select2({
            width: '100%',
            placeholder: function () {
                return $(this).data('placeholder') || '';
            },
        });

        const form = document.querySelector('[data-user-detail-form]');
        const saveButton = document.querySelector('[data-user-detail-save]');
        const feedback = document.querySelector('[data-user-detail-feedback]');
        const enablePasswordChange = form?.querySelector('[data-user-detail-enable-password-change]');
        const passwordPanel = form?.querySelector('[data-user-detail-password-panel]');
        const newPasswordInput = form?.querySelector('#detail-new-password');
        const confirmPasswordInput = form?.querySelector('#detail-confirm-password');
        const $studySelect = $('#detail-studies');
        const $siteSelect = $('#detail-sites');
        const studiesApiUrl = form?.dataset.apiStudiesUrl || '';
        const studySitesApiUrl = form?.dataset.apiStudySitesUrl || '';
        const canManagePermissions = form?.dataset.canManagePermissions === 'true';
        const canUpdateDetail = form?.dataset.canUpdateDetail === 'true';
        const messagePasswordRequired = form?.dataset.messagePasswordRequired || 'Please fill in both password fields to change the password.';
        const messageSaveFailed = form?.dataset.messageSaveFailed || 'Unable to save user details.';
        const messageSaveSuccess = form?.dataset.messageSaveSuccess || 'User details saved successfully.';
        const labelSaving = form?.dataset.labelSaving || 'Saving...';

        if (!form || !saveButton) {
            return;
        }

        $('.old-select2-multiple-choice')
            .not('#detail-studies, #detail-sites')
            .select2({
                width: '100%',
                closeOnSelect: false,
                placeholder: function () {
                    return $(this).data('placeholder') || '';
                },
            });

        if ($studySelect.length > 0) {
            $studySelect.select2({
                width: '100%',
                closeOnSelect: false,
                placeholder: function () {
                    return $(this).data('placeholder') || '';
                },
                ajax: studiesApiUrl
                    ? {
                        url: studiesApiUrl,
                        dataType: 'json',
                        delay: 250,
                        data: function (params) {
                            return { q: params.term || '' };
                        },
                        processResults: function (payload) {
                            return { results: payload?.results || [] };
                        },
                    }
                    : undefined,
            });
        }

        if ($siteSelect.length > 0) {
            $siteSelect.select2({
                width: '100%',
                closeOnSelect: false,
                placeholder: function () {
                    return $(this).data('placeholder') || '';
                },
                ajax: studySitesApiUrl
                    ? {
                        url: studySitesApiUrl,
                        dataType: 'json',
                        delay: 250,
                        data: function (params) {
                            const selectedStudyIds = $studySelect.val() || [];
                            return {
                                q: params.term || '',
                                study_ids: selectedStudyIds.join(','),
                            };
                        },
                        processResults: function (payload) {
                            return { results: payload?.results || [] };
                        },
                    }
                    : undefined,
            });
        }

        const originalSaveLabel = saveButton.textContent.trim();

        function setFeedback(message, tone) {
            if (!feedback) {
                return;
            }
            feedback.textContent = message;
            feedback.classList.remove('is-success', 'is-error');
            if (tone) {
                feedback.classList.add(`is-${tone}`);
            }
            feedback.hidden = !message;
        }

        function clearFeedback() {
            setFeedback('', '');
        }

        function flattenErrors(errors) {
            return Object.values(errors || {})
                .flat()
                .map((item) => item.message)
                .filter(Boolean)
                .join(' ');
        }

        function syncSiteSelectState() {
            if ($studySelect.length === 0 || $siteSelect.length === 0) {
                return;
            }
            const selectedStudyIds = $studySelect.val() || [];
            const hasSelectedStudies = selectedStudyIds.length > 0;
            $siteSelect.prop('disabled', !hasSelectedStudies || !canManagePermissions);
            if (!hasSelectedStudies) {
                $siteSelect.val(null).trigger('change');
            }
        }

        function getPayload() {
            const payload = {
                first_name: form.querySelector('#detail-first-name')?.value || '',
                last_name: form.querySelector('#detail-last-name')?.value || '',
                email: form.querySelector('#detail-email')?.value || '',
                phone_number: form.querySelector('#detail-phone-number')?.value || '',
                is_active: form.querySelector('#detail-is-active')?.checked || false,
                role: form.querySelector('#detail-role')?.value || '',
                permission_groups: $('#detail-permission-groups').val() || [],
                studies: $studySelect.val() || [],
                sites: $siteSelect.val() || [],
            };

            if (enablePasswordChange?.checked) {
                payload.new_password = newPasswordInput?.value || '';
                payload.confirm_password = confirmPasswordInput?.value || '';
            }
            return payload;
        }

        function validatePasswordInputs() {
            if (!enablePasswordChange?.checked) {
                return true;
            }
            const newPwd = newPasswordInput?.value || '';
            const confirmPwd = confirmPasswordInput?.value || '';
            return Boolean(newPwd.trim() && confirmPwd.trim());
        }

        function updateSaveButtonState() {
            saveButton.disabled = !validatePasswordInputs();
        }

        function syncPasswordChangeState() {
            if (!passwordPanel) {
                return;
            }

            const isEnabled = !!enablePasswordChange?.checked;
            passwordPanel.hidden = !isEnabled;

            if (newPasswordInput) {
                newPasswordInput.disabled = !isEnabled;
                if (!isEnabled) {
                    newPasswordInput.value = '';
                }
            }
            if (confirmPasswordInput) {
                confirmPasswordInput.disabled = !isEnabled;
                if (!isEnabled) {
                    confirmPasswordInput.value = '';
                }
            }
            updateSaveButtonState();
        }

        if ($studySelect.length > 0 && $siteSelect.length > 0) {
            syncSiteSelectState();
            $studySelect.on('change', function () {
                $siteSelect.val(null).trigger('change');
                syncSiteSelectState();
            });
        }

        if (enablePasswordChange) {
            enablePasswordChange.addEventListener('change', function () {
                clearFeedback();
                syncPasswordChangeState();
            });
        }
        if (newPasswordInput) {
            newPasswordInput.addEventListener('input', updateSaveButtonState);
        }
        if (confirmPasswordInput) {
            confirmPasswordInput.addEventListener('input', updateSaveButtonState);
        }

        syncPasswordChangeState();

        saveButton.addEventListener('click', async function () {
            clearFeedback();
            if (!validatePasswordInputs()) {
                setFeedback(messagePasswordRequired, 'error');
                return;
            }

            saveButton.disabled = true;
            saveButton.textContent = labelSaving;

            try {
                const response = await fetch(form.dataset.saveUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify(getPayload()),
                });

                const payload = await response.json().catch(function () {
                    return {};
                });

                if (!response.ok) {
                    setFeedback(payload.detail || flattenErrors(payload.errors) || messageSaveFailed, 'error');
                    return;
                }

                setFeedback(payload.detail || messageSaveSuccess, 'success');
                if (payload.redirect_url) {
                    window.location.href = payload.redirect_url;
                }
            } catch (error) {
                setFeedback(messageSaveFailed, 'error');
            } finally {
                saveButton.disabled = !canUpdateDetail;
                saveButton.textContent = originalSaveLabel;
                updateSaveButtonState();
            }
        });

        form.addEventListener('reset', function () {
            clearFeedback();
            window.setTimeout(function () {
                $('#detail-role').trigger('change.select2');
                $('#detail-permission-groups').trigger('change.select2');
                $('#detail-studies').trigger('change.select2');
                $('#detail-sites').trigger('change.select2');
                syncSiteSelectState();
                syncPasswordChangeState();
            }, 0);
        });
    });
})();
