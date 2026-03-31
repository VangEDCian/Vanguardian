from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class IdentifierBackend(ModelBackend):
    """
    Allow login with username, email, or phone number while keeping Django's
    default password and active-user checks.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)

        if username is None or password is None:
            return None

        identifier = username.strip()
        if not identifier:
            return None

        user = self._get_user_by_identifier(identifier)
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _get_user_by_identifier(self, identifier):
        user_model = get_user_model()
        manager = user_model._default_manager
        lookups = (
            {user_model.USERNAME_FIELD: identifier},
            {"email__iexact": identifier},
            {"phone_number": identifier},
        )

        for lookup in lookups:
            try:
                return manager.get(**lookup)
            except user_model.DoesNotExist:
                continue
            except user_model.MultipleObjectsReturned:
                return None

        return None
