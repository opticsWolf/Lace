# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Theme kit: build, check and extend Lace themes from a few seed colours.

A theme is a *palette* (seed colours and colour keywords) plus a *chassis*
(geometry and styling)::

    from lace.theme_kit import derive, compose, audit, family, status_colors, export

    pal = derive(base="#1b1d23", accent="#4f8cff")      # text from the base
    spec = compose(pal, chassis="edge", title_mode="darker")
    report = audit(spec)                                  # Phase 2 rules + author checks
    report.failures, report.capped, report.suggest()
    fam = family(spec)                                    # dark / neutral / light
    export.to_json(spec, "my_theme.json")                 # loads with load_theme_json()

The same from the shell: ``python -m lace.theme_kit --help``.
"""

from lace.theme_kit import export
from lace.theme_kit.audit import AuditReport, apply_fix, audit
from lace.theme_kit.chassis import (CHASSIS, CHASSIS_FIELDS, chassis_of, compose,
                                    palette_of, restyle)
from lace.theme_kit.derive import PALETTE_FIELDS, Palette, derive, status_colors
from lace.theme_kit.family import VARIANTS, family, spec_delta, variant_of

__all__ = [
    "AuditReport", "CHASSIS", "CHASSIS_FIELDS", "PALETTE_FIELDS", "Palette", "VARIANTS",
    "apply_fix", "audit", "chassis_of", "compose", "derive", "export", "family", "palette_of",
    "restyle", "spec_delta", "status_colors", "variant_of",
]
