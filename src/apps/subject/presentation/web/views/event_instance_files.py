import hashlib
import mimetypes
import re
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.infrastructure.repositories import DjangoSubjectEventInstanceFileRepository
from apps.subject.models import Subject
from apps.subject.presentation.web.forms import (
    ALLOWED_EVENT_INSTANCE_IMAGE_EXTENSIONS,
    ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES,
    ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS,
    ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES,
    SubjectEventInstanceFileImportForm,
    detect_event_instance_upload_kind_from_header,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectEventInstanceFileViewMixin:
    repository_class = DjangoSubjectEventInstanceFileRepository
    private_upload_root = Path(settings.BASE_DIR) / "protected_uploads"
    legacy_upload_root = Path(settings.BASE_DIR) / "staticfiles" / "uploads"

    def get_repository(self):
        return self.repository_class()

    def get_subject(self):
        return Subject.objects.filter(
            pk=self.kwargs["subject_id"],
            study_id=self.get_study_id(),
            deleted=False,
        ).select_related("site").first()

    def get_event_instance(self):
        return self.get_repository().get_event_instance(
            study_id=self.get_study_id(),
            subject_id=self.kwargs["subject_id"],
            event_instance_id=self.kwargs["event_instance_id"],
        )

    def build_subject_detail_url(self):
        subject = self.get_subject()
        if subject is None:
            raise Http404

        event_instance = self.get_event_instance()
        if event_instance is None:
            raise Http404

        detail_url = reverse(
            "subject:subject_detail",
            kwargs={"study_id": self.get_study_id(), "subject_id": subject.pk},
        )
        query_parts = [f"event={event_instance.pk}"]

        focused_form_id = (self.request.GET.get("form") or self.request.POST.get("form") or "").strip()
        if focused_form_id:
            query_parts.append(f"form={focused_form_id}")

        view_mode = (self.request.GET.get("view") or self.request.POST.get("view") or "").strip().lower()
        if view_mode:
            query_parts.append(f"view={view_mode}")

        return f"{detail_url}?{'&'.join(query_parts)}"

    @staticmethod
    def _sanitize_file_name(file_name):
        normalized = Path(file_name or "").name.strip()
        if not normalized:
            return "file"
        return re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)

    @staticmethod
    def _resolve_file_kind(file_name, mime_type):
        extension = Path(file_name or "").suffix.lower().strip()
        normalized_mime_type = (mime_type or "").split(";", 1)[0].lower().strip()
        if extension in ALLOWED_EVENT_INSTANCE_IMAGE_EXTENSIONS or normalized_mime_type in ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES:
            return "image"
        if extension in ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS or normalized_mime_type in ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES:
            return "pdf"
        return "unsupported"

    def _resolve_storage_path(self, storage_relative_path):
        relative_path = Path(storage_relative_path or "")
        if relative_path.is_absolute():
            raise Http404

        if relative_path.parts and relative_path.parts[0] == "uploads":
            candidate = (self.legacy_upload_root / Path(*relative_path.parts[1:])).resolve()
            allowed_root = self.legacy_upload_root.resolve()
        else:
            candidate = (Path(settings.BASE_DIR) / relative_path).resolve()
            allowed_root = self.private_upload_root.resolve()

        try:
            candidate.relative_to(allowed_root)
        except ValueError as exc:
            raise Http404 from exc
        return candidate


class SubjectEventInstanceFileImportView(
    SubjectEventInstanceFileViewMixin,
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.update_subject"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        subject = self.get_subject()
        if subject is None:
            raise Http404

        event_instance = self.get_event_instance()
        if event_instance is None:
            raise Http404

        form = SubjectEventInstanceFileImportForm(request.POST, request.FILES)
        if not form.is_valid():
            errors = form.errors.get("import_file")
            error_message = errors[0] if errors else _("Invalid file upload.")
            messages.error(request, error_message)
            return redirect(self.build_subject_detail_url())

        uploaded_file = form.cleaned_data["import_file"]
        now = timezone.now()

        safe_original_name = self._sanitize_file_name(uploaded_file.name)
        stored_file_name = f"{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}_{safe_original_name}"
        relative_dir = (
            Path("protected_uploads")
            / "study_eventinstance_files"
            / str(self.get_study_id())
            / str(subject.pk)
            / str(event_instance.pk)
        )
        storage_relative_path = (relative_dir / stored_file_name).as_posix()
        target_dir = Path(settings.BASE_DIR) / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / stored_file_name

        checksum = hashlib.sha256()
        with target_path.open("wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                checksum.update(chunk)

        self.get_repository().create_file(
            study_id=self.get_study_id(),
            subject_id=subject.pk,
            site_id=subject.site_id,
            event_instance_id=event_instance.pk,
            original_file_name=safe_original_name,
            stored_file_name=stored_file_name,
            storage_relative_path=storage_relative_path,
            mime_type=getattr(uploaded_file, "content_type", "") or None,
            file_size_bytes=uploaded_file.size,
            checksum_sha256=checksum.hexdigest(),
            actor_user_id=request.user.pk,
            now=now,
        )

        return redirect(self.build_subject_detail_url())


class SubjectEventInstanceFilePreviewView(
    SubjectEventInstanceFileViewMixin,
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    TemplateView,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    template_name = "subject/subject_eventinstance_files_preview2.html"
    layout_nav_key = "SUBJECTS"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_subject()
        if subject is None:
            raise Http404

        event_instance = self.get_event_instance()
        if event_instance is None:
            raise Http404

        file_records = list(self.get_repository().list_files(event_instance_id=event_instance.pk))
        selected_file_id_raw = (self.request.GET.get("file") or "").strip()
        selected_file_id = int(selected_file_id_raw) if selected_file_id_raw.isdigit() else None

        files = []
        selected_file = None
        for file_obj in file_records:
            file_item = {
                "id": file_obj.pk,
                "original_file_name": file_obj.original_file_name,
                "file_size_bytes": file_obj.file_size_bytes,
                "created_at": file_obj.created_at,
                "preview_url": reverse(
                    "subject:subject_eventinstance_file_content",
                    kwargs={
                        "study_id": self.get_study_id(),
                        "subject_id": subject.pk,
                        "event_instance_id": event_instance.pk,
                        "file_id": file_obj.pk,
                    },
                ),
                "kind": self._resolve_file_kind(file_obj.original_file_name, file_obj.mime_type),
            }
            files.append(file_item)
            if selected_file_id is not None and file_obj.pk == selected_file_id:
                selected_file = file_item

        if selected_file is None and files:
            selected_file = files[0]

        context["subject_obj"] = subject
        context["event_instance"] = event_instance
        context["files"] = files
        context["selected_file"] = selected_file
        context["back_url"] = self.build_subject_detail_url()
        return context


class SubjectEventInstanceFileContentView(
    SubjectEventInstanceFileViewMixin,
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def get(self, request, *args, **kwargs):
        subject = self.get_subject()
        if subject is None:
            raise Http404

        event_instance = self.get_event_instance()
        if event_instance is None:
            raise Http404

        file_id_raw = str(kwargs.get("file_id", "")).strip()
        if not file_id_raw.isdigit():
            raise Http404
        file_obj = self.get_repository().get_file(
            event_instance_id=event_instance.pk,
            file_id=int(file_id_raw),
        )
        if file_obj is None:
            raise Http404

        file_path = self._resolve_storage_path(file_obj.storage_relative_path)
        if not file_path.exists() or not file_path.is_file():
            raise Http404

        with file_path.open("rb") as source:
            file_header = source.read(16)
        detected_kind = detect_event_instance_upload_kind_from_header(file_header)
        expected_kind = self._resolve_file_kind(file_obj.original_file_name, file_obj.mime_type)
        if detected_kind is None or detected_kind != expected_kind:
            raise Http404

        guessed_content_type, _ = mimetypes.guess_type(file_obj.original_file_name or "")
        content_type = file_obj.mime_type or guessed_content_type or "application/octet-stream"
        response = FileResponse(file_path.open("rb"), content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = content_disposition_header(
            as_attachment=False,
            filename=self._sanitize_file_name(file_obj.original_file_name),
        )
        return response
