import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    prometheus_url: str = "http://127.0.0.1:9090"
    demo_url: str = "http://127.0.0.1:8001"
    database_path: Path = Path("data/incidents.sqlite")
    webhook_token: str = ""
    lab_token: str = ""
    enable_probe: bool = True
    probe_interval: float = 5
    frontend_path: Path = Path("frontend/dist")
    postgres_monitor_dsn: str = ""
    postgres_workload_dsn: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            prometheus_url=os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090"),
            demo_url=os.getenv("DEMO_URL", "http://127.0.0.1:8001"),
            database_path=Path(os.getenv("DATABASE_PATH", "data/incidents.sqlite")),
            webhook_token=os.getenv("WEBHOOK_TOKEN", ""),
            lab_token=os.getenv("LAB_TOKEN", ""),
            enable_probe=os.getenv("ENABLE_PROBE", "true").lower() == "true",
            frontend_path=Path(os.getenv("FRONTEND_PATH", "frontend/dist")),
            postgres_monitor_dsn=os.getenv("POSTGRES_MONITOR_DSN", ""),
            postgres_workload_dsn=os.getenv("POSTGRES_WORKLOAD_DSN", ""),
        )
