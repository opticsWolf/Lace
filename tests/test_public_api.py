# -*- coding: utf-8 -*-
"""What `import lace` exposes — §5.4.

The package used to carry a PEP 562 __getattr__ that, on the first missed
attribute, imported every module in the package and registered every public
callable it found into a flat registry. It was not lazy, it made every
internal helper reachable as ``lace.<name>``, and it swallowed ImportError
with a warning so a genuinely broken module degraded into a silent
AttributeError. The explicit imports are the API now, and __all__ says so.
"""

import inspect
import pathlib

import lace


def test_a_missing_name_raises_attribute_error():
    """Not a whole-package import, and not a warning — an error."""
    try:
        lace.definitely_not_a_real_symbol
    except AttributeError:
        pass
    else:
        raise AssertionError("the dynamic fallback resolved a nonexistent name")


def test_internal_helpers_are_not_reachable_from_the_package():
    """The registry leaked these. They are implementation, not API."""
    for name in ("find_parent_dock_widget", "paint_tab", "top_open_path",
                 "resolve_tab_outline_color", "blend_colors", "DockStyled"):
        assert not hasattr(lace, name), f"lace.{name} is not public API"


def test_all_is_accurate_in_both_directions():
    """A name in __all__ that does not resolve breaks `from lace import *`.

    A public name missing from __all__ is worse: it is API by accident.
    """
    missing = [n for n in lace.__all__ if not hasattr(lace, n)]
    assert not missing, missing

    exported = {n for n in vars(lace)
                if not n.startswith("_") and not inspect.ismodule(getattr(lace, n))}
    assert exported - set(lace.__all__) == set()


def test_star_import_matches_all():
    namespace = {}
    exec("from lace import *", namespace)
    got = {n for n in namespace if not n.startswith("__")}
    assert got == set(lace.__all__) - {"__version__"}


def test_the_discovery_machinery_is_gone():
    """Including the hand-maintained skip list that named a deleted module."""
    for name in ("get_model_registry", "_discover_models", "_MODEL_REGISTRY",
                 "_SKIP_MODULES", "_DISCOVERY_LOCK"):
        assert not hasattr(lace, name), f"{name} survived"

    source = (pathlib.Path(lace.__file__)).read_text(encoding="utf-8")
    assert "def __getattr__" not in source
    assert "_SKIP_MODULES" not in source, "the hand-maintained skip list survived"


def test_importing_lace_does_not_pull_in_every_module():
    """The point of dropping the loader: a bounded import.

    The frameless float stack is opt-in — chosen per manager via
    floating_container_class() — and must not arrive with the package.
    """
    import subprocess
    import sys

    code = (
        "import sys, lace; "
        "print(','.join(m for m in ('lace.frameless_titlebar', "
        "'lace.floating_dock_container_frameless') if m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code],
                         capture_output=True, text=True,
                         cwd=str(pathlib.Path(lace.__file__).parent.parent))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "", f"eagerly imported: {out.stdout.strip()}"
