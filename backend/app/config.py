import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    prometheus_url: str = "http://127.0.0.1:9090"
    demo_url: str = "http://127.0.0.1:8011"
    database_path: Path = Path("data/incidents.sqlite")
    webhook_token: str = ""
    lab_token: str = ""
    enable_probe: bool = True
    probe_interval: float = 5
    frontend_path: Path = Path("frontend/dist")
    postgres_monitor_dsn: str = ""
    postgres_workload_dsn: str = ""
    dns_server: str = ""
    dns_port: int = 1053
    dns_name: str = "app.aularedes.test."
    dns_expected: str = "192.0.2.10"
    smtp_host: str = ""
    smtp_port: int = 2525
    auth_username: str = "admin"
    auth_password_hash: str = ""
    auth_cookie_secure: bool = False
    integrity_root: Path | None = None
    vulnerability_root: Path | None = None
    resource_root: Path | None = None

    @classmethod
    def from_env(cls):
        hash_path = os.getenv("AUTH_PASSWORD_HASH_FILE", "")
        password_hash = Path(hash_path).read_text(encoding="utf-8").strip() if hash_path and Path(hash_path).is_file() else ""
        return cls(
            prometheus_url=os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090"),
            demo_url=os.getenv("DEMO_URL", "http://127.0.0.1:8011"),
            database_path=Path(os.getenv("DATABASE_PATH", "data/incidents.sqlite")),
            webhook_token=os.getenv("WEBHOOK_TOKEN", ""),
            lab_token=os.getenv("LAB_TOKEN", ""),
            enable_probe=os.getenv("ENABLE_PROBE", "true").lower() == "true",
            frontend_path=Path(os.getenv("FRONTEND_PATH", "frontend/dist")),
            postgres_monitor_dsn=os.getenv("POSTGRES_MONITOR_DSN", ""),
            postgres_workload_dsn=os.getenv("POSTGRES_WORKLOAD_DSN", ""),
            dns_server=os.getenv("DNS_SERVER", ""),
            dns_port=int(os.getenv("DNS_PORT", "1053")),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "2525")),
            auth_username=os.getenv("ADMIN_USERNAME", "admin"),
            auth_password_hash=password_hash,
            auth_cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
            integrity_root=Path(os.environ["CONFIG_WATCH_ROOT"]) if os.getenv("CONFIG_WATCH_ROOT") else None,
            vulnerability_root=Path(os.environ["VULNERABILITY_REPORT_ROOT"]) if os.getenv("VULNERABILITY_REPORT_ROOT") else None,
            resource_root=Path(os.environ["RESOURCE_REPORT_ROOT"]) if os.getenv("RESOURCE_REPORT_ROOT") else None,
        )
