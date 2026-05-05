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
    });
})();
