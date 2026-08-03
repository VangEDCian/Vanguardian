from apps.identity.infrastructure.role_scope import DjangoIdentityRoleScopeRepository


class IdentityRoleScopeService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoIdentityRoleScopeRepository()

    def list_study_role_options(self, *, study_id: int) -> list[dict]:
        return self.repository.list_study_role_options(study_id=study_id)

    def user_has_any_active_role_ids(self, **kwargs) -> bool:
        return self.repository.user_has_any_active_role_ids(**kwargs)


__all__ = ["IdentityRoleScopeService"]
