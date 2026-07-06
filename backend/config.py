"""Environment-driven configuration for the Kiki complete-trip demo backend."""
import os


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# Serve JSON fixtures from backend/mocks/ instead of calling real Sabre.
MOCK_MODE: bool = _bool_env("MOCK_MODE", True)

# Artificial latency added to every endpoint so voice rehearsals match
# real API timing. Set to 0 for tests / local iteration.
MOCK_DELAY_SECONDS: float = float(os.getenv("MOCK_DELAY_SECONDS", "1.5"))

# Return a polished fake payment confirmation instead of charging anything.
PAYMENT_MOCK: bool = _bool_env("PAYMENT_MOCK", True)
