class RandomizationImportController {
    constructor() {
        this.previewMaxRows = 100;
        this.dom = this.buildDom();
        this.state = {
            activeImport: null,
        };
        this.msg = this.buildMessages();
    }

    buildDom() {
        return {
            toggleButtons: document.querySelectorAll("[data-import-toggle-target]"),
            importInputs: document.querySelectorAll("[data-randomization-import-input]"),
            modal: document.getElementById("scheme-import-modal"),
            modalTitle: document.getElementById("scheme-import-modal-title"),
            modalMeta: document.getElementById("scheme-import-modal-meta"),
            modalStatus: document.getElementById("scheme-import-modal-status"),
            previewTable: document.getElementById("scheme-import-preview-table"),
            confirmImportBtn: document.getElementById("scheme-import-confirm"),
            closeModalButtons: document.querySelectorAll("[data-scheme-modal-close]"),
            i18n: document.getElementById("scheme-import-i18n"),
        };
    }

    buildMessages() {
        const i18n = this.dom.i18n;

        return {
            noFile: i18n?.dataset.noFile || "Please select a file first.",
            previewTruncated: i18n?.dataset.previewTruncated || "Preview truncated to %(max)s rows (total rows: %(total)s).",
            importing: i18n?.dataset.importing || "Importing...",
            importSuccess: i18n?.dataset.importSuccess || "Import completed successfully.",
            importError: i18n?.dataset.importError || "Import failed. Please try again.",
            previewError: i18n?.dataset.previewError || "Could not preview the selected file.",
            uploadingPreview: i18n?.dataset.uploadingPreview || "Uploading file for preview...",
            networkError: i18n?.dataset.networkError || "The request could not be completed. Please try again.",
            invalidCells: i18n?.dataset.invalidCells || "Some cells contain invalid values. Please review the details below.",
            validationErrorTitle: i18n?.dataset.validationErrorTitle || "Import validation issues",
            unexpectedError: i18n?.dataset.unexpectedError || "An unexpected error occurred.",
        };
    }

    init() {
        this.bindPanelToggles();
        this.bindModal();
        this.bindImportInputs();
        this.bindConfirmImport();
    }

    bindPanelToggles() {
        this.dom.toggleButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const targetId = button.getAttribute("data-import-toggle-target");
                if (!targetId) {
                    return;
                }

                const targetPanel = document.getElementById(targetId);
                if (!targetPanel) {
                    return;
                }

                const isOpen = !targetPanel.hidden;
                targetPanel.hidden = isOpen;
                button.setAttribute("aria-expanded", String(!isOpen));
            });
        });
    }

    bindModal() {
        this.dom.closeModalButtons.forEach((button) => {
            button.addEventListener("click", () => this.closeModal());
        });

        if (!this.dom.modal) {
            return;
        }

        this.dom.modal.addEventListener("click", (event) => {
            if (event.target === this.dom.modal) {
                this.closeModal();
            }
        });
    }

    bindImportInputs() {
        this.dom.importInputs.forEach((input) => {
            input.addEventListener("change", async (event) => {
                const file = event.target.files?.[0];
                await this.handleImportFile(input, file);
            });
        });
    }

    bindConfirmImport() {
        if (!this.dom.confirmImportBtn) {
            return;
        }

        this.dom.confirmImportBtn.addEventListener("click", async () => {
            await this.submitActiveImport();
        });
    }

    async handleImportFile(input, file) {
        if (!file) {
            this.setStatus(this.msg.noFile, "error");
            return;
        }

        const previewUrl = input.dataset.previewUrl || "";
        const commitUrl = input.dataset.commitUrl || "";
        const title = input.dataset.previewTitle || this.msg.previewError;

        this.state.activeImport = {
            file,
            previewUrl,
            commitUrl,
            title,
        };

        this.setModalTitle(title);
        this.setImportButtonDisabled(true);
        this.clearPreview();
        this.setStatus(this.msg.uploadingPreview, "info");
        this.openModal();

        const response = await this.postFile(previewUrl, file);
        if (!response.ok) {
            this.renderRequestError(response, { fallbackDetail: this.msg.previewError });
            return;
        }

        this.renderPreview(response.data);
    }

    async submitActiveImport() {
        if (!this.state.activeImport?.file) {
            this.setStatus(this.msg.noFile, "error");
            return;
        }

        if (!this.state.activeImport.commitUrl) {
            this.setStatus(this.msg.importError, "error");
            return;
        }

        this.setImportButtonDisabled(true);
        this.setStatus(this.msg.importing, "info");

        const response = await this.postFile(
            this.state.activeImport.commitUrl,
            this.state.activeImport.file,
        );
        if (!response.ok) {
            this.renderRequestError(response, { fallbackDetail: this.msg.importError });
            return;
        }

        this.setStatus(response.data.detail || this.msg.importSuccess, "success");
        if (response.data.redirect_url) {
            window.location.assign(response.data.redirect_url);
            return;
        }

        window.location.reload();
    }

    async postFile(url, file) {
        if (!url) {
            return {
                ok: false,
                data: { detail: this.msg.unexpectedError },
            };
        }

        const payload = new FormData();
        payload.append("import_file", file);

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": this.getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
                body: payload,
            });
            const data = await response.json().catch(() => ({}));
            return { ok: response.ok, status: response.status, data };
        } catch {
            return {
                ok: false,
                data: { detail: this.msg.networkError },
            };
        }
    }

    renderRequestError(response, { fallbackDetail }) {
        const detail = response.data?.detail || this.extractFormError(response.data?.errors) || fallbackDetail;
        const issues = response.data?.issues || [];

        if (issues.length) {
            this.renderIssues(issues, detail || this.msg.invalidCells);
        } else {
            this.setStatus(detail || this.msg.unexpectedError, "error");
        }
        this.setImportButtonDisabled(true);
    }

    extractFormError(errors) {
        if (!errors) {
            return "";
        }

        const fieldErrors = Object.values(errors).flat();
        const firstError = fieldErrors[0]?.[0];
        return firstError?.message || "";
    }

    renderPreview(payload) {
        this.setModalTitle(payload.title || this.state.activeImport?.title || "Import Preview");
        this.renderTable(payload.headers || [], payload.rows || []);

        if ((payload.issues || []).length) {
            this.renderIssues(payload.issues, this.msg.validationErrorTitle);
        } else {
            this.clearStatus();
        }

        if ((payload.total_rows || 0) > (payload.rows || []).length) {
            this.dom.modalMeta.textContent = this.msg.previewTruncated
                .replace("%(max)s", String(this.previewMaxRows))
                .replace("%(total)s", String(payload.total_rows || 0));
        } else {
            this.dom.modalMeta.textContent = "";
        }

        this.setImportButtonDisabled(!payload.can_commit);
    }

    renderTable(headers, rows) {
        if (!this.dom.previewTable) {
            return;
        }

        const headHtml = headers.map((header) => `<th>${this.escapeHtml(header)}</th>`).join("");
        const bodyHtml = rows
            .map((row) => `<tr>${row.map((value) => `<td>${this.escapeHtml(this.formatCellValue(value))}</td>`).join("")}</tr>`)
            .join("");

        this.dom.previewTable.innerHTML = `<thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody>`;
    }

    renderIssues(issues, title) {
        const itemsHtml = issues
            .map((issue) => `<li>${this.escapeHtml(issue.detail || this.msg.unexpectedError)}</li>`)
            .join("");

        const html = `
            <span class="randomization-modal__status-title">${this.escapeHtml(title)}</span>
            <ul class="randomization-modal__status-list">${itemsHtml}</ul>
        `;
        this.setStatus(html, "error", true);
    }

    clearPreview() {
        if (this.dom.previewTable) {
            this.dom.previewTable.innerHTML = "";
        }
        if (this.dom.modalMeta) {
            this.dom.modalMeta.textContent = "";
        }
    }

    setImportButtonDisabled(isDisabled) {
        if (!this.dom.confirmImportBtn) {
            return;
        }

        this.dom.confirmImportBtn.disabled = isDisabled;
    }

    setStatus(content, type = "", allowHtml = false) {
        if (!this.dom.modalStatus) {
            return;
        }

        if (allowHtml) {
            this.dom.modalStatus.innerHTML = content;
        } else {
            this.dom.modalStatus.textContent = content;
        }

        this.dom.modalStatus.className = "randomization-modal__status";
        if (type) {
            this.dom.modalStatus.classList.add(`randomization-modal__status--${type}`);
        }
    }

    clearStatus() {
        this.setStatus("");
    }

    setModalTitle(title) {
        if (!this.dom.modalTitle) {
            return;
        }

        this.dom.modalTitle.textContent = title;
    }

    openModal() {
        if (!this.dom.modal) {
            return;
        }

        this.dom.modal.hidden = false;
        this.dom.modal.setAttribute("aria-hidden", "false");
    }

    closeModal() {
        if (!this.dom.modal) {
            return;
        }

        this.dom.modal.hidden = true;
        this.dom.modal.setAttribute("aria-hidden", "true");
    }

    getCsrfToken() {
        const cookie = document.cookie
            .split(";")
            .map((part) => part.trim())
            .find((part) => part.startsWith("csrftoken="));

        if (!cookie) {
            return "";
        }

        return decodeURIComponent(cookie.split("=")[1]);
    }

    formatCellValue(value) {
        if (value === null || value === undefined) {
            return "";
        }
        if (typeof value === "boolean") {
            return value ? "True" : "False";
        }
        return String(value);
    }

    escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new RandomizationImportController().init();
});
