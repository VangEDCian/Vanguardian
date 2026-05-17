from django.contrib.auth import get_user_model


def get_username_display_for_user_id(user_id: int | None) -> str:
    if user_id is None:
        return "—"
    user_model = get_user_model()
    username = (
        user_model.objects.filter(pk=user_id, deleted=False).values_list("username", flat=True).first()
    )
    return username or str(user_id)


__all__ = ["get_username_display_for_user_id"]
