from dataclasses import dataclass


class CrfPageLifecycleStep:
    VERIFY = "VERIFY"
    # Kept as a legacy code so old audit/status data remains readable. New
    # Study configuration uses Visit-level CERTIFICATION attestation instead of
    # treating Data Assurance certification as a Page status.
    CERTIFY = "CERTIFY"
    FINALIZE = "FINALIZE"
    LOCK = "LOCK"

    ALL = (VERIFY, FINALIZE, LOCK)
    PERMISSION_BY_STEP = {
        VERIFY: "SDV.MARK",
        FINALIZE: "SDV.MARK",
        LOCK: "DATA.LOCK",
    }
    STATUS_BY_STEP = {
        VERIFY: "verified",
        FINALIZE: "finalized",
        LOCK: "locked",
    }


@dataclass(frozen=True)
class CrfPageLifecycleStepPolicy:
    step_code: str
    display_order: int
    allowed_role_ids: tuple[int, ...]

    @property
    def required_permission_code(self) -> str:
        return CrfPageLifecycleStep.PERMISSION_BY_STEP[self.step_code]

    @property
    def target_status(self) -> str:
        return CrfPageLifecycleStep.STATUS_BY_STEP[self.step_code]


class CrfPageLifecycleConfigurationError(ValueError):
    pass


def validate_crf_page_lifecycle_steps(
    steps: tuple[CrfPageLifecycleStepPolicy, ...],
) -> tuple[CrfPageLifecycleStepPolicy, ...]:
    ordered = tuple(sorted(steps, key=lambda item: (item.display_order, item.step_code)))
    codes = [item.step_code for item in ordered]
    if len(codes) != len(set(codes)):
        raise CrfPageLifecycleConfigurationError("Each CRF Page lifecycle step can only be selected once.")
    unknown = [code for code in codes if code not in CrfPageLifecycleStep.ALL]
    if unknown:
        raise CrfPageLifecycleConfigurationError(f"Unsupported CRF Page lifecycle step: {unknown[0]}.")
    if CrfPageLifecycleStep.VERIFY in codes and codes[0] != CrfPageLifecycleStep.VERIFY:
        raise CrfPageLifecycleConfigurationError("Verify must be the first enabled step.")
    if CrfPageLifecycleStep.LOCK in codes and codes[-1] != CrfPageLifecycleStep.LOCK:
        raise CrfPageLifecycleConfigurationError("Lock Page must be the last enabled step.")
    if any(not item.allowed_role_ids for item in ordered):
        raise CrfPageLifecycleConfigurationError("Select at least one role for every enabled step.")
    return ordered


__all__ = [
    "CrfPageLifecycleConfigurationError",
    "CrfPageLifecycleStep",
    "CrfPageLifecycleStepPolicy",
    "validate_crf_page_lifecycle_steps",
]
