# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
import subprocess
from pathlib import Path

CHECKLISTS = {
    "S1": "S1_manager_checklist.md",
    "S2": "S2_drop_checklist.md",
    "S3": "S3_menus_checklist.md",
    "S4": "S4_sidebar_checklist.md",
}


def print_checklist(session: str) -> None:
    interactive_dir = Path(__file__).parent
    if session in CHECKLISTS:
        checklist_path = interactive_dir / CHECKLISTS[session]
        if checklist_path.exists():
            print(f"\n=== CHECKLIST FOR {session} ===")
            print(checklist_path.read_text("utf-8"))
            print("===============================\n")
        else:
            print(f"Checklist file {checklist_path} not found.")
    else:
        print(f"Unknown session '{session}'. Available sessions: {', '.join(CHECKLISTS.keys())}")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python capture.py <session: S1|S2|S3|S4|all> <output_trace_file>")
        return 1

    session = sys.argv[1]
    out_path = Path(sys.argv[2])

    if session != "all":
        print_checklist(session)
    else:
        for s in CHECKLISTS:
            print_checklist(s)

    print(f"Starting demo_app.py with LACE_TRACE=1...")
    print(f"Only lines containing '[TRACE]' will be written to: {out_path}\n")

    env = os.environ.copy()
    env["LACE_TRACE"] = "1"

    demo_app_path = Path(__file__).parent.parent.parent / "demo_app.py"
    
    # Run demo_app.py, capturing stdout and stderr
    proc = subprocess.Popen(
        [sys.executable, str(demo_app_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    trace_lines = []
    if proc.stdout:
        for line in proc.stdout:
            sys.stdout.write(line)
            if "[TRACE]" in line:
                # Extract from [TRACE] onwards to strip any variable logging prefixes/timestamps
                idx = line.find("[TRACE]")
                trace_lines.append(line[idx:].strip())

    proc.wait()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(trace_lines) + "\n" if trace_lines else "", encoding="utf-8")
    print(f"\nCapture complete. Wrote {len(trace_lines)} trace lines to {out_path}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
