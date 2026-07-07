# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import logging
import os

_log = logging.getLogger("lace.trace")
TRACE_ON = os.environ.get("LACE_TRACE", "") not in ("", "0", "false")


def trace(event: str, **fields) -> None:
    """Emit one deterministic, greppable line per behavioural decision point.
    Off by default (zero overhead); enable with LACE_TRACE=1."""
    if TRACE_ON:
        kv = " ".join(f"{k}={v!r}" for k, v in sorted(fields.items()))
        _log.info("[TRACE] %s %s", event, kv)
