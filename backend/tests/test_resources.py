import copy
import json
import time
from datetime import datetime, timezone

import pytest

from backend.app.resource_report import measure, unavailable, validate_snapshot


IDENTITY = "a" * 64
BOOT = "1970-01-01T00:00:01Z"


def raw(at=1000, cpu=1_000_000_000, read=100, write=200):
    return {"id": IDENTITY, "read": datetime.fromtimestamp(at, timezone.utc).isoformat(),
            "cpu_stats": {"cpu_usage": {"total_usage": cpu}},
            "memory_stats": {"usage": 1000, "stats": {"inactive_file": 200}, "limit": 10000},
            "blkio_stats": {"io_service_bytes_recursive": [
                {"major": 8, "minor": 0, "op": "Read", "value": read},
                {"major": 8, "minor": 0, "op": "Write", "value": write}]}}


def test_exact_cpu_io_deltas_and_memory_cache():
    first, baseline = measure(IDENTITY, BOOT, raw(), None, 1000)
    assert first["values"]["cpu_cores"] is None and first["values"]["read_bps"] is None
    second, _ = measure(IDENTITY, BOOT, raw(1005, 6_000_000_000, 600, 1200), baseline, 1005)
    assert second["values"] == {"cpu_cores": 1.0, "memory_bytes": 800, "memory_total_bytes": 1000,
                                "engine_memory_limit_bytes": 10000, "read_bps": 100.0, "write_bps": 200.0}
    assert second["source_ok"] and second["running"]


def test_true_zeros_survive_but_missing_io_cache_does_not_become_zero():
    value = raw(cpu=0, read=0, write=0)
    first, previous = measure(IDENTITY, BOOT, value, None, 1000)
    second, _ = measure(IDENTITY, BOOT, raw(1005, 0, 0, 0), previous, 1005)
    assert second["values"]["cpu_cores"] == second["values"]["read_bps"] == second["values"]["write_bps"] == 0
    del value["memory_stats"]["stats"]["inactive_file"]
    value["blkio_stats"]["io_service_bytes_recursive"] = None
    missing, _ = measure(IDENTITY, BOOT, value, None, 1000)
    assert missing["values"]["memory_bytes"] is None and missing["values"]["read_bps"] is None
    assert missing["values"]["memory_total_bytes"] == 1000


@pytest.mark.parametrize("change", ["restart", "identity", "regression", "backwards_time", "long_gap"])
def test_restart_bad_interval_or_counter_cannot_create_rate(change):
    _, previous = measure(IDENTITY, BOOT, raw(), None, 1000)
    identity, boot, value, now = IDENTITY, BOOT, raw(1005), 1005
    if change == "restart": boot = "1970-01-01T00:16:42Z"
    if change == "identity": identity = "b" * 64; value["id"] = identity
    if change == "regression": value = raw(1005, 0, 0, 0)
    if change == "backwards_time": value = raw(999); now = 1000
    if change == "long_gap": value = raw(1040); now = 1040
    result, _ = measure(identity, boot, value, previous, now)
    assert result["values"]["cpu_cores"] is None and result["values"]["read_bps"] is None


@pytest.mark.parametrize("path,value", [
    (("cpu_stats", "cpu_usage", "total_usage"), float("nan")),
    (("cpu_stats", "cpu_usage", "total_usage"), True),
    (("memory_stats", "usage"), -1),
    (("memory_stats", "stats", "inactive_file"), 2000),
])
def test_invalid_numeric_fields_remain_unavailable(path, value):
    data = raw()
    target = data
    for name in path[:-1]: target = target[name]
    target[path[-1]] = value
    result, baseline = measure(IDENTITY, BOOT, data, None, 1000)
    if path[0] == "cpu_stats": assert baseline["cpu"] is None
    else: assert result["values"]["memory_bytes"] is None


@pytest.mark.parametrize("kind", ["wrong_id", "future", "stale", "naive", "bad_boot"])
def test_identity_and_timestamps_are_required(kind):
    data = raw(); boot = BOOT
    if kind == "wrong_id": data["id"] = "b" * 64
    if kind == "future": data = raw(1006)
    if kind == "stale": data = raw(979)
    if kind == "naive": data["read"] = "1970-01-01T00:16:40"
    if kind == "bad_boot": boot = "invalid"
    with pytest.raises(ValueError): measure(IDENTITY, boot, data, None, 1000)


def test_snapshot_has_fixed_services_metrics_and_no_nonfinite_values():
    row, _ = measure(IDENTITY, BOOT, raw(), None, 1000)
    snapshot = {"schema_version": 1, "sampled_at": 1000, "services": {
        name: copy.deepcopy(row) for name in ("web-demo", "postgres", "dns", "smtp")}}
    assert validate_snapshot(snapshot)
    for field, value in [("cpu_cores", float("inf")), ("secret", 1), ("memory_bytes", True)]:
        invalid = copy.deepcopy(snapshot); invalid["services"]["dns"]["values"][field] = value
        with pytest.raises(ValueError): validate_snapshot(invalid)
    snapshot["services"]["other"] = row
    with pytest.raises(ValueError): validate_snapshot(snapshot)


def test_absent_container_is_unavailable_not_empty_healthy_metrics():
    row = unavailable("container_not_running")
    assert not row["source_ok"] and not row["running"]
    assert all(value is None for value in row["values"].values())


def test_cgroup_v1_prefers_total_cache_including_children():
    data = raw()
    data["memory_stats"]["stats"]["total_inactive_file"] = 500
    result, _ = measure(IDENTITY, BOOT, data, None, 1000)
    assert result["values"]["memory_bytes"] == 500


def test_metadata_limit_without_any_counter_is_unavailable():
    data = raw()
    data["cpu_stats"] = {}
    data["memory_stats"] = {"limit": 10000}
    data["blkio_stats"] = {}
    result, _ = measure(IDENTITY, BOOT, data, None, 1000)
    assert not result["source_ok"] and all(value is None for value in result["values"].values())
