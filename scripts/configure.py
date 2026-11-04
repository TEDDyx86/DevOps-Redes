"""Create local secrets without overwriting an existing environment."""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.passwords import hash_password, verify_password


def configure(root: Path):
    env_path = root / ".env"
    values = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    additions = []
    if not values.get("ADMIN_USERNAME"):
        values["ADMIN_USERNAME"] = "admin"
        additions.append("ADMIN_USERNAME=admin")
    for key in ["LAB_TOKEN", "WEBHOOK_TOKEN", "POSTGRES_ADMIN_PASSWORD", "POSTGRES_MONITOR_PASSWORD", "POSTGRES_WORKLOAD_PASSWORD", "ADMIN_PASSWORD"]:
        if not values.get(key):
            values[key] = secrets.token_hex(24)
            additions.append(f"{key}={values[key]}")
    if additions:
        with env_path.open("a", encoding="utf-8") as stream:
            stream.write("\n" + "\n".join(additions) + "\n")
    secret_dir = root / ".runtime" / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    (root / ".runtime" / "vulnerabilities").mkdir(parents=True, exist_ok=True)
    (root / ".runtime" / "resources").mkdir(parents=True, exist_ok=True)
    (secret_dir / "webhook-token").write_text(values["WEBHOOK_TOKEN"], encoding="utf-8")
    hash_path = secret_dir / "admin-password-hash"
    existing = hash_path.read_text(encoding="utf-8").strip() if hash_path.exists() else ""
    if not verify_password(values["ADMIN_PASSWORD"], existing):
        hash_path.write_text(hash_password(values["ADMIN_PASSWORD"]), encoding="utf-8")
    print("Ambiente local configurado. Tokens preservados em .env (ignorado pelo Git).")


if __name__ == "__main__":
    configure(Path(__file__).resolve().parents[1])
