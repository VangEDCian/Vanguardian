from dataclasses import dataclass

from apps.study.domain.crf_page_lifecycle import (
    CrfPageLifecycleConfigurationError,
    CrfPageLifecycleStep,
    CrfPageLifecycleStepPolicy,
    validate_crf_page_lifecycle_steps,
)
from apps.study.infrastructure.repositories import DjangoStudyCrfPageLifecycleRepository

LEGACY_CRF_PAGE_LIFECYCLE = (
    CrfPageLifecycleStepPolicy(CrfPageLifecycleStep.VERIFY, 1, ()),
    CrfPageLifecycleStepPolicy(CrfPageLifecycleStep.FINALIZE, 2, ()),
    CrfPageLifecycleStepPolicy(CrfPageLifecycleStep.LOCK, 3, ()),
)


def _default_role_option_reader(*, study_id: int):
    from apps.identity.public import list_role_options_for_study

    return list_role_options_for_study(study_id=study_id)


@dataclass(frozen=True)
class CrfPageLifecycleActionState:
    next_step_code: str | None
    next_step: CrfPageLifecycleStepPolicy | None


class StudyCrfPageLifecycleService:
    def __init__(self, repository=None, role_option_reader=None):
        self.repository = repository or DjangoStudyCrfPageLifecycleRepository()
        self.role_option_reader = role_option_reader or _default_role_option_reader

    def list_steps(self, *, study_id: int) -> tuple[CrfPageLifecycleStepPolicy, ...]:
        rows = self.repository.list_steps(study_id=study_id)
        if not rows and not self.repository.is_configured(study_id=study_id):
            return LEGACY_CRF_PAGE_LIFECYCLE
        return tuple(
            CrfPageLifecycleStepPolicy(
                step_code=str(row.step_code),
                display_order=int(row.display_order),
                allowed_role_ids=tuple(int(role_id) for role_id in (row.allowed_role_ids or [])),
            )
            for row in rows
        )

    def build_configuration(self, *, study_id: int) -> dict:
        is_configured = self.repository.is_configured(study_id=study_id)
        steps = self.list_steps(study_id=study_id)
        role_options = self.role_option_reader(study_id=study_id)
        configured_by_code = {item.step_code: item for item in steps}
        return {
            "uses_legacy_default": not is_configured,
            "roles": role_options,
            "steps": [
                {
                    "code": step_code,
                    "label": self._label(step_code),
                    "enabled": step_code in configured_by_code,
                    "display_order": (
                        configured_by_code[step_code].display_order
                        if step_code in configured_by_code
                        else CrfPageLifecycleStep.ALL.index(step_code) + 1
                    ),
                    "allowed_role_ids": (
                        configured_by_code[step_code].allowed_role_ids
                        if step_code in configured_by_code
                        else ()
                    ),
                    "required_permission_code": CrfPageLifecycleStep.PERMISSION_BY_STEP[step_code],
                }
                for step_code in CrfPageLifecycleStep.ALL
            ],
        }

    def save(self, *, study_id: int, raw_steps: list[dict], actor_user_id: int | None):
        role_options = self.role_option_reader(study_id=study_id)
        roles_by_id = {int(role["id"]): role for role in role_options}
        policies = []
        for raw_step in raw_steps:
            if not raw_step.get("enabled"):
                continue
            step_code = str(raw_step.get("step_code") or "").strip().upper()
            role_ids = tuple(dict.fromkeys(int(role_id) for role_id in raw_step.get("role_ids", ())))
            permission_code = CrfPageLifecycleStep.PERMISSION_BY_STEP.get(step_code)
            if permission_code is None:
                raise CrfPageLifecycleConfigurationError(f"Unsupported CRF Page lifecycle step: {step_code}.")
            for role_id in role_ids:
                role = roles_by_id.get(role_id)
                if role is None:
                    raise CrfPageLifecycleConfigurationError("A selected role no longer belongs to this Study.")
                if permission_code not in role["permission_codes"]:
                    raise CrfPageLifecycleConfigurationError(
                        f"Role {role['name']} does not have permission {permission_code}."
                    )
            policies.append(
                CrfPageLifecycleStepPolicy(
                    step_code=step_code,
                    display_order=int(raw_step.get("display_order") or 0),
                    allowed_role_ids=role_ids,
                )
            )
        ordered = validate_crf_page_lifecycle_steps(tuple(policies))
        self.repository.replace_steps(
            study_id=study_id,
            steps=ordered,
            actor_user_id=actor_user_id,
        )
        return ordered

    def action_state(self, *, study_id: int, page_status: str) -> CrfPageLifecycleActionState:
        steps = self.list_steps(study_id=study_id)
        normalized_status = str(page_status or "").strip().lower()
        if normalized_status == "locked":
            return CrfPageLifecycleActionState(None, None)
        status_codes = {
            step.target_status: index
            for index, step in enumerate(steps)
        }
        completed_through = status_codes.get(normalized_status, -1)
        if normalized_status in {"under_review", "correction_required"}:
            completed_through = -1
        next_index = completed_through + 1
        if next_index >= len(steps):
            return CrfPageLifecycleActionState(None, None)
        next_step = steps[next_index]
        return CrfPageLifecycleActionState(next_step.step_code, next_step)

    @staticmethod
    def _label(step_code: str) -> str:
        return {
            CrfPageLifecycleStep.VERIFY: "Verify Page",
            CrfPageLifecycleStep.CERTIFY: "Certify Page",
            CrfPageLifecycleStep.FINALIZE: "Finalize Page Data",
            CrfPageLifecycleStep.LOCK: "Lock Page",
        }[step_code]


__all__ = [
    "CrfPageLifecycleActionState",
    "LEGACY_CRF_PAGE_LIFECYCLE",
    "StudyCrfPageLifecycleService",
]
