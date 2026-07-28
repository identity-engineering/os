"""IE OS Surface Runtime – local deterministic core (v0)."""

from .apply import apply_interaction_signal
from .models import InteractionSignal, Receipt, ApplyStatus

__all__ = [
    "apply_interaction_signal",
    "InteractionSignal",
    "Receipt",
    "ApplyStatus",
]
