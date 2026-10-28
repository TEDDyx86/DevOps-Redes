"""Create local secrets without overwriting an existing environment."""
import secrets
from pathlib import Path


def configure(root: Path):
    env_path = root / ".env"
    values = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    additions = []
    for key in ["LAB_TOKEN", "WEBHOOK_TOKEN", "POSTGRES_ADMIN_PASSWORD", "POSTGRES_MONITOR_PASSWORD", "POSTGRES_WORKLOAD_PASSWORD"]:
        if not values.get(key):
            values[key] = secrets.token_hex(24)
            additions.append(f"{key}={values[key]}")
    if additions:
        with env_path.open("a", encoding="utf-8") as stream:
            stream.write("\n" + "\n".join(additions) + "\n")
    secret_dir = root / ".runtime" / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    (secret_dir / "webhook-token").write_text(values["WEBHOOK_TOKEN"], encoding="utf-8")
    print("Ambiente local configurado. Tokens preservados em .env (ignorado pelo Git).")


if __name__ == "__main__":
    configure(Path(__file__).resolve().parents[1])
