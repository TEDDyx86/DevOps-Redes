import asyncio
import os
import threading
import time
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

from .integrity_files import linked, regular_file, signature
from .vulnerability_report import MAX_REPORT_BYTES, SERVICES, SEVERITIES, image_id, strict_json, timestamp, validate_report


def read_document(root, filename, limit):
    if linked(root) or not root.is_dir():
        raise ValueError("source_unavailable")
    with regular_file(root, (filename,)) as stream:
        before = os.fstat(stream.fileno())
        if before.st_size > limit:
            raise ValueError("report_too_large")
        content = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(content) > limit or len(content) != after.st_size or signature(before) != signature(after):
            raise ValueError("unstable_report")
    return strict_json(content)


def valid_inventory(value):
    try:
        if value["schema_version"] != 1 or type(value["ok"]) is not bool:
            raise ValueError("invalid_inventory")
        timestamp(value["checked_at"])
        if set(value["services"]) != set(SERVICES) or not isinstance(value["attempts"], dict) or len(value["attempts"]) > 16:
            raise ValueError("invalid_inventory")
        for row in value["services"].values():
            if row["image_id"] is not None:
                image_id(row["image_id"])
            if type(row["running"]) is not bool:
                raise ValueError("invalid_inventory")
        for key, attempt in value["attempts"].items():
            image_id(key)
            timestamp(attempt["at"])
            if attempt["status"] not in {"running", "failed", "completed"}:
                raise ValueError("invalid_attempt")
        return value
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid_inventory") from error


def fresh(value, now, limit):
    return value is not None and -5 <= now - value <= limit


class VulnerabilityMonitor:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else None
        self.lock = threading.Lock()
        self.snapshot = None
        self.sampled_at = None
        self.registry = CollectorRegistry()
        self.registry.register(self)

    def sample(self, now=None):
        now = time.time() if now is None else now
        snapshot = None
        if self.root is not None:
            try:
                inventory = valid_inventory(read_document(self.root, "inventory.json", 65536))
                reports = {}
                for identity in {row["image_id"] for row in inventory["services"].values()} - {None}:
                    try:
                        reports[identity] = validate_report(read_document(self.root, identity[7:] + ".json", MAX_REPORT_BYTES))
                    except (ValueError, OSError, UnicodeError, RecursionError):
                        reports[identity] = None
                snapshot = {"inventory": inventory, "reports": reports}
            except (ValueError, OSError, UnicodeError, RecursionError):
                pass
        with self.lock:
            self.snapshot, self.sampled_at = snapshot, now

    def overview(self, service="web-demo", severity="all", page=1, now=None):
        now = time.time() if now is None else now
        with self.lock:
            snapshot, sampled = self.snapshot, self.sampled_at
        inventory = snapshot["inventory"] if snapshot else None
        inventory_current = bool(inventory and inventory["ok"] and fresh(inventory["checked_at"], now, 120) and fresh(sampled, now, 20))
        rows = []
        selected = []
        for key, name in SERVICES.items():
            item = inventory["services"][key] if inventory else {}
            identity = item.get("image_id")
            report = snapshot["reports"].get(identity) if snapshot else None
            attempt = inventory["attempts"].get(identity, {}) if inventory else {}
            reason = "not_configured" if self.root is None else "inventory_unavailable"
            valid = False
            if inventory_current and identity:
                reason = "analysis_pending" if attempt.get("status") == "running" else "report_unavailable"
                if report:
                    if report["image_id"] != identity:
                        reason = "image_changed"
                    elif not fresh(report["scanned_at"], now, 86400):
                        reason = "analysis_expired"
                    elif not fresh(report["db_built_at"], now, 120 * 3600):
                        reason = "database_expired"
                    elif attempt.get("status") == "failed" and attempt.get("at", 0) >= report["scanned_at"]:
                        reason = "scanner_failed"
                    else:
                        valid, reason = True, None
            counts = report["counts"] if valid else None
            status = ("critical" if counts["critical"] else "warning" if counts["high"] else "notice" if sum(counts.values()) else "clear") if counts is not None else "unknown"
            rows.append({"id": key, "name": name, "status": status, "reason": reason, "counts": counts,
                "image_id": identity, "running": item.get("running", False), "scan_status": attempt.get("status"),
                "inventory_at": inventory["checked_at"] if inventory else None, "checked_at": sampled,
                "scanned_at": report["scanned_at"] if report else None, "db_built_at": report["db_built_at"] if report else None,
                "scanner_version": report["scanner_version"] if report else None, "package_count": report["package_count"] if report else None,
                "package_types": report["package_types"] if report else None})
            if key == service and valid:
                selected = [finding for finding in report["findings"] if severity == "all" or finding["severity"] == severity]
        offset = (page - 1) * 50
        return {"enabled": self.root is not None, "generated_at": now, "services": rows,
                "findings": {"service": service, "severity": severity, "page": page, "page_size": 50,
                             "total": len(selected), "items": selected[offset:offset + 50]}}

    def collect(self):
        yield GaugeMetricFamily("security_vulnerability_monitor_enabled", "Vulnerability report source configured", value=int(self.root is not None))
        if self.root is None:
            return
        rows = self.overview()["services"]
        success = GaugeMetricFamily("security_vulnerability_analysis_success", "Current analysis for observed image", labels=["service"])
        findings = GaugeMetricFamily("security_vulnerability_findings", "Advisory/package/version matches", labels=["service", "severity"])
        for row in rows:
            success.add_metric([row["id"]], int(row["counts"] is not None))
            if row["counts"] is not None:
                for severity in SEVERITIES:
                    findings.add_metric([row["id"], severity], row["counts"][severity])
        yield success
        yield findings

    async def run(self):
        while True:
            await asyncio.to_thread(self.sample)
            await asyncio.sleep(5)
