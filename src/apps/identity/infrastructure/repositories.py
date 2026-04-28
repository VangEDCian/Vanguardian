from django.contrib.auth.models import Group

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.models import User
from apps.shared.constants import AuditEventAction, AuditEventObjectType


class DjangoIdentityUserRepository:
    def build_user(self, **values):
        return User(**values)

    def save_user(self, user):
        user.save()
        return user

    def get_user_with_groups(self, *, user_id):
        return User.objects.prefetch_related("groups").filter(pk=user_id).first()

    def list_users(self, *, order_by=()):
        return User.objects.filter(deleted=False).order_by(*order_by)

    def get_user_for_detail(self, *, user_id, include_deleted=False):
        queryset = User.objects.prefetch_related("groups").filter(pk=user_id)
        if not include_deleted:
            queryset = queryset.filter(deleted=False)
        return queryset.first()

    def reload_user_with_groups(self, user):
        return User.objects.prefetch_related("groups").get(pk=user.pk)

    def username_exists(self, *, username, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(username__iexact=username)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def email_exists(self, *, email, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(email__iexact=email)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def phone_number_exists(self, *, phone_number, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(phone_number=phone_number)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def list_groups_by_ids(self, group_ids):
        return Group.objects.filter(pk__in=group_ids).order_by("name")

    def list_groups_by_names(self, group_names):
        return Group.objects.filter(name__in=group_names).order_by("name")

    def list_groups(self):
        return Group.objects.order_by("name")

    def get_latest_user_deleted_event(self, *, user_id):
        return (
            AuditEvent.objects.filter(
                deleted=False,
                action=AuditEventAction.IDENTITY_USER_DELETED,
                object_type=AuditEventObjectType.IDENTITY_USER,
                object_id=str(user_id),
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def _apply_user_filters(queryset, *, exclude_user_id, deleted):
        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)
        if exclude_user_id is not None:
            queryset = queryset.exclude(pk=exclude_user_id)
        return queryset
