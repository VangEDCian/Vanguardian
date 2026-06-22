from dataclasses import dataclass

from django.db import DatabaseError, transaction

from apps.core.choices import EligibilityAssessmentStatusChoices, EligibilityResultChoices
from apps.study.infrastructure.repositories import (
    DjangoEligibilityAssessmentRepository,
    DjangoRandomizationRepository,
)


class RandomizationSlotAssignmentError(RuntimeError):
    """Raised when an available randomization slot cannot be assigned after retries."""


@dataclass(frozen=True)
class RandomizationSlotAssignment:
    slot_id: int
    scheme_id: int
    scheme_code: str
    arm_id: int
    arm_code: str
    arm_name: str
    sequence_no: int


class StudyRandomizationSlotAssignmentService:
    repository_class = DjangoRandomizationRepository
    eligibility_repository_class = DjangoEligibilityAssessmentRepository
    max_attempts = 10

    def __init__(self, repository=None, eligibility_repository=None):
        self.repository = repository or self.repository_class()
        self.eligibility_repository = eligibility_repository or self.eligibility_repository_class()

    def assign_random_available_slot(
        self,
        *,
        study_id: int,
        subject_id: int,
        event_instance_id: int,
        actor_user_id: int | None = None,
        scheme_id: int | None = None,
        stratum_code: str | None = None,
    ) -> RandomizationSlotAssignment | None:
        if self.repository.active_scheme_requires_screening_pass(study_id=study_id):
            assessment = self.eligibility_repository.get_current_assessment(
                study_id=study_id,
                subject_id=subject_id,
                assessment_type="SCREENING",
            )
            if not self._is_final_eligible_assessment(assessment):
                return None

        excluded_slot_ids: set[int] = set()
        for _attempt in range(self.max_attempts):
            now = self.repository.now()
            try:
                with transaction.atomic():
                    result = self.repository.assign_random_available_slot_for_subject(
                        study_id=study_id,
                        subject_id=subject_id,
                        event_instance_id=event_instance_id,
                        actor_user_id=actor_user_id,
                        now=now,
                        scheme_id=scheme_id,
                        stratum_code=stratum_code,
                        excluded_slot_ids=tuple(excluded_slot_ids),
                    )
            except DatabaseError:
                continue

            if result is None:
                return None
            slot_id = int(result["slot_id"])
            if not result.get("assigned"):
                excluded_slot_ids.add(slot_id)
                continue
            return RandomizationSlotAssignment(
                slot_id=slot_id,
                scheme_id=int(result["scheme_id"]),
                scheme_code=str(result["scheme_code"] or ""),
                arm_id=int(result["arm_id"]),
                arm_code=str(result["arm_code"] or ""),
                arm_name=str(result["arm_name"] or ""),
                sequence_no=int(result["sequence_no"]),
            )

        raise RandomizationSlotAssignmentError("Unable to assign an available randomization slot after retries.")

    @staticmethod
    def _is_final_eligible_assessment(assessment) -> bool:
        return bool(
            assessment
            and assessment.is_current
            and assessment.assessment_status == EligibilityAssessmentStatusChoices.FINAL
            and assessment.result == EligibilityResultChoices.ELIGIBLE
        )


class StudyRandomizationTransitionFactService:
    repository_class = DjangoRandomizationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def build_facts(self, *, study_id: int) -> dict[str, object]:
        facts = {
            "randomization.available_slot_count": self.repository.count_available_slots_for_active_schemes(
                study_id=study_id,
            ),
        }
        active_scheme_status = self.repository.get_active_scheme_status(study_id=study_id)
        if active_scheme_status:
            facts["randomization.scheme.status"] = active_scheme_status
        return facts


__all__ = [
    "RandomizationSlotAssignment",
    "RandomizationSlotAssignmentError",
    "StudyRandomizationSlotAssignmentService",
    "StudyRandomizationTransitionFactService",
]
