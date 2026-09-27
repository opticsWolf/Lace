# -*- coding: utf-8 -*-
"""Snapshot of every derived theme token, and a drift report against it.

    <python> tests/baselines/theme_tokens.py dump            # rewrite the 0.7.6 snapshot
    <python> tests/baselines/theme_tokens.py drift [stage]   # compare a stage (default: all)

The snapshot is the M0 reference for the 0.8 colour work: Phase 2 changes the
derivation on purpose, and the drift report shows by how much, per token.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SNAPSHOT = Path(__file__).resolve().parent / "theme_tokens_0.7.6.json"


def tokens(key: str) -> dict:
    """``{category: {token: json value}}`` for one theme."""
    from lace.dock_theme import deep_to_serializable
    from tests.theme_sets import load
    theme = load(key)
    return {getattr(cat, "name", str(cat)): deep_to_serializable(values)
            for cat, values in theme.items()}


def dump() -> None:
    from tests.theme_sets import all_themes
    data = {key: tokens(key) for key in all_themes()}
    SNAPSHOT.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {SNAPSHOT.name}: {len(data)} themes")


def _max_channel_delta(a, b):
    if (isinstance(a, list) and isinstance(b, list) and len(a) == len(b)
            and all(isinstance(x, int) for x in a + b)):
        return max(abs(x - y) for x, y in zip(a, b))
    return None


def drift(stage: str = "all") -> int:
    """Print changed tokens per theme; return the number changed."""
    from tests.theme_sets import resolve
    base = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    total = 0
    for key in resolve(stage):
        now, then = tokens(key), base.get(key)
        if then is None:
            print(f"{key}: not in snapshot")
            continue
        changed = []
        for cat in sorted(set(now) | set(then)):
            a, b = then.get(cat, {}), now.get(cat, {})
            for tok in sorted(set(a) | set(b)):
                if a.get(tok) != b.get(tok):
                    delta = _max_channel_delta(a.get(tok), b.get(tok))
                    changed.append(f"{cat}.{tok}" + (f" (max Δ{delta})" if delta is not None else ""))
        total += len(changed)
        print(f"{key}: {len(changed)} changed")
        for line in changed:
            print(f"    {line}")
    print(f"TOTAL: {total} tokens changed")
    return total


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    cmd = sys.argv[1] if len(sys.argv) > 1 else "drift"
    if cmd == "dump":
        dump()
    else:
        drift(sys.argv[2] if len(sys.argv) > 2 else "all")
