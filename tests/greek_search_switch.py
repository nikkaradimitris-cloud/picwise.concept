"""Turn the Greek search on for a test module that tests it.

Owner, 2026-11-07: «Ναι σε όλα, κλείσε και τα δύο»: the site is English, for the UK, and
Greek and greeklish are not read in a search (`concept_understanding.greek_search_on`).
The code that reads them stays, for a Greek site one day, and so do its tests: a module
that tests it imports these two, which unittest runs around the module's tests:

    from greek_search_switch import setUpModule, tearDownModule  # noqa: E402,F401
"""
from __future__ import annotations

import os

# `picwise_nlu.concept_understanding.GREEK_SEARCH_ENV`, written out so this file needs no
# import path of its own.
GREEK_SEARCH_ENV = "PICWISE_GREEK_SEARCH"

_previous: list[str | None] = []


def setUpModule() -> None:  # noqa: N802 - unittest's name
    _previous.append(os.environ.get(GREEK_SEARCH_ENV))
    os.environ[GREEK_SEARCH_ENV] = "on"


def tearDownModule() -> None:  # noqa: N802 - unittest's name
    previous = _previous.pop() if _previous else None
    if previous is None:
        os.environ.pop(GREEK_SEARCH_ENV, None)
    else:
        os.environ[GREEK_SEARCH_ENV] = previous
