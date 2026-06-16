from django.contrib.auth import get_user_model


def get_user_display_map(user_ids) -> dict[int, str]:
    normalized_ids = tuple(
        sorted(
            {
                int(user_id)
                for user_id in user_ids or ()
                if user_id not in (None, "")
            }
        )
    )
    if not normalized_ids:
        return {}

    user_model = get_user_model()
    rows = user_model.objects.filter(pk__in=normalized_ids, deleted=False).values(
        "id",
        "display_name",
        "first_name",
        "last_name",
        "username",
    )
    return {int(row["id"]): _display_name(row) for row in rows}


def _display_name(row: dict) -> str:
    explicit_display_name = str(row.get("display_name") or "").strip()
    full_name = " ".join(
        part
        for part in (
            str(row.get("first_name") or "").strip(),
            str(row.get("last_name") or "").strip(),
        )
        if part
    )
    username = str(row.get("username") or "").strip()
    return explicit_display_name or full_name or username


__all__ = ["get_user_display_map"]
