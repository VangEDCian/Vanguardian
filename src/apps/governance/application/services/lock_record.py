from apps.governance.infrastructure.repositories import DjangoGovernanceLockWriteRepository


class GovernancePageLockService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoGovernanceLockWriteRepository()

    def lock_page_scope(self, **kwargs) -> int:
        return self.repository.lock_page_scope(**kwargs)


__all__ = ["GovernancePageLockService"]
