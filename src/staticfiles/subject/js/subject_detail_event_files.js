(function () {
    document.addEventListener("DOMContentLoaded", function () {
        const form = document.querySelector("[data-eventinstance-file-import-form]");
        const previewLink = document.querySelector("[data-eventinstance-file-preview-link]");
        if (!(form instanceof HTMLFormElement)) {
            if (previewLink instanceof HTMLAnchorElement) {
                previewLink.addEventListener("click", function (event) {
                    event.preventDefault();
                    window.open(previewLink.href, "_blank", "width=1024,height=1024");
                });
            }
            return;
        }

        const trigger = form.querySelector("[data-eventinstance-file-import-trigger]");
        const fileInput = form.querySelector("[data-eventinstance-file-input]");

        if (!(trigger instanceof HTMLElement) || !(fileInput instanceof HTMLInputElement)) {
            return;
        }

        trigger.addEventListener("click", function () {
            fileInput.click();
        });

        fileInput.addEventListener("change", function () {
            if (!fileInput.files || fileInput.files.length === 0) {
                return;
            }
            form.submit();
        });

        if (previewLink instanceof HTMLAnchorElement) {
            previewLink.addEventListener("click", function (event) {
                event.preventDefault();
                window.open(previewLink.href, "_blank", "width=1024,height=1024");
            });
        }
    });
})();
