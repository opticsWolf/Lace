# -*- coding: utf-8 -*-
"""Layout serializer exception tests — ARCHITECTURE.md §5.1 (layout_serializer.py).

The serializer surfaces four exception types with a strict hierarchy; the
engine's guards (type validation, version validation) must map to them.
"""

import pytest

from lace.layout_serializer import (
    LayoutError,
    LayoutIOError,
    InvalidFormatError,
    RestoreFailureError,
)


def test_exception_hierarchy():
    assert issubclass(LayoutIOError, LayoutError)
    assert issubclass(InvalidFormatError, LayoutError)
    assert issubclass(RestoreFailureError, LayoutError)
    # IO and format failures are distinct categories
    assert not issubclass(LayoutIOError, InvalidFormatError)


def test_exceptions_carry_messages():
    for exc_type, message in (
        (LayoutError, "generic"),
        (LayoutIOError, "disk full"),
        (InvalidFormatError, "bad json"),
        (RestoreFailureError, "missing widget"),
    ):
        with pytest.raises(LayoutError) as excinfo:
            raise exc_type(message)
        assert str(excinfo.value) == message


def test_caught_as_base_layout_error():
    try:
        raise InvalidFormatError("corrupt payload")
    except LayoutError:
        pass  # the public API contract: callers only need LayoutError
    else:
        pytest.fail("InvalidFormatError is not a LayoutError")
