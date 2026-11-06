"""Which products' photos are gone (owner, 2026-11-01).

The owner, of products whose photo did not load on the live site: «Όταν το προϊόν δεν
φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις περισσότερες περιπτώσεις είναι not
found»: the shop has taken the product down, and its photo with it. A read of the live
site's photos (`.github/scripts/live_photos.py`, 01/11) found 19 of 244 gone (HTTP 404),
18 of them InStock UK's, and every other shop's loading.

The server checks the photos every night (`deployment/server/check_photos.py`) and writes
the addresses of those that are gone (HTTP 404 or 410) to a file the site reads
(`PICWISE_GONE_PHOTOS_FILE`): a product whose photo is in it is not shown, counted or
recommended (`state._prepared_search_catalogue`, `state._search_catalogue`). A photo the
check could not read (no answer, refused, a server error) is not called gone. Without the
file, every product is shown as before.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Iterable

GONE_PHOTOS_FILE_ENV = "PICWISE_GONE_PHOTOS_FILE"
# How often the file is looked at again for a newer one, at most.
_RECHECK_SECONDS = 60.0


class _GonePhotos:
    """The file, read once and again when it changes."""

    def __init__(self) -> None:
        self.key: tuple[Any, ...] | None = None
        self.checked = 0.0
        self.urls: frozenset[str] = frozenset()

    def refresh(self) -> None:
        path = str(os.environ.get(GONE_PHOTOS_FILE_ENV) or "").strip()
        now = time.monotonic()
        if self.key is not None and self.key[0] == path and now - self.checked < _RECHECK_SECONDS:
            return
        self.checked = now
        if not path:
            self.key, self.urls = ("", 0, 0), frozenset()
            return
        try:
            stat = os.stat(path)
        except OSError:
            self.key, self.urls = (path, 0, 0), frozenset()
            return
        key = (path, int(stat.st_mtime_ns), int(stat.st_size))
        if key == self.key:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, ValueError):
            document = None
        gone = document.get("gone") if isinstance(document, dict) else None
        self.urls = frozenset(
            " ".join(str(url).split()) for url in (gone if isinstance(gone, list) else ()) if str(url).strip()
        )
        self.key = key


_GONE = _GonePhotos()
_SET_BY_HAND = False


def set_gone_photos(urls: Iterable[str] | None) -> None:
    """Use these addresses instead of the file (tests); None goes back to the file."""
    global _SET_BY_HAND
    if urls is None:
        _SET_BY_HAND = False
        _GONE.key, _GONE.urls, _GONE.checked = None, frozenset(), 0.0
        return
    _SET_BY_HAND = True
    _GONE.urls = frozenset(" ".join(str(url).split()) for url in urls)
    _GONE.key = ("by hand", len(_GONE.urls), hash(_GONE.urls))


def gone_photos() -> frozenset[str]:
    """The addresses of the photos the last check found gone."""
    if not _SET_BY_HAND:
        _GONE.refresh()
    return _GONE.urls


def gone_photos_key() -> tuple[Any, ...]:
    """Which list of gone photos is in use: it changes whenever the list does."""
    gone_photos()
    return _GONE.key or ()


def photo_is_gone(product: Any, gone: frozenset[str] | None = None) -> bool:
    """Whether this product's photo is one the last check found gone."""
    urls = gone_photos() if gone is None else gone
    if not urls:
        return False
    return " ".join(str(getattr(product, "image_url", "") or "").split()) in urls
