(function () {
    const roots = Array.from(document.querySelectorAll('[data-date-range-sync]'));

    function parsePickerValue(input) {
        if (!window.flatpickr || !input.value) {
            return null;
        }
        return window.flatpickr.parseDate(
            input.value,
            input.dataset.flatpickrDateFormat || 'Y-m-d'
        );
    }

    roots.forEach((root) => {
        const startId = root.dataset.dateRangeStartId || '';
        const endId = root.dataset.dateRangeEndId || '';
        if (!startId || !endId) {
            return;
        }

        const startInput = document.getElementById(startId);
        const endInput = document.getElementById(endId);
        if (!startInput || !endInput) {
            return;
        }

        function syncEndMin() {
            const endPicker = endInput._flatpickr || null;
            if (startInput.value) {
                if (endPicker) {
                    endPicker.set('minDate', startInput.value);
                }
                const startDate = parsePickerValue(startInput);
                const endDate = parsePickerValue(endInput);
                if (startDate && endDate && endDate < startDate) {
                    endInput.value = '';
                    if (endPicker) {
                        endPicker.clear();
                    }
                }
            } else if (endPicker) {
                endPicker.set('minDate', null);
            }
        }

        startInput.addEventListener('change', syncEndMin);
        syncEndMin();
    });
})();
