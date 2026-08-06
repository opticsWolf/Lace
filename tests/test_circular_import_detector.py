# -*- coding: utf-8 -*-
"""Tests for the AST-based circular import detector.

The detector is a standalone script (tests/circular_import_detector.py) whose
main() returns an exit code and whose ModuleGraph class can be driven directly,
so these tests call both the module API and the CLI entry point.
"""

import json

import pytest

import circular_import_detector as detector

LACE_DIR = detector.Path(__file__).resolve().parent.parent / "lace"


def write_module(tmp_path, name, content):
    """Write a tiny module into a scratch package directory."""
    (tmp_path / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Real package: lace/ must stay cycle-free at module level
# ---------------------------------------------------------------------------
def test_lace_package_has_no_module_level_cycles():
    """The production package must not introduce module-level import cycles."""
    graph = detector.ModuleGraph(LACE_DIR)
    assert graph.find_cycles() == []
    assert detector.main([str(LACE_DIR)]) == 0


def test_lace_package_edges_are_internal_only():
    """Every tracked edge must point at another lace module."""
    graph = detector.ModuleGraph(LACE_DIR)
    for module, deps in graph.graph.items():
        for dep in deps:
            assert dep in graph.modules, f"{module} -> {dep} is not a lace module"


# ---------------------------------------------------------------------------
# Detection: real cycles must be found
# ---------------------------------------------------------------------------
def test_detects_mutual_cycle(tmp_path):
    write_module(tmp_path, "a.py", "from lace.b import B\nclass A: pass\n")
    write_module(tmp_path, "b.py", "from lace.a import A\nclass B: pass\n")
    graph = detector.ModuleGraph(tmp_path)
    cycles = graph.find_cycles()
    assert any(set(c) == {"a", "b"} for c in cycles)
    assert detector.main([str(tmp_path)]) == 1


def test_detects_self_import(tmp_path):
    write_module(tmp_path, "c.py", "from lace.c import C\nclass C: pass\n")
    cycles = detector.ModuleGraph(tmp_path).find_cycles()
    assert any(set(c) == {"c"} for c in cycles)


def test_detects_cycle_via_relative_imports(tmp_path):
    write_module(tmp_path, "a.py", "from .b import B\nclass A: pass\n")
    write_module(tmp_path, "b.py", "from .a import A\nclass B: pass\n")
    cycles = detector.ModuleGraph(tmp_path).find_cycles()
    assert any(set(c) == {"a", "b"} for c in cycles)


def test_sample_cycle_returns_round_trip_path(tmp_path):
    write_module(tmp_path, "a.py", "from lace.b import B\nclass A: pass\n")
    write_module(tmp_path, "b.py", "from lace.a import A\nclass B: pass\n")
    graph = detector.ModuleGraph(tmp_path)
    component = next(c for c in graph.find_cycles() if set(c) == {"a", "b"})
    path = graph.sample_cycle(component)
    assert path[0] == path[-1]                 # closes the loop
    assert set(path[:-1]) == {"a", "b"}        # visits both members


# ---------------------------------------------------------------------------
# Non-cycles must be ignored (this is why we use AST, not a line scanner)
# ---------------------------------------------------------------------------
def test_ignores_type_checking_and_function_level_imports(tmp_path):
    write_module(
        tmp_path,
        "a.py",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from lace.b import B\n"
        "def f():\n"
        "    from lace.b import B\n"
        "    return B\n"
        "class A: pass\n",
    )
    write_module(tmp_path, "b.py", "class B: pass\n")
    graph = detector.ModuleGraph(tmp_path)
    assert graph.graph["a"] == set()           # no runtime edge to b
    assert graph.find_cycles() == []
    assert detector.main([str(tmp_path)]) == 0


def test_ignores_docstring_import_examples(tmp_path):
    # A docstring containing import-looking text must not create an edge.
    write_module(
        tmp_path,
        "a.py",
        '"""Example:\n\n    from lace.b import B\n"""\n'
        "class A: pass\n",
    )
    write_module(tmp_path, "b.py", "class B: pass\n")
    graph = detector.ModuleGraph(tmp_path)
    assert graph.graph["a"] == set()


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------
def test_main_rejects_missing_directory(tmp_path):
    assert detector.main([str(tmp_path / "does_not_exist")]) == 2


def test_main_json_output_reports_cycles(tmp_path, capsys):
    write_module(tmp_path, "a.py", "from lace.b import B\nclass A: pass\n")
    write_module(tmp_path, "b.py", "from lace.a import A\nclass B: pass\n")
    assert detector.main([str(tmp_path), "--json"]) == 1
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])
    assert any(set(c) == {"a", "b"} for c in payload["cycles"])
