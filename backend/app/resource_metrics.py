import asyncio
import time

import httpx

from .metrics import WINDOWS, finite
from .resources import CORE_METRICS


def merge_series(ranges, start, end, step):
    if not any(item.get("values") for result in ranges for item in result.get("result", [])):
        return []
    rows = {key: {"timestamp": key / 1000, **dict.fromkeys(CORE_METRICS)}
            for key in range(round(start * 1000), round(end * 1000) + 1, step * 1000)}
    for field, result in zip(CORE_METRICS, ranges):
        if len(result.get("result", [])) > 1: raise ValueError("ambiguous_resource_series")
        for metric in result.get("result", []):
            for stamp, value in metric.get("values", []):
                key = round(float(stamp) * 1000)
                number = finite(value)
                if key in rows: rows[key][field] = number if number is not None and number >= 0 else None
    return [rows[key] for key in sorted(rows)]


async def overview(monitor, prometheus, service, window):
    end = round(time.time(), 3)
    start, step = round(end - WINDOWS[window], 3), max(5, WINDOWS[window] // 180)
    available, series = True, []
    try:
        ranges = await asyncio.gather(*(prometheus.query(
            f'(service_resource_{field}{{job="platform",service="{service}"}} and on(service) '
            f'(service_resource_metric_available{{job="platform",service="{service}",metric="{field}"}} == 1)) '
            'and on() (up{job="platform"} == 1)', start, end, step) for field in CORE_METRICS))
        series = merge_series(ranges, start, end, step)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError):
        available = False
    return {**monitor.overview(), "service": service, "window": window, "history_available": available, "series": series}
