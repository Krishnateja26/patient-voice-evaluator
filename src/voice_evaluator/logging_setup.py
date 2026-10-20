"""Console logging.

Human-readable on stdout; the machine-readable record of a call is the JSONL
event log in the call's artifact directory, not this.
"""

from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        logging.getLogger("voice_evaluator").setLevel(level)
        return

    handler = RichHandler(rich_tracebacks=True, show_path=False, markup=False)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="%H:%M:%S"))

    root = logging.getLogger("voice_evaluator")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False

    # These are chatty and their failures surface through our own logs anyway.
    for noisy in ("twilio", "httpx", "httpcore", "websockets", "openai", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
