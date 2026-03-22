from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Identity user stays compatible with django-auth's runtime semantics while
    reserving ownership of the concrete user table for the DB-first schema.
    """

    class Meta(AbstractUser.Meta):
        db_table = "identity_user"
        managed = False
        default_permissions = ()
        permissions = ()
        verbose_name = "user"
        verbose_name_plural = "users"
