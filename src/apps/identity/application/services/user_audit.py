from apps.audit.public import AuditContextAdapter
from apps.shared.constants import (
    AuditEventAction,
    AuditEventActionEnum,
    AuditEventObjectType,
    AuditEventObjectTypeEnum,
)


def serialize_identity_user_snapshot(user):
    role_key, role_label = _get_role_metadata(user)

    return {
        "username": user.get_username(),
        "display_name": getattr(user, "display_name", "") or "",
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone_number": getattr(user, "phone_number", "") or None,
        "role_key": role_key,
        "role_label": role_label,
        "is_active": user.is_active,
    }


class IdentityUserAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_created(self, *, user, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_CREATED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data={},
            after_data=serialize_identity_user_snapshot(user),
        )

    def record_updated(self, *, user, before_data, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_UPDATED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data=before_data,
            after_data=serialize_identity_user_snapshot(user),
        )

    def record_deleted(self, *, user_id, before_data, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_DELETED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            before_data=before_data,
            after_data={**before_data, "deleted": True, "is_active": False},
        )

    def record_restored(self, *, user, before_data, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_RESTORED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data=before_data,
            after_data=serialize_identity_user_snapshot(user),
        )

    def record_user_change_password(self, *, user, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.IDENTITY_USER_CHANGE_PASSWORD,
            object_type=AuditEventObjectTypeEnum.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data={},
            after_data={},
        )

    def record_admin_set_password(self, *, user, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.IDENTITY_USER_ADMIN_SET_PASSWORD,
            object_type=AuditEventObjectTypeEnum.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data={},
            after_data={},
        )

    def record_user_reset_password(self, *, user, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.IDENTITY_USER_RESET_PASSWORD,
            object_type=AuditEventObjectTypeEnum.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data={},
            after_data={},
        )


def _get_role_metadata(user):
    if user.is_superuser:
        return "administrator", "Administrator"
    if user.is_staff:
        return "staff", "Staff"
    return "user", "User"
