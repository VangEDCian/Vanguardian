from apps.governance.application import GovernancePageLockService


class GovernancePageLockAdapter:
    def __init__(self, service=None):
        self.service = service or GovernancePageLockService()

    def lock_page_scope(self, **kwargs) -> int:
        return self.service.lock_page_scope(**kwargs)


def lock_page_scope(**kwargs) -> int:
    return GovernancePageLockAdapter().lock_page_scope(**kwargs)


__all__ = ["GovernancePageLockAdapter", "lock_page_scope"]
