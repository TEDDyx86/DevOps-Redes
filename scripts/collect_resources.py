"""Local read-only Docker statistics worker; API receives metadata files only."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.resource_report import SERVICES, MAX_BYTES, container_id, measure, unavailable, validate_snapshot
from backend.app.vulnerability_report import strict_json
from scripts.scan_vulnerabilities import exclusive_lock, atomic_json

DIRECTORY = ROOT / ".runtime/resources"
RUNTIME = ROOT / ".runtime/resource-worker-venv"


def run_command(arguments, timeout=10, limit=MAX_BYTES, request=None):
    if request is not None and len(request) > 16384: raise ValueError("request_too_large")
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    buffers, errors = [bytearray(), bytearray()], []
    process = subprocess.Popen(arguments, cwd=ROOT, shell=False, stdin=subprocess.PIPE if request is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    def read(pipe, index, maximum):
        try:
            while chunk := pipe.read(4096):
                if len(buffers[index]) + len(chunk) > maximum:
                    raise ValueError("output_too_large")
                buffers[index].extend(chunk)
        except (ValueError, OSError) as error:
            errors.append(error)
            try: process.kill()
            except OSError: pass
        finally: pipe.close()
    readers = [threading.Thread(target=read, args=(process.stdout, 0, limit)),
               threading.Thread(target=read, args=(process.stderr, 1, 16384))]
    for reader in readers: reader.start()
    try:
        if request is not None:
            process.stdin.write(request); process.stdin.close()
        process.wait(timeout=timeout)
    except BaseException:
        try: process.kill()
        except OSError: pass
        process.wait()
        raise
    finally:
        for reader in readers: reader.join()
    if errors: raise errors[0]
    if process.returncode: raise subprocess.CalledProcessError(process.returncode, arguments, output=bytes(buffers[0]))
    return bytes(buffers[0])


def local_endpoint(value):
    if not isinstance(value, str) or any(c in value for c in ("?", "#", "\x00", "\r", "\n")):
        raise ValueError("unsupported_context")
    if value.startswith("unix:///") or re.fullmatch(r"npipe:/+\./pipe/[A-Za-z0-9._-]+", value):
        return value
    raise ValueError("unsupported_context")


def parse_containers(rows):
    candidates = {}
    if not isinstance(rows, list): raise ValueError("invalid_inventory")
    for row in rows:
        if not isinstance(row, dict): continue
        service = row.get("Service")
        if service not in SERVICES: continue
        try: identity = container_id(row.get("ID"))
        except ValueError: identity = None
        candidates.setdefault(service, []).append(identity)
    counts = Counter(identity for ids in candidates.values() for identity in ids if identity is not None)
    return {service: ids[0] if len(ids) == 1 and ids[0] is not None and counts[ids[0]] == 1 else None
            for service, ids in candidates.items()}


def fetch_stats(endpoint, identity, factory=None):
    local_endpoint(endpoint); container_id(identity)
    if factory is None:
        import docker
        factory = docker.APIClient
    client = factory(base_url=endpoint, version="1.44", timeout=5)
    client.trust_env = False
    try:
        response = client.get(client.base_url + "/v1.44/containers/" + identity + "/stats",
                              params={"stream": "false", "one-shot": "true"}, stream=True, timeout=5)
        try:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(8192):
                if len(content) + len(chunk) > 1024 ** 2: raise ValueError("stats_too_large")
                content.extend(chunk)
            return strict_json(bytes(content))
        finally: response.close()
    finally: client.close()


def sample_child():
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384: raise ValueError("request_too_large")
    request = strict_json(raw)
    endpoint = local_endpoint(request["endpoint"])
    containers = request["containers"]
    if not isinstance(containers, dict) or not set(containers) <= set(SERVICES): raise ValueError("invalid_inventory")
    for identity in containers.values(): container_id(identity)
    def fetch(item):
        service, identity = item
        try:
            value = fetch_stats(endpoint, identity)
            memory = value.get("memory_stats", {})
            stats = memory.get("stats", {})
            clean = {"id": value.get("id"), "read": value.get("read"), "cpu_stats": {
                "cpu_usage": {"total_usage": value.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage")}},
                "memory_stats": {"usage": memory.get("usage"), "limit": memory.get("limit"),
                                 "stats": {key: stats[key] for key in ("inactive_file", "total_inactive_file", "cache") if key in stats}},
                "blkio_stats": {"io_service_bytes_recursive": value.get("blkio_stats", {}).get("io_service_bytes_recursive")}}
            return service, clean
        except Exception:
            return service, None  # No raw error/URL/configuration is exported.
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = dict(pool.map(fetch, containers.items()))
    sys.stdout.write(json.dumps(result, allow_nan=False, separators=(",", ":")))


def ensure_runtime():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    python = RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirements = ROOT / "requirements-resources.lock.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = RUNTIME / "requirements.sha256"
    with exclusive_lock(DIRECTORY / "setup.lock"):
        if not python.is_file():
            run_command([sys.executable, "-m", "venv", str(RUNTIME)], timeout=120)
        if not marker.is_file() or marker.read_text(encoding="ascii") != digest:
            print("Preparando SDK Docker no ambiente isolado do coletor...", flush=True)
            run_command([str(python), "-m", "pip", "--isolated", "install", "--index-url", "https://pypi.org/simple",
                         "--disable-pip-version-check", "--quiet", "--require-hashes", "-r", str(requirements)], timeout=180)
            marker.write_text(digest, encoding="ascii")
    return python


def inspect_states(identities):
    if not identities: return {}
    template = '{"id":{{json .Id}},"boot":{{json .State.StartedAt}},"running":{{json .State.Running}}}'
    try:
        data = run_command(["docker", "inspect", "--format", template, *identities], timeout=5)
    except subprocess.CalledProcessError as error:
        data = error.output or b""  # Other IDs may still have been inspected successfully.
    rows = [strict_json(line) for line in data.splitlines() if line.strip()]
    return {row["id"]: row for row in rows if row.get("id") in identities and type(row.get("running")) is bool}


def collect_once(python, previous):
    rows = {name: unavailable() for name in SERVICES}
    try:
        endpoint = local_endpoint(strict_json(run_command(["docker", "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"], timeout=5)))
        template = '{"Service":{{json (.Label "com.docker.compose.service")}},"ID":{{json .ID}}}'
        data = run_command(["docker", "ps", "-a", "--no-trunc", "--filter", "label=com.docker.compose.project=aularedes", "--format", template], timeout=5)
        document = strict_json(data) if data.lstrip().startswith(b"[") else [strict_json(line) for line in data.splitlines() if line.strip()]
        containers = parse_containers(document)
        before = inspect_states([identity for identity in containers.values() if identity is not None])
        running = {s: identity for s, identity in containers.items() if identity in before and before[identity]["running"]}
        request = json.dumps({"endpoint": endpoint, "containers": running}).encode()
        result = strict_json(run_command([str(python), str(Path(__file__).resolve()), "--sample"], timeout=15, request=request))
        after = inspect_states(list(running.values()))
        for service in SERVICES:
            identity = containers.get(service)
            if service in containers and identity is None:
                rows[service] = unavailable("ambiguous_container"); previous.pop(service, None); continue
            if identity not in running.values():
                rows[service] = unavailable("container_not_running"); previous.pop(service, None); continue
            if before[identity] != after.get(identity):
                rows[service] = unavailable("container_changed"); previous.pop(service, None); continue
            try:
                rows[service], previous[service] = measure(identity, before[identity]["boot"], result.get(service), previous.get(service), time.time())
            except (ValueError, TypeError, AttributeError, KeyError):
                rows[service] = unavailable("invalid_stats"); previous.pop(service, None)
    except (OSError, ValueError, subprocess.SubprocessError, KeyError, TypeError):
        previous.clear()
    value = {"schema_version": 1, "sampled_at": time.time(), "services": rows}
    validate_snapshot(value)
    if len(json.dumps(value).encode()) > MAX_BYTES: raise ValueError("snapshot_too_large")
    atomic_json(DIRECTORY / "snapshot.json", value)
    return value


def launch_background(stop):
    # --stop acknowledges a request, not process termination. Never lose a restart
    # by treating the still-exiting process as an already healthy collector.
    until = time.monotonic() + 45
    while True:
        try:
            with exclusive_lock(DIRECTORY / "worker.lock"): pass
            break
        except RuntimeError as error:
            if str(error) != "worker_already_running": raise
            if not stop.exists(): return False
            if time.monotonic() >= until: raise TimeoutError("resource_worker_stop_timeout")
            time.sleep(.2)
    with (DIRECTORY / "worker.log").open("ab") as log:
        creation = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watch"], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, **creation)
    until = time.monotonic() + 10
    while time.monotonic() < until:
        try:
            with exclusive_lock(DIRECTORY / "worker.lock"): pass
        except RuntimeError as error:
            if str(error) != "worker_already_running": raise
            if not stop.exists(): return True
        if process.poll() is not None: raise RuntimeError("resource_worker_start_failed")
        time.sleep(.1)
    raise TimeoutError("resource_worker_start_timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--background", action="store_true")
    flags.add_argument("--watch", action="store_true")
    flags.add_argument("--stop", action="store_true")
    flags.add_argument("--sample", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.sample:
        sample_child(); return
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    stop = DIRECTORY / "stop.request"
    if options.stop:
        stop.write_text("stop", encoding="ascii"); print("Encerramento solicitado ao coletor de recursos."); return
    python = ensure_runtime()
    try:
        if options.background:
            started = launch_background(stop)
            print("Coletor de recursos iniciado em segundo plano." if started else "Já existe um coletor de recursos para esta pasta.")
            return
        with exclusive_lock(DIRECTORY / "worker.lock"):
            stop.unlink(missing_ok=True)
            previous = {}
            while True:
                try: collect_once(python, previous)
                except OSError: previous.clear()  # A transient Windows rename failure must not stop collection.
                if not options.watch: break
                for _ in range(5):
                    if stop.exists(): return
                    time.sleep(1)
    except RuntimeError as error:
        if str(error) != "worker_already_running": raise
        print("Já existe um coletor de recursos para esta pasta.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    main()
