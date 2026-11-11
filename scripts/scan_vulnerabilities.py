"""Local image inventory + isolated Syft/Grype worker. No credentials or Docker socket in scanners."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.vulnerability_report import SERVICES, MAX_REPORT_BYTES, image_id, normalize_report, strict_json, timestamp, validate_report

GRYPE = "anchore/grype:v0.121.0@sha256:621d56d1d68106b787022c81546f7e0a36202a25d1239f0c20195fab8c16f7ea"
SYFT = "anchore/syft:v1.55.0@sha256:4cc92b64ca74ffca4c94d4c8fcc01f217731375300be14d0b6eeb2e82eaa110a"
CACHE = "aularedes-vulnerability-cache"
MAX_RAW_BYTES = 32 * 1024 * 1024


@contextmanager
def exclusive_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("worker_already_running") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def atomic_json(path, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(content) > MAX_REPORT_BYTES:
        raise ValueError("report_too_large")
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        # A concurrent reader on Windows blocks os.replace with PermissionError;
        # readers hold the file for milliseconds, so retry briefly before failing.
        for attempt in range(50):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 49:
                    raise
                time.sleep(0.1)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path, limit=MAX_RAW_BYTES):
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("report_too_large")
    return strict_json(content)


def archive_config_id(path):
    """Hash the single exported config, reading members without extracting any paths."""
    with tarfile.open(path, "r") as archive:
        manifest = archive.getmember("manifest.json")
        if not manifest.isfile() or manifest.size > 65536:
            raise ValueError("invalid_archive_manifest")
        document = strict_json(archive.extractfile(manifest).read(65537))
        if not isinstance(document, list) or len(document) != 1:
            raise ValueError("ambiguous_archive")
        config = archive.getmember(document[0]["Config"])
        if not config.isfile() or config.size > 2 * 1024 * 1024:
            raise ValueError("invalid_archive_config")
        content = archive.extractfile(config).read(2 * 1024 * 1024 + 1)
        return "sha256:" + hashlib.sha256(content).hexdigest()


class Worker:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.output = self.root / ".runtime" / "vulnerabilities"
        self.work = self.root / ".runtime" / "vulnerability-work"
        self.output.mkdir(parents=True, exist_ok=True)
        self.work.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.inventory = {key: {"image_id": None, "running": False} for key in SERVICES}
        self.inventory_at = time.time()
        self.inventory_ok = False
        self.attempts = {}
        self.active_containers = set()
        self.active_processes = set()
        self.stopping = threading.Event()
        self.thread = None
        self.load_attempts()

    def load_attempts(self):
        try:
            value = read_json(self.output / "inventory.json", 65536)
            attempts = value["attempts"]
            if not isinstance(attempts, dict) or len(attempts) > 16:
                return
            for identity, attempt in attempts.items():
                image_id(identity)
                at = timestamp(attempt["at"])
                if at > time.time() + 5 or attempt["status"] not in {"failed", "completed", "running"}:
                    continue
                status = "failed" if attempt["status"] == "running" else attempt["status"]
                self.attempts[identity] = {"status": status, "at": at, "error": "scanner_failed" if status == "failed" else None}
        except (OSError, ValueError, KeyError, TypeError):
            self.attempts = {}

    def command(self, arguments, timeout=30, stdout=None):
        buffers = [bytearray(), bytearray()]
        errors = []
        flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        with self.lock:
            if self.stopping.is_set():
                raise RuntimeError("worker_stopping")
            process = subprocess.Popen(arguments, cwd=self.root, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, **flags)
            self.active_processes.add(process)

        def consume(pipe, index, limit, destination=None):
            size = 0
            try:
                while chunk := pipe.read(4096):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("output_too_large")
                    if destination is None:
                        buffers[index].extend(chunk)
                    else:
                        destination.write(chunk)
            except (OSError, ValueError) as error:
                errors.append(error)
                try: process.kill()
                except OSError: pass
            finally:
                pipe.close()

        readers = [threading.Thread(target=consume, args=(process.stdout, 0, MAX_RAW_BYTES, stdout)),
                   threading.Thread(target=consume, args=(process.stderr, 1, 65536))]
        for reader in readers:
            reader.start()
        try:
            try:
                process.wait(timeout=timeout)
            except BaseException:
                try: process.kill()
                except OSError: pass
                process.wait()
                raise
            finally:
                for reader in readers:
                    reader.join()
            if errors:
                raise errors[0]
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, arguments, bytes(buffers[0]), bytes(buffers[1]))
            return subprocess.CompletedProcess(arguments, process.returncode, bytes(buffers[0]), bytes(buffers[1]))
        finally:
            with self.lock:
                self.active_processes.discard(process)

    def shutdown(self):
        with self.lock:
            self.stopping.set()
            processes = list(self.active_processes)
            names = list(self.active_containers)
        for process in processes:
            if process.poll() is None:
                try: process.kill()
                except OSError: pass
        for name in names:
            self.remove_container(name)
        # Keep the checkout lock until export/scanner commands and file readers finish.
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join()

    def discover(self):
        inventory = {}
        for service in SERVICES:
            ids = self.command(["docker", "compose", "ps", "-a", "-q", service], timeout=10).stdout.decode().split()
            if len(ids) != 1:
                inventory[service] = {"image_id": None, "running": False}
                continue
            if not all(char in "0123456789abcdef" for char in ids[0]) or len(ids[0]) != 64:
                raise ValueError("invalid_container")
            template = '{"image_id":{{json .Image}},"running":{{json .State.Running}}}'
            item = strict_json(self.command(["docker", "inspect", "--format", template, ids[0]], timeout=10).stdout)
            image_id(item["image_id"])
            if type(item["running"]) is not bool:
                raise ValueError("invalid_container")
            inventory[service] = {"image_id": item["image_id"], "running": item["running"]}
        with self.lock:
            self.inventory, self.inventory_at, self.inventory_ok = inventory, time.time(), True
            current = {item["image_id"] for item in inventory.values()}
            self.attempts = {key: item for key, item in self.attempts.items() if key in current}
            self.publish()

    def publish(self):
        with self.lock:
            atomic_json(self.output / "inventory.json", {"schema_version": 1, "checked_at": self.inventory_at,
                "ok": self.inventory_ok, "services": self.inventory, "attempts": self.attempts})

    def scanner_command(self, tool, source=None, network="none"):
        if tool not in (GRYPE, SYFT) or network not in ("none", "bridge"):
            raise ValueError("invalid_scanner")
        name = "aularedes-scan-" + uuid.uuid4().hex
        command = ["docker", "run", "--rm", "--name", name, "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--cpus", "2", "--memory", "2g", "--network", network,
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m", "-e", "GRYPE_CHECK_FOR_APP_UPDATE=false", "-e", "SYFT_CHECK_FOR_APP_UPDATE=false"]
        if tool == GRYPE:
            command += ["-v", CACHE + ":/cache", "-e", "GRYPE_DB_CACHE_DIR=/cache",
                "-e", "GRYPE_DB_AUTO_UPDATE=false", "-e", "GRYPE_DB_MAX_ALLOWED_BUILT_AGE=120h"]
        if source is not None:
            source = Path(source)
            if source.is_symlink() or source.parent.resolve() != self.work.resolve() or not source.is_file():
                raise ValueError("invalid_input")
            command += ["--mount", f"type=bind,source={source.resolve()},target=/input/source,readonly"]
        command.append(tool)
        return command

    def run_scanner(self, tool, args, source=None, output=None, network="none", timeout=600):
        command = self.scanner_command(tool, source, network)
        name = command[command.index("--name") + 1]
        with self.lock:
            if self.stopping.is_set():
                raise RuntimeError("worker_stopping")
            self.active_containers.add(name)
        try:
            if output is None:
                self.command(command + args, timeout=timeout)
            else:
                with output.open("wb") as stream:
                    self.command(command + args, timeout=timeout, stdout=stream)
                if output.stat().st_size > MAX_RAW_BYTES:
                    raise ValueError("report_too_large")
        finally:
            self.remove_container(name)
            with self.lock:
                self.active_containers.discard(name)

    def remove_container(self, name):
        try:
            flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
            subprocess.run(["docker", "rm", "-f", name], cwd=self.root, timeout=20,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, shell=False, **flags)
        except (subprocess.SubprocessError, OSError):
            pass

    def update_database(self):
        # Only the database updater has network access. It has no image or SBOM mount.
        self.run_scanner(GRYPE, ["db", "update"], network="bridge", timeout=600)

    def scan_image(self, identity):
        image_id(identity)
        stem = identity[7:]
        archive, sbom_path, raw_path = [self.work / (stem + suffix) for suffix in (".tar", ".sbom.json", ".raw.json")]
        try:
            size = int(self.command(["docker", "image", "inspect", "--format", "{{.Size}}", identity]).stdout)
            if not 0 < size <= 1024 ** 3:
                raise ValueError("image_too_large")
            self.command(["docker", "image", "save", "-o", str(archive), identity], timeout=180)
            if archive.stat().st_size > 2 * 1024 ** 3:
                raise ValueError("archive_too_large")
            self.run_scanner(SYFT, ["docker-archive:/input/source", "-o", "syft-json"], archive, sbom_path)
            self.run_scanner(GRYPE, ["sbom:/input/source", "-o", "json"], sbom_path, raw_path)
            result = normalize_report(read_json(raw_path), read_json(sbom_path), identity, time.time(), expected_config=archive_config_id(archive))
            atomic_json(self.output / (stem + ".json"), result)
            print(f"Análise concluída: {stem[:12]} · {result['package_count']} pacotes · {sum(result['counts'].values())} achados", flush=True)
        finally:
            # Exact task-owned paths only; no recursive deletion of computed directories.
            for path in (archive, sbom_path, raw_path):
                if path.parent.resolve() == self.work.resolve():
                    path.unlink(missing_ok=True)

    def scan_batch(self, identities):
        try:
            self.update_database()
        except (subprocess.SubprocessError, OSError, ValueError, RuntimeError):
            with self.lock:
                self.attempts.update({key: {"status": "failed", "at": time.time(), "error": "database_update_failed"} for key in identities})
                self.publish()
            print("Atualização da base indisponível; nova tentativa em 5 min.", flush=True)
            return
        for identity in identities:
            if self.stopping.is_set():
                break
            with self.lock:
                self.attempts[identity] = {"status": "running", "at": time.time(), "error": None}
                self.publish()
            try:
                self.scan_image(identity)
                attempt = {"status": "completed", "at": time.time(), "error": None}
            except (subprocess.SubprocessError, OSError, ValueError, RuntimeError):
                attempt = {"status": "failed", "at": time.time(), "error": "scanner_failed"}
                traceback.print_exc()
                print("Análise indisponível; resultado anterior preservado e nova tentativa em 5 min.", flush=True)
            with self.lock:
                self.attempts[identity] = attempt
                self.publish()

    def due_images(self, force=False):
        now = time.time()
        due = []
        with self.lock:
            identities = sorted({item["image_id"] for item in self.inventory.values()} - {None})
            for identity in identities:
                attempt = self.attempts.get(identity, {})
                if not force and attempt.get("status") == "failed" and now - attempt["at"] < 300:
                    continue
                try:
                    report = validate_report(read_json(self.output / (identity[7:] + ".json"), MAX_REPORT_BYTES))
                    if (not force and attempt.get("status") != "failed" and report["image_id"] == identity
                            and -5 <= now - report["scanned_at"] < 21600 and -5 <= now - report["db_built_at"] <= 120 * 3600):
                        continue
                except (OSError, ValueError, KeyError, TypeError):
                    pass
                due.append(identity)
        return due

    def run(self, watch=False):
        stop_file = self.output / "stop.request"
        with exclusive_lock(self.output / "worker.lock"):
            stop_file.unlink(missing_ok=True)
            try:
                while not self.stopping.is_set():
                    try:
                        self.discover()
                    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
                        with self.lock:
                            self.inventory_ok = False
                            self.publish()
                        print("Inventário Docker indisponível; verificando novamente em 30 s.", flush=True)
                    if self.inventory_ok and (self.thread is None or not self.thread.is_alive()):
                        due = self.due_images(force=not watch)
                        if due:
                            self.thread = threading.Thread(target=self.scan_batch, args=(due,))
                            self.thread.start()
                    if not watch:
                        while self.thread and self.thread.is_alive():
                            self.thread.join(timeout=20)
                            self.discover()
                        return
                    if stop_file.exists():
                        return
                    self.stopping.wait(30)
            finally:
                self.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--watch", action="store_true", help="Inventário contínuo e análise a cada seis horas")
    group.add_argument("--background", action="store_true", help="Iniciar watch oculto (usa a trava do checkout)")
    group.add_argument("--stop", action="store_true", help="Solicitar encerramento do watch deste checkout")
    options = parser.parse_args()
    worker = Worker()
    if options.stop:
        (worker.output / "stop.request").write_text("stop", encoding="ascii")
        print("Encerramento solicitado; o monitor verifica o pedido a cada 30 s.")
        return
    try:
        if options.background:
            with exclusive_lock(worker.output / "worker.lock"):
                pass
            with (worker.output / "worker.log").open("ab") as log:
                flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
                subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watch"], cwd=ROOT,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, **flags)
            print("Monitor de vulnerabilidades iniciado em segundo plano.")
        else:
            worker.run(watch=options.watch)
    except RuntimeError as error:
        if str(error) != "worker_already_running":
            raise
        print("Já existe um monitor de vulnerabilidades para esta pasta.")
    except KeyboardInterrupt:
        print("Monitor de vulnerabilidades encerrado.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
