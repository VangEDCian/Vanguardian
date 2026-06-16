from apps.identity.infrastructure.auth.authorization import AuthorizationService, ResourceContext


def can_perform(*, user_id: int, permission_code: str, resource_context: ResourceContext):
    return AuthorizationService().can_perform(
        user_id=user_id,
        permission_code=permission_code,
        resource_context=resource_context,
    )


__all__ = ["ResourceContext", "can_perform"]
