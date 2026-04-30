(function () {
    const i18n = window.CRF_FORM_BUILDER_I18N || {};
    const sectionIdMatch = window.location.search.match(/(?:\?|&)section_id=(\d+)/);
    const fieldIdMatch = window.location.search.match(/(?:\?|&)field_id=(\d+)/);
    const builderForm = document.querySelector('.crf-builder-form');
    const fieldAddButtons = Array.from(document.querySelectorAll('[data-field-add]'));
    const fieldPanelAddButton = document.querySelector('[data-field-panel-add]');
    const fieldDraftPanelsContainer = document.querySelector('[data-field-draft-panels]');
    const sectionsShowButton = document.querySelector('[data-sections-show]');
    const fieldsShowButton = document.querySelector('[data-fields-show]');
    const deleteSectionButtons = Array.from(document.querySelectorAll('[data-delete-section]'));
    const deleteFieldButtons = Array.from(document.querySelectorAll('[data-delete-field]'));
    const sdtmModal = document.querySelector('[data-sdtm-modal]');
    const sdtmModalEditor = document.querySelector('[data-sdtm-modal-editor]');
    const sdtmCloseButtons = Array.from(document.querySelectorAll('[data-sdtm-close], [data-sdtm-cancel]'));
    const sdtmSaveButton = document.querySelector('[data-sdtm-save]');
    const sdtmDomainInput = document.querySelector('[data-sdtm-domain]');
    const sdtmVariableInput = document.querySelector('[data-sdtm-variable]');
    const sdtmRoleInput = document.querySelector('[data-sdtm-role]');
    const sectionAddButtons = Array.from(document.querySelectorAll('[data-section-add]'));
    const sectionDraftPanelsContainer = document.querySelector('[data-section-draft-panels]');
    const styleModal = document.querySelector('[data-ui-config-modal]');
    const styleCloseButtons = Array.from(document.querySelectorAll('[data-ui-config-modal-close], [data-ui-config-modal-cancel]'));
    const styleSaveButton = document.querySelector('[data-ui-config-modal-save]');
    const styleAddButton = document.querySelector('[data-ui-config-modal-add]');
    const styleItemsContainer = document.querySelector('[data-ui-config-modal-items]');
    const isBuilder2 = Boolean(builderForm?.classList.contains('builder2-form'));
    const builderInitial = window.CRF_FORM_BUILDER_INITIAL || null;
    let sectionDraftTemplate = null;

    function normalizeObject(value) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            return null;
        }
        return value;
    }

    function parseCompositeValue(rawValue) {
        return String(rawValue || '')
            .split(/\s*\+\s*/)
            .map((item) => item.trim())
            .filter((item) => item.length > 0)
            .slice(0, 3);
    }

    function formatCompositeValue(parts) {
        return parts.filter((item) => item).join(' + ');
    }

    function insertSeparator(event) {
        const isPlusKey = event.key === '+' || (event.key === '=' && event.shiftKey) || event.code === 'NumpadAdd';
        const isSpaceKey = event.key === ' ';
        if ((!isPlusKey && !isSpaceKey) || event.isComposing) {
            return;
        }

        const input = event.currentTarget;
        if (!(input instanceof HTMLInputElement)) {
            return;
        }

        event.preventDefault();
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? input.value.length;
        const before = input.value.slice(0, start);
        const after = input.value.slice(end);
        const nextValue = `${before} + ${after}`.replace(/\s*\+\s*\+\s*/g, ' + ');
        input.value = nextValue;
        const nextCaret = start + 3;
        input.setSelectionRange(nextCaret, nextCaret);
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function syncSource(editor, options = {}) {
        const { canonicalizeDisplay = false } = options;
        const source = editor.querySelector('textarea[name="sdtm"], input[name="sdtm"]');
        const compositeInput = editor.querySelector('[data-sdtm-composite]');
        const parts = parseCompositeValue(compositeInput?.value || '');

        if (source) {
            source.value = JSON.stringify({
                domain: parts[0] || '',
                variable: parts[1] || '',
                role: parts[2] || '',
            }, null, 2);
        }

        if (compositeInput && canonicalizeDisplay) {
            const formatted = formatCompositeValue(parts);
            if (compositeInput.value !== formatted) {
                compositeInput.value = formatted;
            }
        }
    }

    function setFieldDefinitionCollapsed(panel, isCollapsed) {
        if (!panel) {
            return;
        }

        const toggle = panel.querySelector('[data-field-definition-toggle]');
        panel.classList.toggle('is-collapsed', Boolean(isCollapsed));
        if (toggle) {
            toggle.setAttribute('aria-expanded', String(!isCollapsed));
        }
    }

    function setCollapsiblePanelState(panelName, isCollapsed) {
        const panel = document.querySelector(`[data-collapsible-panel="${panelName}"]`);
        const toggle = document.querySelector(`[data-collapsible-toggle="${panelName}"] .crf-collapsible-panel__toggle`);

        if (!panel || !toggle) {
            return;
        }

        panel.classList.toggle('is-collapsed', Boolean(isCollapsed));
        toggle.setAttribute('aria-expanded', String(!isCollapsed));
    }

    function setBuilderPanelView(panelName, viewName) {
        document.querySelectorAll(`[data-builder-panel-view="${panelName}"]`).forEach((view) => {
            view.hidden = view.getAttribute('data-builder-panel-mode') !== viewName;
        });
    }

    function setBuilderPanelVisibility(panelName, isVisible) {
        const panel = document.querySelector(`[data-builder-panel="${panelName}"]`);
        if (panel) {
            panel.hidden = !isVisible;
        }
    }

    function setFieldFormActionVisibility(isVisible) {
        document.querySelectorAll('[data-field-form-action]').forEach((button) => {
            button.hidden = !isVisible;
        });
    }

    let activeSdtmEditor = null;
    let activeSdtmPanel = null;
    let activeSdtmCompositeInput = null;
    let activeSdtmSourceInput = null;
    let activeUiConfigEditor = null;

    function openBuilderPanel(panelName, options = {}) {
        const { focusFirstField = true, scrollIntoView = true } = options;
        const section = document.querySelector(`[data-builder-panel="${panelName}"]`);

        if (section) {
            section.hidden = false;
        }

        setCollapsiblePanelState(panelName, false);

        if (focusFirstField) {
            const focusSelector = panelName === 'sections'
                ? '[name="section_code"], [name$="-section_code"]'
                : '[name="field_key"], [name$="-field_key"]';
            const firstField = document.querySelector(focusSelector);
            if (firstField && typeof firstField.focus === 'function') {
                firstField.focus();
            }
        }

        if (scrollIntoView && section && typeof section.scrollIntoView === 'function') {
            section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function switchSectionFormToCreateMode(panel) {
        if (!panel) return;
        panel.querySelectorAll('input[name], textarea[name], select[name]').forEach((field) => {
            if (field.type === 'checkbox') {
                field.checked = false;
                return;
            }

            if (field.tagName === 'SELECT') {
                field.selectedIndex = 0;
                field.dispatchEvent(new Event('change', { bubbles: true }));
                return;
            }

            field.value = '';
        });

        const sectionTemplateIdInput = getSectionFieldControl(panel, 'section_template_id');
        if (sectionTemplateIdInput) {
            sectionTemplateIdInput.value = '';
        }

        [
            'section_code',
            'section_name_en',
            'section_name_vi',
            'description_en',
            'description_vi',
            'help_text_en',
            'help_text_vi',
            'instruction_text_en',
            'instruction_text_vi',
            'display_order',
            'min_repeats',
            'max_repeats'
        ].forEach((fieldName) => {
            const field = getSectionFieldControl(panel, fieldName);
            if (!field) {
                return;
            }

            if (field.type === 'checkbox') {
                field.checked = false;
                return;
            }

            if (field.tagName === 'SELECT') {
                field.selectedIndex = 0;
                field.dispatchEvent(new Event('change', { bubbles: true }));
                return;
            }

            field.value = '';
        });

        const isRequiredField = getSectionFieldControl(panel, 'is_required');
        if (isRequiredField) {
            isRequiredField.checked = true;
        }

        const isRepeatableField = getSectionFieldControl(panel, 'is_repeatable');
        if (isRepeatableField) {
            isRepeatableField.checked = false;
        }

        panel.dataset.sectionId = '';
    }

    function getSectionDraftPanels() {
        if (!sectionDraftPanelsContainer) return [];
        return Array.from(sectionDraftPanelsContainer.querySelectorAll('[data-section-draft-panel]'));
    }

    function getActiveSectionDraftPanel() {
        return getSectionDraftPanels().find((panel) => panel.dataset.sectionDraftActive === 'true') || null;
    }

    function getLastSectionDraftPanel() {
        const panels = getSectionDraftPanels();
        return panels.length ? panels[panels.length - 1] : null;
    }

    function getSectionDraftTemplate() {
        if (!sectionDraftPanelsContainer) {
            return null;
        }

        if (!sectionDraftTemplate) {
            const sourcePanel = sectionDraftPanelsContainer.querySelector('[data-section-draft-panel]');
            if (!sourcePanel) {
                return null;
            }
            sectionDraftTemplate = sourcePanel.cloneNode(true);
        }

        return sectionDraftTemplate.cloneNode(true);
    }

    function getSectionFieldControl(panel, fieldName) {
        if (!panel || !fieldName) {
            return null;
        }

        return panel.querySelector(`[name="${fieldName}"], [name$="-${fieldName}"]`);
    }

    function setSectionFieldValue(panel, fieldName, value) {
        const field = getSectionFieldControl(panel, fieldName);
        if (!field) {
            return;
        }

        if (field.type === 'checkbox') {
            field.checked = Boolean(value);
            return;
        }

        if (value === null || value === undefined) {
            field.value = '';
            return;
        }

        field.value = String(value);
    }

    function cleanupClonedSectionPanel(panel, panelIndex) {
        if (!panel) return;
        panel.removeAttribute('data-section-draft-initialized');
        panel.removeAttribute('data-section-draft-active');
        panel.dataset.sectionDraftIndex = String(panelIndex);
        panel.dataset.sectionId = '';

        panel.querySelectorAll('.user-detail-field__error').forEach((el) => {
            el.innerHTML = '';
        });

        panel.querySelectorAll('input, select, textarea').forEach((control, index) => {
            if (!control.id) {
                return;
            }

            const previousId = control.id;
            const nextId = `${previousId}--panel-${panelIndex}-${index}`;
            panel.querySelectorAll(`label[for="${previousId}"]`).forEach((label) => {
                label.setAttribute('for', nextId);
            });
            control.id = nextId;
        });
    }

    function updateSectionDraftPanelTitle(panel) {
        if (!panel) return;
        const title = panel.querySelector('[data-section-draft-title]');
        if (!title) return;
        const panelIndex = Number(panel.dataset.sectionDraftIndex || '1') || 1;
        const sectionCode = getSectionFieldControl(panel, 'section_code')?.value?.trim() || '';
        const sectionNameEn = getSectionFieldControl(panel, 'section_name_en')?.value?.trim() || '';
        const sectionNameVi = getSectionFieldControl(panel, 'section_name_vi')?.value?.trim() || '';
        const displayTitle = sectionNameEn || sectionNameVi || sectionCode;
        title.textContent = displayTitle || `${i18n.sectionPrefix || 'Section'} ${panelIndex}`;
    }

    function bindSectionDraftPanelTitleSync(panel) {
        ['section_code', 'section_name_en', 'section_name_vi'].forEach((fieldName) => {
            const control = getSectionFieldControl(panel, fieldName);
            if (!control || control.dataset.sectionTitleBound === 'true') {
                return;
            }
            control.dataset.sectionTitleBound = 'true';
            control.addEventListener('input', () => updateSectionDraftPanelTitle(panel));
        });
    }

    function populateSectionDraftPanel(panel, sectionData) {
        if (!panel) {
            return;
        }

        const translations = sectionData?.translations || {};
        const enTranslation = translations.en || {};
        const viTranslation = translations.vi || {};

        setSectionFieldValue(panel, 'section_template_id', sectionData?.id || '');
        setSectionFieldValue(panel, 'section_code', sectionData?.section_code || '');
        setSectionFieldValue(panel, 'section_name_en', enTranslation.section_name || sectionData?.section_name || '');
        setSectionFieldValue(panel, 'section_name_vi', viTranslation.section_name || sectionData?.section_name || '');
        setSectionFieldValue(panel, 'description_en', enTranslation.description || '');
        setSectionFieldValue(panel, 'description_vi', viTranslation.description || '');
        setSectionFieldValue(panel, 'help_text_en', enTranslation.help_text || '');
        setSectionFieldValue(panel, 'help_text_vi', viTranslation.help_text || '');
        setSectionFieldValue(panel, 'instruction_text_en', enTranslation.instruction_text || '');
        setSectionFieldValue(panel, 'instruction_text_vi', viTranslation.instruction_text || '');
        setSectionFieldValue(panel, 'display_order', sectionData?.display_order ?? 1);
        setSectionFieldValue(panel, 'is_required', sectionData?.is_required ?? true);
        setSectionFieldValue(panel, 'is_repeatable', sectionData?.is_repeatable ?? false);
        setSectionFieldValue(panel, 'min_repeats', sectionData?.min_repeats ?? 0);
        setSectionFieldValue(panel, 'max_repeats', sectionData?.max_repeats ?? '');

        panel.dataset.sectionId = sectionData?.id ? String(sectionData.id) : '';
        updateSectionDraftPanelTitle(panel);
    }

    function setAllSectionDraftPanelsInactive() {
        getSectionDraftPanels().forEach((draftPanel) => {
            draftPanel.dataset.sectionDraftActive = 'false';
            draftPanel.classList.remove('is-active');
            draftPanel.querySelectorAll('input, select, textarea, button[type="submit"]').forEach((control) => {
                control.disabled = true;
            });
        });
    }

    function collapseOtherSectionPanels(exceptPanel = null) {
        getSectionDraftPanels().forEach((draftPanel) => {
            setSectionDefinitionCollapsed(draftPanel, draftPanel !== exceptPanel);
        });
    }

    function buildSectionDraftPanel(sectionData = null) {
        if (!sectionDraftPanelsContainer) {
            return null;
        }

        const panel = getSectionDraftTemplate();
        if (!panel) {
            return null;
        }

        const nextIndex = getSectionDraftPanels().length + 1;
        cleanupClonedSectionPanel(panel, nextIndex);
        sectionDraftPanelsContainer.appendChild(panel);
        initializeSectionDraftPanel(panel);

        if (sectionData) {
            populateSectionDraftPanel(panel, sectionData);
        } else {
            switchSectionFormToCreateMode(panel);
            updateSectionDraftPanelTitle(panel);
        }

        return panel;
    }

    function setSectionDefinitionCollapsed(panel, isCollapsed) {
        if (!panel) return;
        panel.dataset.sectionDefinitionCollapsed = String(isCollapsed);
        panel.classList.toggle('is-collapsed', isCollapsed);
        const toggle = panel.querySelector('[data-section-definition-toggle]');
        if (toggle) {
            toggle.setAttribute('aria-expanded', String(!isCollapsed));
        }
    }

    function setSectionDraftPanelActive(panel, isActive) {
        getSectionDraftPanels().forEach((draftPanel) => {
            const isTarget = draftPanel === panel && isActive;
            draftPanel.dataset.sectionDraftActive = String(isTarget);
            draftPanel.classList.toggle('is-active', isTarget);
            draftPanel.querySelectorAll('input, select, textarea, button[type="submit"]').forEach((control) => {
                control.disabled = !isTarget;
            });
        });
    }

    function activateSectionDraftPanel(panel, options = {}) {
        if (!panel) return;
        const { focusFirstField = true } = options;
        collapseOtherSectionPanels(panel);
        setSectionDraftPanelActive(panel, true);
        setSectionDefinitionCollapsed(panel, false);
        if (focusFirstField) {
            const firstField = getSectionFieldControl(panel, 'section_code');
            firstField?.focus?.();
        }
    }

    function cloneSectionDraftPanel(sourcePanel) {
        if (!sourcePanel && !sectionDraftPanelsContainer) return null;
        const clonedPanel = buildSectionDraftPanel();
        if (!clonedPanel) {
            return null;
        }

        collapseOtherSectionPanels(clonedPanel);

        clonedPanel.classList.add('crf-definition-panel--entering');
        clonedPanel.addEventListener('animationend', () => {
            clonedPanel.classList.remove('crf-definition-panel--entering');
        }, { once: true });

        setSectionDefinitionCollapsed(clonedPanel, false);
        setSectionDraftPanelActive(clonedPanel, true);

        setTimeout(() => {
            if (typeof clonedPanel.scrollIntoView === 'function') {
                clonedPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }, 100);
        return clonedPanel;
    }

    function initializeSectionDraftPanel(panel) {
        if (!panel || panel.dataset.sectionDraftInitialized === 'true') return;
        panel.dataset.sectionDraftInitialized = 'true';
        updateSectionDraftPanelTitle(panel);
        bindSectionDraftPanelTitleSync(panel);

        const header = panel.querySelector('.crf-definition-panel__header');
        const toggleButton = panel.querySelector('[data-section-definition-toggle]');
        const deleteButton = panel.querySelector('[data-delete-section-draft]');

        header?.addEventListener('click', (event) => {
            if (event.target.closest('button')) {
                return;
            }
            activateSectionDraftPanel(panel, { focusFirstField: false });
        });

        toggleButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            const isCollapsed = panel.classList.contains('is-collapsed');
            setSectionDefinitionCollapsed(panel, !isCollapsed);
            if (isCollapsed) {
                setSectionDraftPanelActive(panel, true);
            }
        });

        deleteButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            const panels = getSectionDraftPanels();
            if (panels.length > 1) {
                panel.remove();
                const remaining = getSectionDraftPanels();
                remaining.forEach((p, index) => {
                    p.dataset.sectionDraftIndex = String(index + 1);
                    updateSectionDraftPanelTitle(p);
                });
                const last = remaining[remaining.length - 1];
                if (last) activateSectionDraftPanel(last);
            } else {
                switchSectionFormToCreateMode(panel);
            }
        });

        panel.addEventListener('focusin', () => {
            setSectionDraftPanelActive(panel, true);
        });
    }

    function showSectionsList() {
        setBuilderPanelVisibility('fields', false);
        setBuilderPanelVisibility('sections', true);
        setBuilderPanelView('sections', 'list');
        openBuilderPanel('sections', { focusFirstField: false });
    }

    function showFieldsList() {
        setBuilderPanelVisibility('sections', false);
        setBuilderPanelVisibility('fields', true);
        setBuilderPanelView('fields', 'list');
        setFieldFormActionVisibility(false);
        openBuilderPanel('fields', { focusFirstField: false });
    }

    function showSectionsForm(options = {}) {
        const { focusFirstField = true, expandActivePanel = true } = options;
        setBuilderPanelVisibility('fields', false);
        setBuilderPanelVisibility('sections', true);
        setBuilderPanelView('sections', 'form');
        openBuilderPanel('sections', { focusFirstField, scrollIntoView: false });

        const activePanel = getActiveSectionDraftPanel() || getLastSectionDraftPanel();
        if (activePanel && expandActivePanel) {
            activateSectionDraftPanel(activePanel, { focusFirstField: false });
        } else if (!expandActivePanel) {
            setAllSectionDraftPanelsInactive();
        }
    }

    function showFieldsForm() {
        setBuilderPanelVisibility('sections', false);
        setBuilderPanelVisibility('fields', true);
        setBuilderPanelView('fields', 'form');
        setFieldFormActionVisibility(true);
        const section = document.querySelector('[data-builder-panel="fields"]');
        if (section) {
            section.hidden = false;
        }
        const activePanel = getActiveFieldDraftPanel() || getLastFieldDraftPanel();
        if (activePanel) {
            activateFieldDraftPanel(activePanel, { focusFirstField: false });
        }
    }

    function expandSectionPanelById(sectionId, options = {}) {
        const normalizedSectionId = String(sectionId || '').trim();
        if (!normalizedSectionId) {
            return;
        }

        showSectionsForm({ focusFirstField: false, expandActivePanel: false });
        const targetPanel = getSectionDraftPanels().find((panel) => String(panel.dataset.sectionId || '') === normalizedSectionId);
        if (!targetPanel) {
            return;
        }

        collapseOtherSectionPanels(targetPanel);
        activateSectionDraftPanel(targetPanel, { focusFirstField: false });

        if (options.scrollIntoView !== false && typeof targetPanel.scrollIntoView === 'function') {
            targetPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function initializeBuilder2SectionPanels() {
        if (!isBuilder2 || !sectionDraftPanelsContainer) {
            return;
        }

        const existingSections = Array.isArray(builderInitial?.sections)
            ? builderInitial.sections.filter((section) => section && section.id)
            : [];

        getSectionDraftTemplate();
        sectionDraftPanelsContainer.innerHTML = '';

        existingSections.forEach((sectionData) => {
            const panel = buildSectionDraftPanel(sectionData);
            if (panel) {
                setSectionDefinitionCollapsed(panel, true);
            }
        });

        showSectionsForm({ focusFirstField: false, expandActivePanel: false });
        setAllSectionDraftPanelsInactive();

        if (sectionIdMatch) {
            expandSectionPanelById(sectionIdMatch[1], { scrollIntoView: false });
        }
    }

    function getFieldDraftPanels() {
        if (!fieldDraftPanelsContainer) {
            return [];
        }

        return Array.from(fieldDraftPanelsContainer.querySelectorAll('[data-field-draft-panel]'));
    }

    function getActiveFieldDraftPanel() {
        return getFieldDraftPanels().find((panel) => panel.dataset.fieldDraftActive === 'true') || null;
    }

    function getLastFieldDraftPanel() {
        const panels = getFieldDraftPanels();
        return panels.length ? panels[panels.length - 1] : null;
    }

    function cleanupClonedFieldPanel(panel, panelIndex) {
        if (!panel) {
            return;
        }

        panel.removeAttribute('data-field-draft-initialized');
        panel.removeAttribute('data-field-draft-active');
        panel.dataset.fieldDraftIndex = String(panelIndex);
        panel.querySelectorAll('[data-sdtm-modal], [data-ui-config-modal]').forEach((node) => node.remove());
        panel.querySelectorAll('.select2-container').forEach((node) => node.remove());
        panel.querySelectorAll('.select2-hidden-accessible').forEach((control) => {
            control.classList.remove('select2-hidden-accessible');
            control.removeAttribute('data-select2-id');
            control.removeAttribute('aria-hidden');
            control.removeAttribute('tabindex');
            control.removeAttribute('style');
            control.removeAttribute('aria-describedby');
            control.removeAttribute('aria-labelledby');
            control.removeAttribute('aria-controls');
            control.removeAttribute('title');
        });
        panel.querySelectorAll('[data-sdtm-editor]').forEach((editor) => {
            editor.removeAttribute('data-sdtm-bound');
        });

        ['field-definition-body', 'field-ui-config-body', 'field-validation-body'].forEach((baseId) => {
            const node = panel.querySelector(`#${baseId}`);
            if (node) {
                const nextId = `${baseId}-${panelIndex}`;
                panel.querySelectorAll(`[aria-controls="${baseId}"]`).forEach((control) => {
                    control.setAttribute('aria-controls', nextId);
                });
                node.id = nextId;
            }
        });
    }

    function updateFieldDraftPanelTitle(panel) {
        if (!panel) {
            return;
        }

        const title = panel.querySelector('[data-field-draft-title]');
        if (!title) {
            return;
        }

        const panelIndex = Number(panel.dataset.fieldDraftIndex || '1') || 1;
        title.textContent = `${i18n.fieldPrefix || 'Field'} ${panelIndex}`;
    }

    function cloneFieldDraftPanel(sourcePanel) {
        if (!fieldDraftPanelsContainer || !sourcePanel) {
            return null;
        }

        const nextIndex = getFieldDraftPanels().length + 1;
        const clonedPanel = sourcePanel.cloneNode(true);
        cleanupClonedFieldPanel(clonedPanel, nextIndex);
        updateFieldDraftPanelTitle(clonedPanel);

        // Collapse all existing panels (data is preserved)
        getFieldDraftPanels().forEach((existingPanel) => {
            setFieldDefinitionCollapsed(existingPanel, true);
        });

        fieldDraftPanelsContainer.appendChild(clonedPanel);
        initializeFieldDraftPanel(clonedPanel);
        switchFieldFormToCreateMode(clonedPanel);

        // Animate the new panel in
        clonedPanel.classList.add('crf-definition-panel--entering');
        clonedPanel.addEventListener('animationend', () => {
            clonedPanel.classList.remove('crf-definition-panel--entering');
        }, { once: true });

        setFieldDefinitionCollapsed(clonedPanel, false);
        setFieldDraftPanelActive(clonedPanel, true);

        // Delay scroll to let collapse animation finish
        setTimeout(() => {
            if (typeof clonedPanel.scrollIntoView === 'function') {
                clonedPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }, 100);
        return clonedPanel;
    }

    function setFieldDraftPanelActive(panel, isActive) {
        getFieldDraftPanels().forEach((draftPanel) => {
            draftPanel.dataset.fieldDraftActive = String(draftPanel === panel && isActive);
            draftPanel.classList.toggle('is-active', draftPanel === panel && isActive);
            draftPanel.querySelectorAll('input, select, textarea').forEach((control) => {
                control.disabled = draftPanel !== panel || !isActive;
            });
        });
    }

    function activateFieldDraftPanel(panel, options = {}) {
        if (!panel) {
            return;
        }

        const { focusFirstField = true } = options;
        setFieldDraftPanelActive(panel, true);
        setFieldDefinitionCollapsed(panel, false);
        if (focusFirstField) {
            const firstField = panel.querySelector('[name="field_key"]');
            firstField?.focus?.();
        }
    }

    function initializeFieldDraftPanel(panel) {
        if (!panel || panel.dataset.fieldDraftInitialized === 'true') {
            return;
        }

        panel.dataset.fieldDraftInitialized = 'true';
        updateFieldDraftPanelTitle(panel);

        const toggleButton = panel.querySelector('[data-field-definition-toggle]');
        const addButton = panel.querySelector('[data-field-panel-add]');
        const sdtmButton = panel.querySelector('[data-sdtm-open]');
        const uiConfigOpenButton = panel.querySelector('[data-ui-config-open]');
        const uiConfigManageButtonsInPanel = Array.from(panel.querySelectorAll('[data-ui-config-manage-target]'));
        const sdtmEditor = panel.querySelector('[data-sdtm-editor]');
        const uiConfigEditor = panel.querySelector('[data-ui-config-editor]');

        toggleButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            const isCollapsed = panel.classList.contains('is-collapsed');
            setFieldDefinitionCollapsed(panel, !isCollapsed);
            setFieldDraftPanelActive(panel, true);
        });

        addButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            const activePanel = getActiveFieldDraftPanel() || panel;
            cloneFieldDraftPanel(activePanel);
        });

        sdtmButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            const compositeEditor = panel.querySelector('#field-definition-sdtm [data-sdtm-editor]') || panel.querySelector('[data-sdtm-editor]:not(.crf-definition-panel__header)');
            if (compositeEditor) {
                openSdtmModalForEditor(compositeEditor);
            }
        });

        uiConfigOpenButton?.addEventListener('click', (event) => {
            event.stopPropagation();
            if (uiConfigEditor) {
                openUiConfigModal('style', uiConfigEditor);
            }
        });

        uiConfigManageButtonsInPanel.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                if (uiConfigEditor) {
                    openUiConfigModal(button.dataset.uiConfigManageTarget || '', uiConfigEditor);
                }
            });
        });

        panel.addEventListener('focusin', () => {
            setFieldDraftPanelActive(panel, true);
        });

        initializeSdtmEditors(panel);
        panel.querySelectorAll('[data-validation-rules-editor]').forEach((editor) => {
            initializeValidationRulesEditor(editor);
        });
        panel.querySelectorAll('[data-ui-config-editor]').forEach((editor) => {
            initializeUiConfigEditor(editor);
        });
        initializeSelect2Controls();
    }

    function initializeSdtmEditors(scope) {
        Array.from(scope.querySelectorAll('[data-sdtm-editor]')).forEach((editor) => {
            const compositeInput = editor.querySelector('[data-sdtm-composite]');
            const source = editor.querySelector('textarea[name="sdtm"], input[name="sdtm"]');
            const form = editor.closest('form');

            if (!compositeInput || !source || editor.dataset.sdtmBound === 'true') {
                return;
            }

            editor.dataset.sdtmBound = 'true';

            let initialValue = {};
            try {
                initialValue = normalizeObject(JSON.parse((source.value || '').trim())) || {};
            } catch (error) {
                initialValue = {};
            }

            compositeInput.value = formatCompositeValue([
                initialValue.domain || '',
                initialValue.variable || '',
                initialValue.role || '',
            ]);

            compositeInput.addEventListener('keydown', insertSeparator);
            compositeInput.addEventListener('input', () => syncSource(editor));
            compositeInput.addEventListener('blur', () => syncSource(editor, { canonicalizeDisplay: true }));

            if (form) {
                form.addEventListener('submit', () => syncSource(editor, { canonicalizeDisplay: true }));
            }

            syncSource(editor, { canonicalizeDisplay: true });
        });
    }

    function submitDeleteAction(button, confirmMessage) {
        if (!builderForm || !button) {
            return;
        }

        if (!window.confirm(confirmMessage)) {
            return;
        }

        if (typeof builderForm.requestSubmit === 'function') {
            builderForm.requestSubmit(button);
            return;
        }

        builderForm.submit();
    }

    function bindCollapsiblePanels() {
        document.querySelectorAll('[data-collapsible-toggle]').forEach((header) => {
            header.addEventListener('click', () => {
                const panelName = header.getAttribute('data-collapsible-toggle');
                if (!panelName) {
                    return;
                }

                const panel = document.querySelector(`[data-collapsible-panel="${panelName}"]`);
                if (!panel) {
                    return;
                }

                const isCollapsed = panel.classList.contains('is-collapsed');
                setCollapsiblePanelState(panelName, !isCollapsed);
            });
        });
    }

    function switchFieldFormToCreateMode(panel) {
        if (!panel) {
            return;
        }

        const fieldIdInput = panel.querySelector('input[name="field_id"]');
        const submitButton = panel.querySelector('button[name="builder_action"][value="field"]');

        if (fieldIdInput) {
            fieldIdInput.value = '';
        }

        [
            'field_key',
            'label_en',
            'label_vi',
            'sdtm',
            'unit',
            'range_min',
            'range_max',
            'precision',
            'allowed_missing_values',
            'codelist',
            'data_semantic',
            'comments',
            'text_max_length',
            'text_min_length',
            'pattern',
            'pattern_err_msg',
            'layout',
            'text',
            'behavior',
            'options',
            'style',
            'validation_rules_json'
        ].forEach((fieldName) => {
            panel.querySelectorAll(`[name="${fieldName}"]`).forEach((field) => {
                if (field.type === 'checkbox') {
                    field.checked = false;
                    return;
                }

                if (field.tagName === 'SELECT') {
                    field.selectedIndex = 0;
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                    return;
                }

                field.value = '';
            });
        });

        panel.querySelectorAll('[data-ui-config-source]').forEach((sourceWrapper) => {
            const sourceInput = sourceWrapper.querySelector('input[name], textarea[name]');
            if (sourceInput) {
                sourceInput.value = '';
                sourceInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });

        panel.querySelectorAll('[data-ui-config-list]').forEach((list) => {
            list.innerHTML = '';
        });

        const validationRowsContainer = panel.querySelector('[data-validation-rules-rows]');
        const validationSource = panel.querySelector('textarea[name="validation_rules_json"]');
        if (validationRowsContainer) {
            validationRowsContainer.innerHTML = '';
            const blankRuleRow = createValidationRuleRow(panel, { rule_type: 'custom', expression: '', messages: { en: '' } });
            validationRowsContainer.appendChild(blankRuleRow);
            const $ = window.jQuery;
            if ($ && $.fn.select2) {
                $(blankRuleRow).find('.old-select2-single-choice').each(function () {
                    const $control = $(this);
                    if ($control.data('select2')) {
                        return;
                    }

                    $control.select2({
                        width: '100%',
                        placeholder: function () {
                            return $control.data('placeholder') || '';
                        },
                    });
                });
            }
        }
        if (validationSource) {
            validationSource.value = '[]';
        }

        const title = panel.querySelector('.crf-definition-panel__title');
        const subtitle = panel.querySelector('.crf-definition-panel__subtitle');
        if (title && !title.hasAttribute('data-field-draft-title')) {
            title.textContent = '';
        }
        if (subtitle) {
            subtitle.textContent = '';
        }

        updateFieldDraftPanelTitle(panel);

        if (submitButton) {
            submitButton.textContent = i18n.createField || 'Create Field';
        }

        setFieldDefinitionCollapsed(panel, false);

        const firstField = panel.querySelector('[name="field_key"]');
        if (firstField && typeof firstField.focus === 'function') {
            firstField.focus();
        }
    }

    function readSdtmSource(editor = activeSdtmEditor) {
        const source = activeSdtmSourceInput
            || activeSdtmPanel?.querySelector('textarea[name="sdtm"], input[name="sdtm"]')
            || (editor ? editor.querySelector('textarea[name="sdtm"], input[name="sdtm"]') : null);
        if (!source) {
            return { domain: '', variable: '', role: '' };
        }

        try {
            const parsed = JSON.parse(String(source.value || '').trim() || '{}');
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
                return { domain: '', variable: '', role: '' };
            }
            return {
                domain: parsed.domain || '',
                variable: parsed.variable || '',
                role: parsed.role || '',
            };
        } catch (error) {
            return { domain: '', variable: '', role: '' };
        }
    }

    function writeSdtmSource(value, editor = activeSdtmEditor) {
        const source = activeSdtmSourceInput
            || activeSdtmPanel?.querySelector('textarea[name="sdtm"], input[name="sdtm"]')
            || (editor ? editor.querySelector('textarea[name="sdtm"], input[name="sdtm"]') : null);
        const compositeInputs = activeSdtmPanel
            ? Array.from(activeSdtmPanel.querySelectorAll('[data-sdtm-composite]'))
            : activeSdtmCompositeInput
                ? [activeSdtmCompositeInput]
                : editor
                    ? Array.from(editor.querySelectorAll('[data-sdtm-composite]'))
                    : [];

        if (source) {
            source.value = JSON.stringify({
                domain: value.domain || '',
                variable: value.variable || '',
                role: value.role || '',
            }, null, 2);
        }

        if (compositeInputs.length > 0) {
            const formattedValue = formatCompositeValue([
                value.domain || '',
                value.variable || '',
                value.role || '',
            ]);

            compositeInputs.forEach((compositeInput) => {
                compositeInput.value = formattedValue;
                compositeInput.dispatchEvent(new Event('input', { bubbles: true }));
            });
        }
    }

    if (styleAddButton) {
        styleAddButton.addEventListener('click', () => {
            if (!styleItemsContainer) {
                return;
            }
            styleItemsContainer.appendChild(createUiConfigModalRow('', ''));
        });
    }

    if (styleSaveButton) {
        styleSaveButton.addEventListener('click', saveUiConfigModal);
    }

    function openSdtmModal() {
        if (!sdtmModal) {
            return;
        }

        const currentValue = readSdtmSource();
        if (sdtmDomainInput) {
            sdtmDomainInput.value = currentValue.domain;
        }
        if (sdtmVariableInput) {
            sdtmVariableInput.value = currentValue.variable;
        }
        if (sdtmRoleInput) {
            sdtmRoleInput.value = currentValue.role;
        }

        sdtmModal.classList.add('is-open');
        sdtmModal.setAttribute('aria-hidden', 'false');
        sdtmDomainInput?.focus();
    }

    function openSdtmModalForEditor(editor) {
        if (!editor) {
            return;
        }

        const compositeEditor = editor.querySelector?.('[data-sdtm-composite]')
            ? editor
            : editor.querySelector?.('#field-definition-sdtm [data-sdtm-editor]')
            || editor.querySelector?.('[data-sdtm-editor]:not(.crf-definition-panel__header)')
            || editor;

        activeSdtmEditor = compositeEditor;
        activeSdtmPanel = compositeEditor?.closest?.('[data-field-draft-panel]') || compositeEditor?.closest?.('.crf-definition-panel') || null;
        activeSdtmCompositeInput = activeSdtmPanel?.querySelector('[data-sdtm-composite]') || compositeEditor?.querySelector?.('[data-sdtm-composite]') || null;
        activeSdtmSourceInput = activeSdtmPanel?.querySelector('textarea[name="sdtm"], input[name="sdtm"]') || compositeEditor?.querySelector?.('textarea[name="sdtm"], input[name="sdtm"]') || null;
        openSdtmModal();
    }

    function closeSdtmModal() {
        if (!sdtmModal) {
            return;
        }

        sdtmModal.classList.remove('is-open');
        sdtmModal.setAttribute('aria-hidden', 'true');
    }

    sectionAddButtons.forEach((button) => {
        button.addEventListener('click', () => {
            if (!isBuilder2) {
                showSectionsForm();
                return;
            }

            showSectionsForm({ focusFirstField: false, expandActivePanel: false });
            const sourcePanel = getActiveSectionDraftPanel() || getLastSectionDraftPanel() || getSectionDraftTemplate();
            if (!sourcePanel) {
                return;
            }
            cloneSectionDraftPanel(sourcePanel);
        });
    });

    if (sectionsShowButton) {
        sectionsShowButton.addEventListener('click', () => {
            showSectionsList();
        });
    }

    deleteSectionButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const target = document.querySelector('input[name="delete_section_id"]');
            if (target) {
                target.value = String(button.dataset.deleteId || '');
            }
            submitDeleteAction(button, 'Delete this section?');
        });
    });

    fieldAddButtons.forEach((button) => {
        button.addEventListener('click', () => {
            showFieldsForm();
        });
    });

    if (fieldPanelAddButton) {
        fieldPanelAddButton.addEventListener('click', () => {
            const sourcePanel = getActiveFieldDraftPanel() || getLastFieldDraftPanel();
            if (sourcePanel) {
                cloneFieldDraftPanel(sourcePanel);
            }
        });
    }

    const sectionPanelAddButton = document.querySelector('[data-section-panel-add]');
    if (sectionPanelAddButton) {
        sectionPanelAddButton.addEventListener('click', () => {
            const sourcePanel = getActiveSectionDraftPanel() || getLastSectionDraftPanel();
            if (sourcePanel) {
                cloneSectionDraftPanel(sourcePanel);
            }
        });
    }

    if (fieldsShowButton) {
        fieldsShowButton.addEventListener('click', () => {
            showFieldsList();
        });
    }

    deleteFieldButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const target = document.querySelector('input[name="delete_field_id"]');
            if (target) {
                target.value = String(button.dataset.deleteId || '');
            }
            submitDeleteAction(button, 'Delete this field?');
        });
    });

    initializeSdtmEditors(document);

    function initializeFieldDraftPanelsOnLoad() {
        const panels = getFieldDraftPanels();
        panels.forEach((panel) => {
            updateFieldDraftPanelTitle(panel);
            initializeFieldDraftPanel(panel);
        });

        if (panels.length > 0) {
            activateFieldDraftPanel(panels[0], { focusFirstField: false });
        }
    }

    function initializeSectionDraftPanelsOnLoad() {
        const panels = getSectionDraftPanels();
        panels.forEach((panel) => {
            updateSectionDraftPanelTitle(panel);
            initializeSectionDraftPanel(panel);
        });

        if (panels.length > 0 && !isBuilder2) {
            activateSectionDraftPanel(panels[0], { focusFirstField: false });
        }
    }

    initializeFieldDraftPanelsOnLoad();
    initializeSectionDraftPanelsOnLoad();
    initializeBuilder2SectionPanels();

    bindCollapsiblePanels();
    setCollapsiblePanelState('sections', false);
    setCollapsiblePanelState('field-ui-config', false);
    setCollapsiblePanelState('field-validation', false);

    if (fieldIdMatch) {
        showFieldsForm();
    } else if (sectionIdMatch && !isBuilder2) {
        showSectionsForm();
    }

    window.CRF_FORM_BUILDER = window.CRF_FORM_BUILDER || {};
    window.CRF_FORM_BUILDER.expandSectionPanel = expandSectionPanelById;

    sdtmCloseButtons.forEach((button) => {
        button.addEventListener('click', closeSdtmModal);
    });

    if (sdtmModal) {
        sdtmModal.addEventListener('click', (event) => {
            if (event.target === sdtmModal) {
                closeSdtmModal();
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && sdtmModal?.classList.contains('is-open')) {
            closeSdtmModal();
        }
    });

    if (sdtmSaveButton) {
        sdtmSaveButton.addEventListener('click', () => {
            writeSdtmSource({
                domain: sdtmDomainInput?.value || '',
                variable: sdtmVariableInput?.value || '',
                role: sdtmRoleInput?.value || '',
            });
            closeSdtmModal();
        });
    }

    [sdtmDomainInput, sdtmVariableInput, sdtmRoleInput].forEach((input) => {
        if (!input) {
            return;
        }
        input.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter') {
                return;
            }
            event.preventDefault();
            if (input === sdtmDomainInput) {
                sdtmVariableInput?.focus();
            } else if (input === sdtmVariableInput) {
                sdtmRoleInput?.focus();
            } else {
                sdtmSaveButton?.click();
            }
        });
    });

    if (sdtmModalEditor) {
        sdtmModalEditor.addEventListener('input', () => {
            // Keep modal values isolated; preview updates only on save.
        });
    }

    ['layout', 'behavior', 'options', 'style'].forEach((target) => renderUiConfigTarget(target));

    function normalizeRuleTranslations(value) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            return {};
        }

        const translations = {};
        Object.keys(value).forEach((languageCode) => {
            const normalizedLanguageCode = String(languageCode || '').trim().toLowerCase();
            const message = String(value[languageCode] || '').trim();
            if (normalizedLanguageCode && message) {
                translations[normalizedLanguageCode] = message;
            }
        });
        return translations;
    }

    function parseValidationRules(rawValue) {
        try {
            const parsed = JSON.parse(String(rawValue || '').trim() || '[]');
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            return [];
        }
    }

    function parseUiConfigObject(rawValue) {
        const normalized = String(rawValue || '').trim();
        if (!normalized) {
            return {};
        }

        try {
            const parsed = JSON.parse(normalized);
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
                return {};
            }
            return Object.entries(parsed).reduce((acc, [key, value]) => {
                const normalizedKey = String(key || '').trim();
                if (!normalizedKey) {
                    return acc;
                }
                acc[normalizedKey] = value == null ? '' : String(value);
                return acc;
            }, {});
        } catch (error) {
            return { value: normalized };
        }
    }

    function stringifyUiConfigObject(value) {
        const entries = Object.entries(value || {}).filter(([key]) => String(key || '').trim());
        if (entries.length === 0) {
            return '';
        }

        return JSON.stringify(
            Object.fromEntries(entries.map(([key, item]) => [String(key), String(item ?? '')])),
            null,
            2,
        );
    }

    function formatTargetLabel(target) {
        return String(target || '')
            .replace(/[_-]+/g, ' ')
            .trim()
            .replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
    }

    function getUiConfigSourceInput(target, scope = document) {
        const sourceWrapper = scope.querySelector(`[data-ui-config-source="${target}"]`);
        return sourceWrapper ? sourceWrapper.querySelector('input[name], textarea[name]') : null;
    }

    function renderUiConfigTarget(target, scope = document) {
        const sourceInput = getUiConfigSourceInput(target, scope);
        const list = scope.querySelector(`[data-ui-config-list="${target}"]`);
        const summary = scope.querySelector('[data-style-summary]');
        const values = parseUiConfigObject(sourceInput?.value || '');

        if (list) {
            list.innerHTML = '';
        }

        if (target === 'style' && summary) {
            const entries = Object.entries(values).filter(([key]) => String(key || '').trim());
            if (!entries.length) {
                summary.textContent = i18n.noStyle || 'Chưa có style';
                summary.classList.add('crf-definition-panel__summary-box--muted');
            } else {
                summary.textContent = entries.map(([key, value]) => `${key}: ${value}`).join(' · ');
                summary.classList.remove('crf-definition-panel__summary-box--muted');
            }
        }

        if (sourceInput) {
            sourceInput.value = stringifyUiConfigObject(values);
        }
    }

    function createUiConfigModalRow(key = '', value = '') {
        const row = document.createElement('div');
        row.className = 'crf-style-modal__item';
        row.innerHTML = `
            <div class="crf-style-modal__item-header">
                <div class="crf-style-modal__item-title">Key / Value</div>
                <button type="button" class="crf-style-modal__item-remove" aria-label="Remove item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 6 6 18"></path>
                        <path d="m6 6 12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
                <div>
                    <label class="user-detail-inline-field__label">Key</label>
                    <input type="text" class="crf-style-modal__field" data-ui-config-row-key placeholder="Enter key" value="${String(key || '').replaceAll('"', '&quot;')}">
                </div>
                <div>
                    <label class="user-detail-inline-field__label">Value</label>
                    <input type="text" class="crf-style-modal__field" data-ui-config-row-value placeholder="Enter value" value="${String(value || '').replaceAll('"', '&quot;')}">
                </div>
            </div>
        `;

        row.querySelector('.crf-style-modal__item-remove')?.addEventListener('click', () => {
            row.remove();
            if (styleItemsContainer && !styleItemsContainer.children.length) {
                styleItemsContainer.appendChild(createUiConfigModalRow('', ''));
            }
        });

        return row;
    }

    function openUiConfigModal(target, editor = activeUiConfigEditor) {
        if (!styleModal || !styleItemsContainer) {
            return;
        }

        const normalizedTarget = String(target || '').trim().toLowerCase();
        if (!normalizedTarget) {
            return;
        }

        activeUiConfigEditor = editor || activeUiConfigEditor;

        const sourceInput = getUiConfigSourceInput(normalizedTarget, activeUiConfigEditor || document);
        const currentValues = parseUiConfigObject(sourceInput?.value || '');
        const entries = Object.entries(currentValues).filter(([key]) => String(key || '').trim());

        styleItemsContainer.innerHTML = '';
        if (entries.length === 0) {
            styleItemsContainer.appendChild(createUiConfigModalRow('', ''));
        } else {
            entries.forEach(([key, value]) => {
                styleItemsContainer.appendChild(createUiConfigModalRow(key, value));
            });
        }

        const modalTitle = document.querySelector('[data-ui-config-modal-title]');
        const modalTargetLabel = document.querySelector('[data-ui-config-modal-target-label]');
        if (modalTitle) {
            modalTitle.textContent = `${i18n.manage || 'Quản lý'} ${formatTargetLabel(normalizedTarget)}`;
        }
        if (modalTargetLabel) {
            modalTargetLabel.textContent = `${i18n.targetLabel || 'Target:'} ${normalizedTarget}`;
        }

        styleModal.dataset.uiConfigTarget = normalizedTarget;
        styleModal.classList.add('is-open');
        styleModal.setAttribute('aria-hidden', 'false');
    }

    function closeUiConfigModal() {
        if (!styleModal) {
            return;
        }

        styleModal.classList.remove('is-open');
        styleModal.setAttribute('aria-hidden', 'true');
        delete styleModal.dataset.uiConfigTarget;
    }

    function saveUiConfigModal() {
        const activeTarget = String(styleModal?.dataset.uiConfigTarget || '').trim().toLowerCase();
        if (!activeTarget || !styleItemsContainer) {
            return;
        }

        const nextValues = {};
        Array.from(styleItemsContainer.querySelectorAll('.crf-style-modal__item')).forEach((row) => {
            const key = String(row.querySelector('[data-ui-config-row-key]')?.value || '').trim();
            const value = String(row.querySelector('[data-ui-config-row-value]')?.value || '').trim();
            if (!key) {
                return;
            }
            nextValues[key] = value;
        });

        const sourceInput = getUiConfigSourceInput(activeTarget, activeUiConfigEditor || document);
        if (sourceInput) {
            sourceInput.value = stringifyUiConfigObject(nextValues);
            sourceInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        renderUiConfigTarget(activeTarget, activeUiConfigEditor || document);
        closeUiConfigModal();
    }

    function initializeUiConfigEditor(editor) {
        const targets = Array.from(
            editor.querySelectorAll('[data-ui-config-source]')
        ).map((element) => String(element.dataset.uiConfigSource || '').trim()).filter((value) => value);
        const sourceInputs = {};
        const sourceValues = {};

        targets.forEach((target) => {
            const sourceElement = editor.querySelector(`[data-ui-config-source="${target}"]`);
            sourceInputs[target] = sourceElement
                ? sourceElement.querySelector('input[name], textarea[name]')
                : null;
            sourceValues[target] = parseUiConfigObject(sourceInputs[target]?.value || '');

            if (sourceInputs[target]) {
                sourceInputs[target].readOnly = true;
                sourceInputs[target].setAttribute('aria-readonly', 'true');
                sourceInputs[target].title = 'Use Add Item to edit key/value.';
                sourceInputs[target].addEventListener('input', () => {
                    sourceValues[target] = parseUiConfigObject(sourceInputs[target].value || '');
                    renderTargetItems(target);
                });
            }
        });

        const openButton = editor.querySelector('[data-ui-config-open]');
        const panel = editor.querySelector('[data-ui-config-item-panel]');
        const cancelButton = editor.querySelector('[data-ui-config-cancel]');
        const addButton = editor.querySelector('[data-ui-config-add]');
        const targetSelect = editor.querySelector('[data-ui-config-target]');
        const keyInput = editor.querySelector('[data-ui-config-key]');
        const valueInput = editor.querySelector('[data-ui-config-value]');

        if (targetSelect) {
            targetSelect.innerHTML = '<option value="">Select target</option>';
            targets.forEach((target) => {
                const option = document.createElement('option');
                option.value = target;
                option.textContent = formatTargetLabel(target);
                targetSelect.appendChild(option);
            });
        }

        if (!targets.length) {
            return;
        }

        function syncTargetInput(target) {
            const sourceInput = sourceInputs[target];
            if (!sourceInput) {
                return;
            }
            sourceInput.value = stringifyUiConfigObject(sourceValues[target]);
        }

        function renderTargetItems(target) {
            const list = editor.querySelector(`[data-ui-config-list="${target}"]`);
            if (!list) {
                return;
            }

            const items = Object.entries(sourceValues[target] || {}).filter(([key]) => String(key || '').trim());
            list.innerHTML = '';

            if (items.length === 0) {
                return;
            }

            items.forEach(([key, value]) => {
                const item = document.createElement('div');
                item.className = 'item';
                item.innerHTML = `
                    <span><strong>${key}</strong>: ${value}</span>
                    <button type="button"
                            class="entity-table__footer-button entity-table__footer-button--secondary"
                            data-ui-config-remove>
                        ×
                    </button>
                `;
                item.querySelector('[data-ui-config-remove]').addEventListener('click', () => {
                    delete sourceValues[target][key];
                    syncTargetInput(target);
                    renderTargetItems(target);
                });
                list.appendChild(item);
            });
        }

        function renderAllTargets() {
            targets.forEach((target) => {
                syncTargetInput(target);
                renderTargetItems(target);
            });
        }

        if (openButton && panel) {
            openButton.addEventListener('click', () => {
                panel.classList.add('is-open');
                if (targetSelect && !targetSelect.value && targets[0]) {
                    targetSelect.value = targets[0];
                }
                keyInput?.focus();
            });
        }

        if (cancelButton && panel) {
            cancelButton.addEventListener('click', () => {
                panel.classList.remove('is-open');
            });
        }

        if (panel) {
            panel.addEventListener('click', (event) => {
                if (event.target === panel) {
                    panel.classList.remove('is-open');
                }
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && panel.classList.contains('is-open')) {
                    panel.classList.remove('is-open');
                }
            });
        }

        if (addButton) {
            addButton.addEventListener('click', () => {
                const target = String(targetSelect?.value || '').trim().toLowerCase();
                const key = String(keyInput?.value || '').trim();
                const value = String(valueInput?.value || '').trim();

                if (!targets.includes(target) || !key) {
                    return;
                }

                sourceValues[target][key] = value;
                syncTargetInput(target);
                renderTargetItems(target);

                if (keyInput) {
                    keyInput.value = '';
                }
                if (valueInput) {
                    valueInput.value = '';
                }
                panel?.classList.remove('is-open');
                keyInput?.focus();
            });
        }

        const form = editor.closest('form');
        if (form) {
            form.addEventListener('submit', () => {
                targets.forEach((target) => syncTargetInput(target));
            });
        }

        renderAllTargets();
    }

    function createTranslationRow(translation = {}, onChange = null) {
        const row = document.createElement('div');
        row.className = 'grid items-start gap-2 md:grid-cols-[88px_minmax(0,1fr)_auto]';
        row.innerHTML = `
            <input type="text"
                                   class="old-textbox text-xs uppercase"
                   placeholder="EN"
                   data-validation-language>
            <input type="text"
                                   class="old-textbox min-w-0 text-sm"
                   placeholder="Message"
                   data-validation-message>
            <button type="button"
                    class="entity-table__footer-button entity-table__footer-button--secondary"
                    data-validation-translation-remove>
                ×
            </button>
        `;

        row.querySelector('[data-validation-language]').value = translation.language_code || '';
        row.querySelector('[data-validation-message]').value = translation.message || '';
        row.querySelector('[data-validation-translation-remove]').addEventListener('click', () => {
            row.remove();
            if (typeof onChange === 'function') {
                onChange();
            }
        });

        row.querySelector('[data-validation-language]').addEventListener('input', () => {
            if (typeof onChange === 'function') {
                onChange();
            }
        });
        row.querySelector('[data-validation-language]').addEventListener('change', () => {
            if (typeof onChange === 'function') {
                onChange();
            }
        });
        row.querySelector('[data-validation-message]').addEventListener('input', () => {
            if (typeof onChange === 'function') {
                onChange();
            }
        });
        row.querySelector('[data-validation-message]').addEventListener('change', () => {
            if (typeof onChange === 'function') {
                onChange();
            }
        });

        return row;
    }

    function createValidationRuleRow(editor, rule = {}) {
        const row = document.createElement('div');
        row.className = 'crf-validation-rule-group';
        row.innerHTML = `
            <div class="crf-validation-rule-group__header">
                <h4 class="crf-validation-rule-group__label">${i18n.validationRule || 'Validation Rule'}</h4>
                <button type="button"
                        class="entity-table__footer-button entity-table__footer-button--secondary crf-validation-rule-group__remove"
                        data-validation-rule-remove>
                    ×
                </button>
            </div>
            <div class="user-detail-inline-row">
                <div class="user-detail-inline-field">
                    <label class="user-detail-inline-field__label">${i18n.ruleType || 'Rule Type'}:</label>
                    <div class="user-detail-inline-field__control-wrap">
                        <select class="old-select2-single-choice" data-validation-rule-type>
                            <option value="hard_limit">Hard Limit</option>
                            <option value="soft_warning">Soft Warning</option>
                            <option value="custom">Custom</option>
                        </select>
                    </div>
                </div>
                <div class="user-detail-inline-field user-detail-inline-field--full">
                    <label class="user-detail-inline-field__label">${i18n.condition || 'Condition'}:</label>
                    <div class="user-detail-inline-field__control-wrap">
                        <input type="text"
                               class="old-textbox"
                               placeholder="$val > 40 && $val < 300"
                               data-validation-expression>
                    </div>
                </div>
            </div>
            <div class="user-detail-inline-row">
                <div class="user-detail-inline-field">
                    <label class="user-detail-inline-field__label">${i18n.severity || 'Severity'}:</label>
                    <div class="user-detail-inline-field__control-wrap">
                        <select class="old-select2-single-choice" data-validation-severity>
                            <option value="error">Error</option>
                            <option value="warning">Warning</option>
                            <option value="info">Info</option>
                        </select>
                    </div>
                </div>
                <div class="user-detail-inline-field">
                    <label class="user-detail-inline-field__label">${i18n.mode || 'Mode'}:</label>
                    <div class="user-detail-inline-field__control-wrap">
                        <select class="old-select2-single-choice" data-validation-mode>
                            <option value="blocking">Blocking</option>
                            <option value="advisory">Advisory</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="user-detail-inline-row">
                <div class="user-detail-inline-field user-detail-inline-field--full">
                    <label class="user-detail-inline-field__label">${i18n.messageMultiLang || 'Message (Multi-lang)'}:</label>
                    <div class="user-detail-inline-field__control-wrap">
                        <div class="crf-validation-rule-group__messages" data-validation-messages></div>
                        <button type="button"
                                class="mt-2 entity-table__footer-button entity-table__footer-button--secondary"
                                data-validation-message-add>
                            ${i18n.addMessage || '+ Add Message'}
                        </button>
                    </div>
                </div>
            </div>
        `;

        row.querySelector('[data-validation-rule-type]').value = rule.rule_type || 'custom';
        row.querySelector('[data-validation-expression]').value = rule.expression || '';
        row.querySelector('[data-validation-severity]').value = rule.severity || 'error';
        row.querySelector('[data-validation-mode]').value = rule.mode || 'blocking';

        const messagesContainer = row.querySelector('[data-validation-messages]');
        const translations = normalizeRuleTranslations(rule.messages || rule.translations || {});
        const translationEntries = Object.entries(translations);

        if (translationEntries.length > 0) {
            translationEntries.forEach(([languageCode, message]) => {
                messagesContainer.appendChild(createTranslationRow(
                    { language_code: languageCode, message },
                    () => syncValidationRulesEditor(editor),
                ));
            });
        } else {
            messagesContainer.appendChild(createTranslationRow(
                { language_code: 'en', message: '' },
                () => syncValidationRulesEditor(editor),
            ));
        }

        row.querySelector('[data-validation-message-add]').addEventListener('click', () => {
            messagesContainer.appendChild(createTranslationRow(
                { language_code: '', message: '' },
                () => syncValidationRulesEditor(editor),
            ));
            syncValidationRulesEditor(editor);
        });

        row.querySelector('[data-validation-rule-remove]').addEventListener('click', () => {
            row.remove();
            syncValidationRulesEditor(editor);
        });

        row.querySelectorAll('input, select').forEach((control) => {
            control.addEventListener('input', () => syncValidationRulesEditor(editor));
            control.addEventListener('change', () => syncValidationRulesEditor(editor));
        });

        messagesContainer.querySelectorAll('input').forEach((control) => {
            control.addEventListener('input', () => syncValidationRulesEditor(editor));
            control.addEventListener('change', () => syncValidationRulesEditor(editor));
        });

        return row;
    }

    function syncValidationRulesEditor(editor) {
        const source = editor.querySelector('textarea[name="validation_rules_json"]');
        const rows = Array.from(editor.querySelectorAll('[data-validation-rules-rows] > .crf-validation-rule-group'));

        if (!source) {
            return;
        }

        const payload = rows.map((row) => {
            const ruleType = row.querySelector('[data-validation-rule-type]')?.value || 'custom';
            const expression = row.querySelector('[data-validation-expression]')?.value || '';
            const severity = row.querySelector('[data-validation-severity]')?.value || 'error';
            const mode = row.querySelector('[data-validation-mode]')?.value || 'blocking';
            const translationRows = Array.from(row.querySelectorAll('[data-validation-messages] > div'));
            const messages = {};

            translationRows.forEach((translationRow) => {
                const languageCode = translationRow.querySelector('[data-validation-language]')?.value || '';
                const message = translationRow.querySelector('[data-validation-message]')?.value || '';
                if (languageCode && message) {
                    messages[String(languageCode).trim().toLowerCase()] = String(message).trim();
                }
            });

            return {
                rule_type: ruleType,
                expression,
                severity,
                mode,
                messages,
            };
        }).filter((rule) => rule.expression || Object.keys(rule.messages).length > 0);

        source.value = JSON.stringify(payload, null, 2);
    }

    function initializeValidationRulesEditor(editor) {
        const source = editor.querySelector('textarea[name="validation_rules_json"]');
        const rowsContainer = editor.querySelector('[data-validation-rules-rows]');
        const addButton = editor.querySelector('[data-validation-rule-add]');

        if (!source || !rowsContainer || !addButton) {
            return;
        }

        const $ = window.jQuery;

        function initSelect2InScope(scope) {
            if (!$ || !$.fn.select2 || !scope) {
                return;
            }

            $(scope).find('.old-select2-single-choice').each(function () {
                const $control = $(this);
                if ($control.data('select2')) {
                    return;
                }

                $control.select2({
                    width: '100%',
                    placeholder: function () {
                        return $control.data('placeholder') || '';
                    },
                });
            });
        }

        const initialRules = parseValidationRules(source.value);

        if (initialRules.length === 0) {
            const row = createValidationRuleRow(editor, { rule_type: 'custom', expression: '', messages: { en: '' } });
            rowsContainer.appendChild(row);
            initSelect2InScope(row);
        } else {
            initialRules.forEach((rule) => {
                const row = createValidationRuleRow(editor, rule);
                rowsContainer.appendChild(row);
                initSelect2InScope(row);
            });
        }

        addButton.addEventListener('click', () => {
            const row = createValidationRuleRow(editor, { rule_type: 'custom', expression: '', messages: { en: '' } });
            rowsContainer.appendChild(row);
            initSelect2InScope(row);
            syncValidationRulesEditor(editor);
        });

        rowsContainer.addEventListener('input', () => syncValidationRulesEditor(editor));
        rowsContainer.addEventListener('change', () => syncValidationRulesEditor(editor));

        initSelect2InScope(editor);
        syncValidationRulesEditor(editor);
    }

    function initializeSelect2Controls() {
        const $ = window.jQuery;

        if (!$ || !$.fn.select2) {
            return;
        }

        $(".old-select2-single-choice").each(function () {
            const $control = $(this);
            if ($control.data('select2')) {
                return;
            }

            $control.select2({
                width: '100%',
                placeholder: function () {
                    return $control.data('placeholder') || '';
                },
            });
        });
    }

    initializeSelect2Controls();
    setFieldFormActionVisibility(false);

    if (sectionIdMatch && !fieldIdMatch) {
        const sectionCard = document.getElementById(`section-card-${sectionIdMatch[1]}`);
        if (sectionCard) {
            sectionCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    if (fieldIdMatch) {
        const fieldCard = document.getElementById(`field-card-${fieldIdMatch[1]}`);
        if (fieldCard) {
            fieldCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
})();
