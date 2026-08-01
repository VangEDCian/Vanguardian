class RandomizationCodeConfigurationError(ValueError):
    """Raised when a scheme cannot produce a valid randomization code."""


def format_randomization_code(*, prefix: str, sequence_no: int, padding: int) -> str:
    normalized_prefix = str(prefix or "").strip()
    if not normalized_prefix:
        raise RandomizationCodeConfigurationError(
            "Randomization Code Prefix must be configured for the scheme."
        )

    normalized_sequence = int(sequence_no)
    normalized_padding = int(padding)
    if normalized_sequence <= 0:
        raise RandomizationCodeConfigurationError("Randomization sequence must be greater than zero.")
    if normalized_padding <= 0 or normalized_padding > 12:
        raise RandomizationCodeConfigurationError(
            "Randomization Code Padding must be between 1 and 12."
        )
    return f"{normalized_prefix}{normalized_sequence:0{normalized_padding}d}"


def format_scheme_randomization_code(*, scheme, sequence_no: int) -> str:
    return format_randomization_code(
        prefix=getattr(scheme, "randomization_code_prefix", ""),
        sequence_no=sequence_no,
        padding=getattr(scheme, "randomization_code_padding", 3),
    )


__all__ = [
    "RandomizationCodeConfigurationError",
    "format_randomization_code",
    "format_scheme_randomization_code",
]
