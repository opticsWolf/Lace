# -*- coding: utf-8 -*-
"""One version, stated in five places, and nothing was keeping them equal.

At the 0.7.0 bump the three doc headers read 0.6.5, 0.5.0 and 0.5.0 against a
package at 0.6.18 — thirteen and eighteen patches behind, each of them wrong
for months without anything noticing.  A stale "**Version:**" line is a small
thing on its own; what makes it worth a test is that it is the first thing a
reader checks to decide whether the rest of the document is current, so a
wrong one quietly discredits the parts that *are* right.

The CHANGELOG is checked from the other direction: it is the one file where
the current version must appear as a released heading, because a bump that
ships without an entry is a change nobody can find afterwards.
"""

import io
import re
from pathlib import Path

import pytest

import lace

ROOT = Path(__file__).resolve().parent.parent

#: Files carrying a "**Version:** x.y.z" header.
DOC_HEADERS = ("README.md", "docs/ARCHITECTURE.md", "docs/QUICK_REFERENCE.md")


def _read(relative: str) -> str:
    return io.open(ROOT / relative, encoding="utf-8").read()


def test_the_package_and_the_build_agree():
    """pyproject is what PyPI publishes; __version__ is what users print."""
    pyproject = _read("pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert match, "pyproject.toml has no version"
    assert match.group(1) == lace.__version__


@pytest.mark.parametrize("relative", DOC_HEADERS)
def test_a_doc_header_states_the_current_version(relative):
    text = _read(relative)
    match = re.search(r"^\*\*Version:\*\*\s*(\S+)", text, re.M)
    assert match, f"{relative} lost its version header"
    assert match.group(1) == lace.__version__, (
        f"{relative} says {match.group(1)}, package is {lace.__version__}")


def test_the_changelog_has_an_entry_for_the_current_version():
    """A bump with no entry is a change nobody can find afterwards."""
    headings = re.findall(r"^## \[([^\]]+)\]", _read("CHANGELOG.md"), re.M)
    assert headings, "CHANGELOG.md has no version headings"
    assert lace.__version__ in headings, (
        f"CHANGELOG.md has no [{lace.__version__}] entry; newest is "
        f"[{headings[0]}]")
    assert headings[0] == lace.__version__, (
        f"CHANGELOG.md's newest entry is [{headings[0]}], not the current "
        f"[{lace.__version__}] — entries go newest first")
