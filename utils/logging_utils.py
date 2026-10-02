"""Logging setup shared by the backend and the agents."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger (configures the root logger once)."""
    global _CONFIGURED

    if not _CONFIGURED:
        level_name = "INFO"
        try:  # import lazily so utils can be used in scripts too
            from backend.config import settings

            level_name = settings.log_level
        except Exception:  # pragma: no cover - fallback for standalone use
            pass

        logging.basicConfig(
            level=getattr(logging, level_name.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stdout,
        )
        _CONFIGURED = True

    return logging.getLogger(name)
