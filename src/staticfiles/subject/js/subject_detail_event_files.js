(function () {
    const allowedExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf"];
    const allowedMimeTypes = [
        "image/png",
        "image/jpeg",
        "image/pjpeg",
        "image/gif",
        "image/bmp",
        "image/x-ms-bmp",
        "image/webp",
        "application/pdf",
    ];

    function hasAllowedExtension(fileName) {
        const normalized = String(fileName || "").trim().toLowerCase();
        return allowedExtensions.some((extension) => normalized.endsWith(extension));
    }

    function hasAllowedMimeType(mimeType) {
        const normalized = String(mimeType || "").split(";", 1)[0].trim().toLowerCase();
        if (!normalized) {
            return true;
        }
        return allowedMimeTypes.includes(normalized);
    }

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
            const selectedFile = fileInput.files[0];
            const isSupportedFile = hasAllowedExtension(selectedFile.name) && hasAllowedMimeType(selectedFile.type);
            if (!isSupportedFile) {
                const invalidTypeMessage =
                    form.dataset.eventinstanceFileInvalidTypeMessage ||
                    "Unsupported file type. Only image and PDF are allowed.";
                window.alert(invalidTypeMessage);
                fileInput.value = "";
                return;
            }
            const unsavedGuard = window.DatacaptureUnsavedChangesGuard;
            if (
                unsavedGuard &&
                typeof unsavedGuard.confirmDiscardUnsavedChanges === "function" &&
                !unsavedGuard.confirmDiscardUnsavedChanges()
            ) {
                fileInput.value = "";
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
