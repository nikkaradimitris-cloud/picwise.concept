"""Functions the search runs when it answers, never the night's preparation of the catalogue.

The owner, 2026-11-24, of a deployment of half an hour for a change to the search alone
(«Αυτή δουλειά θα γίνεται τώρα κάθε φορά 30 λεπτά»): «Είναι καλό να περιορίσουμε το χρόνο
εφόσον υπάρχει ασφάλεια ότι θα βγει σωστό». A prepared file is read only by the code that
wrote it (`prepared_catalogue.code_fingerprint`), and a change to any file of the packages
it freezes prepared it again, about 30 minutes, even a change to how an answer is ordered
or a card drawn, which no prepared file holds.

A function marked `@answer_only` is left out of the fingerprint, its whole text: a change
inside it deploys in minutes. The mark is no promise taken on trust: while the catalogue is
prepared (`preparing`), every call of a marked function is recorded, and a file whose
preparation called one is written with the whole fingerprint (`used_while_preparing`;
`prepared_catalogue.write_prepared_catalogue`), so that a wrong mark makes deployments slower,
never the site wrong. Traced on 24/11: of search_selection's 115 functions the preparation ran
12, none of those marked.
"""
from __future__ import annotations

import functools
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {"preparing": 0, "used": set()}
MARK = "answer_only"

F = TypeVar("F", bound=Callable[..., Any])


def answer_only(function: F) -> F:
    """Mark a function the search runs when it answers and the preparation never runs."""

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if _STATE["preparing"]:
            with _LOCK:
                _STATE["used"].add(f"{function.__module__}.{function.__qualname__}")
        return function(*args, **kwargs)

    wrapper.__answer_only__ = True  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]


@contextmanager
def preparing() -> Iterator[None]:
    """While the catalogue is prepared: the marked functions called are recorded, from none."""
    with _LOCK:
        if not _STATE["preparing"]:
            _STATE["used"] = set()
        _STATE["preparing"] += 1
    try:
        yield
    finally:
        with _LOCK:
            _STATE["preparing"] -= 1


def used_while_preparing() -> frozenset[str]:
    """The marked functions the last preparation called; none when the marks hold."""
    with _LOCK:
        return frozenset(_STATE["used"])
