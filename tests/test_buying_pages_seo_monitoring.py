from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    MonitoringStatus,
    build_seo_monitoring_snapshot,
    generate_first_scale_batch,
)


class BuyingPagesSEOMonitoringTests(unittest.TestCase):
    def test_disconnected_sources_report_honest_placeholders(self) -> None:
        pages = generate_first_scale_batch().published_pages
        snapshot = build_seo_monitoring_snapshot(
            pages,
            search_console_connected=False,
            affiliate_connected=False,
            broken_link_scanner_connected=False,
        )
        self.assertEqual(snapshot.indexed_pages.status, MonitoringStatus.NOT_CONNECTED)
        self.assertEqual(snapshot.impressions.status, MonitoringStatus.NOT_CONNECTED)
        self.assertEqual(snapshot.clicks.status, MonitoringStatus.NOT_CONNECTED)
        self.assertEqual(snapshot.ctr.status, MonitoringStatus.NOT_CONNECTED)
        self.assertEqual(snapshot.sales.status, MonitoringStatus.NOT_CONNECTED)
        self.assertEqual(snapshot.broken_links.status, MonitoringStatus.DATA_NOT_YET)
        self.assertEqual(snapshot.zero_traffic_pages.status, MonitoringStatus.NOT_CONNECTED)
        self.assertIsNone(snapshot.sales.value)
        self.assertEqual(snapshot.sales.source, "affiliate_network")

    def test_connected_mode_uses_deterministic_test_data_not_fake_production(self) -> None:
        pages = generate_first_scale_batch().published_pages
        snapshot = build_seo_monitoring_snapshot(
            pages,
            search_console_connected=True,
            affiliate_connected=True,
            broken_link_scanner_connected=True,
        )
        for metric in (
            snapshot.indexed_pages,
            snapshot.impressions,
            snapshot.clicks,
            snapshot.ctr,
            snapshot.sales,
            snapshot.broken_links,
            snapshot.zero_traffic_pages,
        ):
            self.assertEqual(metric.status, MonitoringStatus.CONNECTED)
            self.assertEqual(metric.source, "deterministic_test_data")
        self.assertGreaterEqual(float(snapshot.ctr.value or 0.0), 0.0)

    def test_not_applicable_is_used_when_refresh_metric_has_no_pages(self) -> None:
        snapshot = build_seo_monitoring_snapshot(
            tuple(),
            search_console_connected=False,
            affiliate_connected=False,
            broken_link_scanner_connected=False,
        )
        self.assertEqual(snapshot.pages_needing_refresh.status, MonitoringStatus.NOT_APPLICABLE)
        self.assertIsNone(snapshot.pages_needing_refresh.value)


if __name__ == "__main__":
    unittest.main()
