from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .google_quality_gate import is_publicly_eligible
from .models import BuyingPage, RefreshStatus


class MonitoringStatus(str, Enum):
    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"
    DATA_NOT_YET = "data_not_yet"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class MetricSnapshot:
    value: int | float | None
    status: MonitoringStatus
    source: str


@dataclass(frozen=True)
class SEOMonitoringSnapshot:
    indexed_pages: MetricSnapshot
    impressions: MetricSnapshot
    clicks: MetricSnapshot
    ctr: MetricSnapshot
    sales: MetricSnapshot
    broken_links: MetricSnapshot
    zero_traffic_pages: MetricSnapshot
    pages_needing_refresh: MetricSnapshot
    generated_at: datetime


def _metric(value: int | float | None, status: MonitoringStatus, source: str) -> MetricSnapshot:
    return MetricSnapshot(value=value, status=status, source=source)


def _deterministic_search_console_metrics(indexable_pages: tuple[BuyingPage, ...]) -> tuple[int, int, float, int]:
    impressions = sum((index + 20) % 47 for index, _page in enumerate(indexable_pages))
    clicks = sum((index + 5) % 9 for index, _page in enumerate(indexable_pages))
    ctr = round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0
    zero_traffic_pages = sum(1 for index, _page in enumerate(indexable_pages) if index % 13 == 0)
    return impressions, clicks, ctr, zero_traffic_pages


def build_seo_monitoring_snapshot(
    pages: tuple[BuyingPage, ...],
    *,
    search_console_connected: bool = False,
    affiliate_connected: bool = False,
    broken_link_scanner_connected: bool = False,
) -> SEOMonitoringSnapshot:
    generated_at = datetime.now(tz=timezone.utc)
    indexable_pages = tuple(page for page in pages if is_publicly_eligible(page))

    if search_console_connected:
        impressions, clicks, ctr, zero_traffic_pages = _deterministic_search_console_metrics(indexable_pages)
        indexed_pages_metric = _metric(
            len(indexable_pages),
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
        impressions_metric = _metric(
            impressions,
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
        clicks_metric = _metric(
            clicks,
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
        ctr_metric = _metric(
            ctr,
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
        zero_traffic_metric = _metric(
            zero_traffic_pages,
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
    else:
        indexed_pages_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "search_console",
        )
        impressions_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "search_console",
        )
        clicks_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "search_console",
        )
        ctr_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "search_console",
        )
        zero_traffic_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "search_console",
        )

    if affiliate_connected:
        sales_value = sum((index % 3) for index, _page in enumerate(indexable_pages))
        sales_metric = _metric(
            sales_value,
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
    else:
        sales_metric = _metric(
            None,
            MonitoringStatus.NOT_CONNECTED,
            "affiliate_network",
        )

    if broken_link_scanner_connected:
        broken_links_metric = _metric(
            sum(1 for index, _page in enumerate(pages) if index % 97 == 0),
            MonitoringStatus.CONNECTED,
            "deterministic_test_data",
        )
    else:
        broken_links_metric = _metric(
            None,
            MonitoringStatus.DATA_NOT_YET,
            "broken_link_scanner",
        )

    if not pages:
        refresh_metric = _metric(
            None,
            MonitoringStatus.NOT_APPLICABLE,
            "internal_refresh_metadata",
        )
    else:
        pages_needing_refresh = sum(
            1
            for page in pages
            if page.refresh_metadata.refresh_status
            in {RefreshStatus.REFRESH_DUE, RefreshStatus.REFRESH_FAILED, RefreshStatus.MANUAL_REQUIRED}
        )
        refresh_metric = _metric(
            pages_needing_refresh,
            MonitoringStatus.CONNECTED,
            "internal_refresh_metadata",
        )

    return SEOMonitoringSnapshot(
        indexed_pages=indexed_pages_metric,
        impressions=impressions_metric,
        clicks=clicks_metric,
        ctr=ctr_metric,
        sales=sales_metric,
        broken_links=broken_links_metric,
        zero_traffic_pages=zero_traffic_metric,
        pages_needing_refresh=refresh_metric,
        generated_at=generated_at,
    )
