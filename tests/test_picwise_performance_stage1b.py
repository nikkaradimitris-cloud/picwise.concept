from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_search import resolve_live_search  # noqa: E402
from picwise_search import search_warmup  # noqa: E402
from picwise_search.search_warmup import (  # noqa: E402
    SEARCH_WARMUP_DELAY_SECONDS,
    get_search_warmup_state,
    schedule_search_warmup_if_needed,
)


class PicwisePerformanceStage1BTests(unittest.TestCase):
    def setUp(self) -> None:
        search_warmup._reset_search_warmup_for_tests()
        self.app = PicwiseLocalApp()

    def tearDown(self) -> None:
        search_warmup._reset_search_warmup_for_tests()

    def test_empty_homepage_schedules_warmup_without_blocking_render(self) -> None:
        with patch("picwise_app.app.schedule_search_warmup_if_needed") as schedule_mock:
            with patch("picwise_search.index_resolver_adapter.get_cached_offline_search_index") as index_mock:
                html = self.app.root_landing_html()
        schedule_mock.assert_called_once_with()
        index_mock.assert_not_called()
        self.assertIn("See the 4 best products before you buy", html)

    def test_empty_reference_schedules_warmup_without_calling_index_synchronously(self) -> None:
        with patch("picwise_app.app.schedule_search_warmup_if_needed") as schedule_mock:
            with patch("picwise_search.index_resolver_adapter.get_cached_offline_search_index") as index_mock:
                html = self.app.picwise_reference_html("")
        schedule_mock.assert_called_once_with()
        index_mock.assert_not_called()
        self.assertIn('action="/search"', html)

    def test_delayed_warmup_uses_real_index_cache_path(self) -> None:
        captured: dict[str, object] = {}

        class _ImmediateTimer:
            def __init__(self, delay: float, callback) -> None:
                captured["delay"] = delay
                captured["callback"] = callback

            def start(self) -> None:
                captured["started"] = True

            def cancel(self) -> None:
                captured["cancelled"] = True

        with patch.object(search_warmup, "_timer_factory", _ImmediateTimer):
            with patch(
                "picwise_search.search_warmup.get_cached_offline_search_index",
                return_value=object(),
            ) as index_mock:
                with patch(
                    "picwise_search.search_warmup.get_cached_canonical_vocabulary_registry",
                    return_value=object(),
                ) as registry_mock:
                    schedule_search_warmup_if_needed()
                    callback = captured["callback"]
                    self.assertEqual(captured["delay"], SEARCH_WARMUP_DELAY_SECONDS)
                    self.assertEqual(get_search_warmup_state(), "scheduled")
                    callback()

        index_mock.assert_called_once_with()
        registry_mock.assert_called_once_with()
        self.assertEqual(get_search_warmup_state(), "ready")

    def test_multiple_empty_homepage_calls_schedule_at_most_one_warmup(self) -> None:
        timer_instances: list[object] = []

        class _ImmediateTimer:
            def __init__(self, delay: float, callback) -> None:
                self.delay = delay
                self.callback = callback
                timer_instances.append(self)

            def start(self) -> None:
                return None

            def cancel(self) -> None:
                return None

        with patch.object(search_warmup, "_timer_factory", _ImmediateTimer):
            self.app.root_landing_html()
            self.app.picwise_reference_html("   ")
            self.app.root_landing_html()

        self.assertEqual(len(timer_instances), 1)
        self.assertEqual(get_search_warmup_state(), "scheduled")

    def test_non_empty_search_still_calls_resolve_live_search(self) -> None:
        with patch("picwise_app.app.schedule_search_warmup_if_needed") as schedule_mock:
            with patch("picwise_app.app.resolve_live_search", wraps=resolve_live_search) as resolve_mock:
                html = self.app.picwise_reference_html("power bank")
        schedule_mock.assert_not_called()
        resolve_mock.assert_called_once_with("power bank")
        self.assertIn("View on Amazon", html)

    def test_warmup_failure_does_not_break_search_path(self) -> None:
        with patch(
            "picwise_search.search_warmup.get_cached_offline_search_index",
            side_effect=RuntimeError("warmup failed"),
        ):
            with patch(
                "picwise_search.search_warmup.get_cached_canonical_vocabulary_registry",
                return_value=object(),
            ):
                search_warmup._run_warmup_task()
        self.assertEqual(get_search_warmup_state(), "failed")

        with patch("picwise_app.app.resolve_live_search", wraps=resolve_live_search) as resolve_mock:
            html = self.app.picwise_reference_html("power bank")
        resolve_mock.assert_called_once_with("power bank")
        self.assertIn("View on Amazon", html)


if __name__ == "__main__":
    unittest.main()
