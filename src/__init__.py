"""Clean-Room Statistical Power Analysis Package for Paired Samples t-Test (t-paired)."""

from .engine import (
    ValidationError,
    calculate_t_paired,
    compute_effect_size_dz,
    round_up_sample_size,
)

__all__ = [
    "ValidationError",
    "calculate_t_paired",
    "compute_effect_size_dz",
    "round_up_sample_size",
]
__version__ = "1.0.0"
