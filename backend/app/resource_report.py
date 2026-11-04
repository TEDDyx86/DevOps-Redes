"""Exact Docker counter conversion and the metadata-only resource snapshot contract."""
import math
import re
from datetime import datetime, timezone

SERVICES = {"web-demo": "HTTP", "postgres": "PostgreSQL", "dns": "DNS", "smtp": "SMTP"}
METRICS = ("cpu_cores", "memory_bytes", "memory_total_bytes", "engine_memory_limit_bytes", "read_bps", "write_bps")
FRESH_SECONDS = 20
MAX_BYTES = 65536
CPU_BUDGET = .8
IO_BUDGET = 10 * 1024 ** 2
MEMORY_BUDGETS = {key: (256 if key == "postgres" else 128) * 1024 ** 2 for key in SERVICES}
ERRORS = {None, "container_not_running", "sampling_failed", "container_changed", "invalid_stats", "ambiguous_container"}


def number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def stamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        result = parsed.timestamp() if parsed.tzinfo is not None else None
        if number(result) is not None:
            return result
    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
        pass
    raise ValueError("invalid_timestamp")


def container_id(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("invalid_container")
    return value


def unavailable(error="sampling_failed"):
    return {"container_id": None, "started_at": None, "observed_at": None, "running": False,
            "source_ok": False, "error": error, "values": dict.fromkeys(METRICS)}


def io_counts(raw):
    rows = raw.get("blkio_stats", {}).get("io_service_bytes_recursive")
    if not isinstance(rows, list) or len(rows) > 256:
        return None, None
    totals, seen = {}, set()
    for row in rows:
        if not isinstance(row, dict): return None, None
        operation = str(row.get("op", "")).lower()
        if operation not in ("read", "write"): continue
        key = (row.get("major"), row.get("minor"), operation)
        value = number(row.get("value"))
        if value is None or key in seen: return None, None
        seen.add(key)
        totals[operation] = totals.get(operation, 0) + value
    return totals.get("read"), totals.get("write")


def measure(identity, boot, raw, previous, now):
    container_id(identity)
    if not isinstance(raw, dict) or raw.get("id") != identity:
        raise ValueError("identity_mismatch")
    at, started = stamp(raw.get("read")), stamp(boot)
    if number(now) is None or not -5 <= now - at <= FRESH_SECONDS or started > at:
        raise ValueError("invalid_sample_time")
    cpu = number(raw.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage"))
    memory = raw.get("memory_stats", {})
    usage, limit = number(memory.get("usage")), number(memory.get("limit"))
    stats = memory.get("stats", {})
    cache = number(stats.get("total_inactive_file", stats.get("inactive_file", stats.get("cache"))))
    working = usage - cache if usage is not None and cache is not None and cache <= usage else None
    read, write = io_counts(raw)
    baseline = {"identity": identity, "boot": boot, "at": at, "cpu": cpu, "read": read, "write": write}
    values = dict.fromkeys(METRICS)
    values.update(memory_bytes=working, memory_total_bytes=usage, engine_memory_limit_bytes=limit)
    if previous and previous["identity"] == identity and previous["boot"] == boot and 0 < at - previous["at"] <= 30:
        elapsed = at - previous["at"]
        for source, target, divisor in (("cpu", "cpu_cores", 1e9), ("read", "read_bps", 1), ("write", "write_bps", 1)):
            current, old = baseline[source], previous[source]
            if current is not None and old is not None and current >= old:
                values[target] = number((current - old) / elapsed / divisor)
    source_ok = any(value is not None for value in (cpu, usage, read, write))
    if not source_ok: values = dict.fromkeys(METRICS)
    row = {"container_id": identity, "started_at": boot, "observed_at": at, "running": True,
           "source_ok": source_ok, "error": None if source_ok else "invalid_stats", "values": values}
    return row, baseline


def validate_snapshot(value):
    try:
        if value["schema_version"] != 1 or number(value["sampled_at"]) is None or set(value["services"]) != set(SERVICES):
            raise ValueError("invalid_snapshot")
        for row in value["services"].values():
            if type(row["running"]) is not bool or type(row["source_ok"]) is not bool or row["error"] not in ERRORS:
                raise ValueError("invalid_state")
            if set(row["values"]) != set(METRICS): raise ValueError("invalid_metrics")
            if any(v is not None and number(v) is None for v in row["values"].values()): raise ValueError("invalid_value")
            if row["container_id"] is not None: container_id(row["container_id"])
            if row["started_at"] is not None: stamp(row["started_at"])
            if row["observed_at"] is not None and number(row["observed_at"]) is None: raise ValueError("invalid_time")
            if row["source_ok"]:
                container_id(row["container_id"])
                if not row["running"] or row["observed_at"] is None or row["error"] is not None or stamp(row["started_at"]) > row["observed_at"]:
                    raise ValueError("invalid_source")
            elif any(v is not None for v in row["values"].values()):
                raise ValueError("unavailable_values")
        return value
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid_snapshot") from error
