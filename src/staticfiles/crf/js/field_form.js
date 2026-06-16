(function () {
    const editors = Array.from(document.querySelectorAll('[data-sdtm-editor]'));

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

    editors.forEach((editor) => {
        const compositeInput = editor.querySelector('[data-sdtm-composite]');
        const source = editor.querySelector('textarea[name="sdtm"], input[name="sdtm"]');
        const form = editor.closest('form');

        if (!compositeInput || !source) {
            return;
        }

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
})();
