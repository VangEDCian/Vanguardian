from dataclasses import dataclass

from apps.study.application.exceptions import (
    RandomizationArmNotFoundError,
    RandomizationDeleteBlockedError,
    RandomizationSchemeNotFoundError,
)


@dataclass(frozen=True)
class DeleteRandomizationSchemeCommand:
    actor_user_id: int
    study_id: int
    scheme_id: int


@dataclass(frozen=True)
class DeleteRandomizationArmCommand:
    actor_user_id: int
    study_id: int
    arm_id: int


@dataclass(frozen=True)
class DeleteRandomizationSchemeResult:
    deleted_slot_count: int
    deleted_arm_count: int


@dataclass(frozen=True)
class DeleteRandomizationArmResult:
    deleted_slot_count: int

__all__ = [
    "DeleteRandomizationArmCommand",
    "DeleteRandomizationArmResult",
    "DeleteRandomizationSchemeCommand",
    "DeleteRandomizationSchemeResult",
    "RandomizationArmNotFoundError",
    "RandomizationDeleteBlockedError",
    "RandomizationSchemeNotFoundError",
]
