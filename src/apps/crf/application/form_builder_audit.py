from apps.audit.public import AuditContextAdapter


class CrfFormBuilderAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_field_created(
        self,
        *,
        study_id,
        form_id,
        field_template_id,
        after_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.field_created",
            object_type="crf.field_template",
            object_id=str(field_template_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={},
            after_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **after_data,
            },
        )

    def record_field_updated(
        self,
        *,
        study_id,
        form_id,
        field_template_id,
        before_data,
        after_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.field_updated",
            object_type="crf.field_template",
            object_id=str(field_template_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **before_data,
            },
            after_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **after_data,
            },
        )

    def record_field_deleted(
        self,
        *,
        study_id,
        form_id,
        field_template_id,
        before_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.field_deleted",
            object_type="crf.field_template",
            object_id=str(field_template_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **before_data,
            },
            after_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                "deleted": True,
            },
        )

    def record_section_template_saved(
        self,
        *,
        study_id,
        form_id,
        section_object_id,
        after_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.section_saved",
            object_type="crf.section_template",
            object_id=str(section_object_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={},
            after_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **after_data,
            },
        )

    def record_section_template_deleted(
        self,
        *,
        study_id,
        form_id,
        section_object_id,
        before_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.section_deleted",
            object_type="crf.section_template",
            object_id=str(section_object_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                **before_data,
            },
            after_data={
                "study_id": str(study_id),
                "form_id": str(form_id),
                "deleted": True,
            },
        )

    def record_template_saved(
        self,
        *,
        study_id,
        template_id,
        after_data,
        actor_user_id=None,
        ip_address=None,
        user_agent=None,
    ):
        self.audit_context_adapter.record_event(
            action="crf.form_builder.template_saved",
            object_type="crf.crf_template",
            object_id=str(template_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={},
            after_data={
                "study_id": str(study_id),
                **after_data,
            },
        )
