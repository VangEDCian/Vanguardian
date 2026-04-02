from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventAction, AuditEventObjectType


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
        "permission_groups": [group.name for group in user.groups.order_by("name")],
    }


class IdentityUserAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_created(self, *, request, user):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_CREATED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            request=request,
            user_id=user.pk,
            before_data={},
            after_data=serialize_identity_user_snapshot(user),
        )

    def record_updated(self, *, request, user, before_data):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_USER_UPDATED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            request=request,
            user_id=user.pk,
            before_data=before_data,
            after_data=serialize_identity_user_snapshot(user),
        )


def _get_role_metadata(user):
    if user.is_superuser:
        return "administrator", "Administrator"
    if user.is_staff:
        return "staff", "Staff"
    return "user", "User"
