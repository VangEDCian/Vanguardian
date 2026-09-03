from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.identity.public import user_has_any_active_role_ids
from apps.study.domain.crf_page_lifecycle import CrfPageLifecycleStep
from apps.study.public import get_crf_page_lifecycle_action_state


class DataCapturePageLifecyclePolicyService:
    def __init__(self, action_state_reader=None, role_checker=None):
        self.action_state_reader = action_state_reader or get_crf_page_lifecycle_action_state
        self.role_checker = role_checker or user_has_any_active_role_ids

    def require_step(
        self,
        *,
        snapshot,
        step_code: str,
        actor_user_id: int | None,
    ):
        state = self.action_state_reader(
            study_id=int(snapshot.study_id),
            page_status=str(snapshot.status or ""),
        )
        if state.next_step_code != step_code or state.next_step is None:
            expected = state.next_step_code or "no further step"
            raise DataCaptureValidationError(
                f"CRF Page lifecycle requires {expected} before {step_code}."
            )
        if actor_user_id is None:
            raise DataCaptureValidationError("Authenticated user is required.")
        allowed_role_ids = tuple(state.next_step.allowed_role_ids)
        if allowed_role_ids and not self.role_checker(
            user_id=int(actor_user_id),
            study_id=int(snapshot.study_id),
            site_id=getattr(snapshot, "site_id", None),
            role_ids=allowed_role_ids,
        ):
            raise DataCaptureValidationError(
                f"Your active Study/Site role is not allowed to perform {step_code}."
            )
        return state.next_step

    def can_perform(
        self,
        *,
        study_id: int,
        page_status: str,
        step_code: str,
        actor_user_id: int,
        site_id: int | None,
    ) -> bool:
        state = self.action_state_reader(study_id=study_id, page_status=page_status)
        if state.next_step_code != step_code or state.next_step is None:
            return False
        role_ids = tuple(state.next_step.allowed_role_ids)
        return not role_ids or self.role_checker(
            user_id=actor_user_id,
            study_id=study_id,
            site_id=site_id,
            role_ids=role_ids,
        )


__all__ = ["CrfPageLifecycleStep", "DataCapturePageLifecyclePolicyService"]
