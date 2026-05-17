(function () {
    const form = document.querySelector('.crf-builder-form');
    if (!form) {
        return;
    }

    const d = form.dataset;
    window.CRF_FORM_BUILDER_I18N = {
        createField: d.formBuilderI18nCreateField || 'Create Field',
        fieldPrefix: d.formBuilderI18nFieldPrefix || 'Field',
        sectionPrefix: d.formBuilderI18nSectionPrefix || 'Section',
        noStyle: d.formBuilderI18nNoStyle || 'Chua co style',
        manage: d.formBuilderI18nManage || 'Quan ly',
        targetLabel: d.formBuilderI18nTargetLabel || 'Target:',
        validationRule: d.formBuilderI18nValidationRule || 'Validation Rule',
        ruleType: d.formBuilderI18nRuleType || 'Rule Type',
        condition: d.formBuilderI18nCondition || 'Condition',
        severity: d.formBuilderI18nSeverity || 'Severity',
        mode: d.formBuilderI18nMode || 'Mode',
        messageMultiLang: d.formBuilderI18nMessageMultiLang || 'Message (Multi-lang)',
        addMessage: d.formBuilderI18nAddMessage || '+ Add Message',
    };
})();
