(function () {
    const $ = window.jQuery;
    if (!$ || !$.fn.select2) {
        return;
    }

    $(function () {
        const form = document.querySelector('[data-site-form]');
        const membershipsApiUrl = form?.dataset.membershipsApiUrl || '';
        const $investigatorSelect = $('.site-investigator-select');

        $('.old-select2-single-choice').not('.site-investigator-select').select2({
            width: '100%',
            placeholder: function () {
                return $(this).data('placeholder') || '';
            },
        });

        if ($investigatorSelect.length > 0) {
            $investigatorSelect.select2({
                width: '100%',
                placeholder: function () {
                    return $(this).data('placeholder') || '';
                },
                allowClear: true,
                ajax: membershipsApiUrl ? {
                    url: membershipsApiUrl,
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        return { q: params.term || '' };
                    },
                    processResults: function (payload) {
                        return { results: payload?.results || [] };
                    },
                } : undefined,
            });
        }
    });
})();
