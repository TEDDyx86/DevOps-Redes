import asyncio
import logging
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

from .integrity_files import observe_file


FILES={
    "http-runtime":{"service":"web-demo","name":"HTTP","path":"http.json"},
    "postgres-runtime":{"service":"postgres","name":"PostgreSQL","path":"postgres/postgresql.conf"},
    "dns-corefile":{"service":"dns","name":"DNS","path":"dns/Corefile"},
    "dns-zone":{"service":"dns","name":"Zona DNS","path":"dns/db.aularedes.test"},
    "smtp-runtime":{"service":"smtp","name":"SMTP","path":"smtp.json"},
    "prometheus":{"service":"monitoring","name":"Prometheus","path":"prometheus.yml"},
    "alert-rules":{"service":"monitoring","name":"Regras de alerta","path":"alerts.yml"},
    "alertmanager":{"service":"monitoring","name":"Alertmanager","path":"alertmanager.yml"},
}


class IntegrityMonitor:
    def __init__(self,path,root=None):
        self.path=Path(path)
        self.root=Path(root) if root is not None else None
        self.lock=threading.RLock();self.snapshot={}
        self.initialized=False
        self.references={key:{"approved_sha256":None,"approved_at":None,"approved_by":None} for key in FILES}
        self.registry=CollectorRegistry();self.registry.register(self)
        try:self.initialize()
        except (sqlite3.Error,OSError):
            logging.error("Armazenamento de integridade indisponível; será verificado novamente")

    def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS integrity_files (
                    id TEXT PRIMARY KEY, approved_sha256 TEXT, approved_at REAL, approved_by TEXT,
                    status TEXT, observed_sha256 TEXT, checked_at REAL, reason TEXT);
                CREATE TABLE IF NOT EXISTS integrity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, file_id TEXT NOT NULL,
                    kind TEXT NOT NULL, old_sha256 TEXT, new_sha256 TEXT, actor TEXT);
            """)
            for key in FILES:
                db.execute("INSERT OR IGNORE INTO integrity_files(id) VALUES (?)",(key,))
            refs={row["id"]:dict(row) for row in db.execute("SELECT * FROM integrity_files")}
        self.references=refs
        self.initialized=True

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    @staticmethod
    def record(db,now,key,kind,old_hash,new_hash,actor=None):
        number=db.execute("INSERT INTO integrity_events(at,file_id,kind,old_sha256,new_sha256,actor) VALUES (?,?,?,?,?,?)",(now,key,kind,old_hash,new_hash,actor)).lastrowid
        db.execute("DELETE FROM integrity_events WHERE id<=? OR at<?",(number-10000,now-7*86400))

    @staticmethod
    def classify(observation,reference):
        if observation["status"]!="readable":return observation["status"]
        if reference is None:return "unapproved"
        return "ok" if observation["sha256"]==reference else "changed"

    def sample(self,now=None):
        now=time.time() if now is None else now
        if self.root is None:return
        with self.lock:
            if not self.initialized:self.initialize()
            self._sample(now)

    def _sample(self,now):
        with self.connect() as db:
            refs={row["id"]:dict(row) for row in db.execute("SELECT * FROM integrity_files")}
            snapshot={}
            db.execute("DELETE FROM integrity_events WHERE at<?",(now-7*86400,))
            for key,item in FILES.items():
                observation=observe_file(self.root,item["path"])
                old=refs[key];status=self.classify(observation,old["approved_sha256"])
                digest=observation["sha256"]
                if (old["status"],old["observed_sha256"])!=(status,digest):
                    kind="restored" if status=="ok" and old["status"] is not None else "observed" if status in {"ok","unapproved"} else status
                    self.record(db,now,key,kind,old["observed_sha256"],digest)
                db.execute("UPDATE integrity_files SET status=?,observed_sha256=?,checked_at=?,reason=? WHERE id=?",(status,digest,now,observation["reason"],key))
                snapshot[key]={"status":status,"observed_sha256":digest,"checked_at":now,"reason":observation["reason"]}
            db.commit()
            self.references,self.snapshot=refs,snapshot

    def approve(self,items,actor,now=None):
        now=time.time() if now is None else now
        if self.root is None:raise ValueError("Monitor de arquivos não configurado.")
        keys=[item["file_id"] for item in items]
        if not 1<=len(items)<=len(FILES) or len(set(keys))!=len(keys) or any(key not in FILES for key in keys):
            raise ValueError("Selecione somente arquivos permitidos, sem IDs repetidos.")
        if any(re.fullmatch(r"[0-9a-f]{64}",item.get("observed_sha256","")) is None for item in items):
            raise ValueError("Hash observado inválido.")
        with self.lock:
            if not self.initialized:self.initialize()
            self._approve(items,actor,now)

    def _approve(self,items,actor,now):
        with self.connect() as db:
            observations={}
            for item in items:
                key=item["file_id"];observed=observe_file(self.root,FILES[key]["path"])
                if observed["status"]!="readable" or observed["sha256"]!=item["observed_sha256"]:
                    raise ValueError("O arquivo mudou ou não pode ser lido. Atualize e revise o hash novamente.")
                observations[key]=observed
            for key,observation in observations.items():
                old=db.execute("SELECT * FROM integrity_files WHERE id=?",(key,)).fetchone()
                if old["approved_sha256"]!=observation["sha256"]:
                    self.record(db,now,key,"approved",old["approved_sha256"],observation["sha256"],actor)
                    db.execute("UPDATE integrity_files SET approved_sha256=?,approved_at=?,approved_by=? WHERE id=?",(observation["sha256"],now,actor,key))
                db.execute("UPDATE integrity_files SET status='ok',observed_sha256=?,checked_at=?,reason=NULL WHERE id=?",(observation["sha256"],now,key))
            refs={row["id"]:dict(row) for row in db.execute("SELECT * FROM integrity_files")}
            db.commit()
            self.references=refs
            for key,observation in observations.items():
                self.snapshot[key]={"status":"ok","observed_sha256":observation["sha256"],"checked_at":now,"reason":None}

    def overview(self,now=None,include_events=True):
        now=time.time() if now is None else now
        with self.lock:
            files=[]
            for key,item in FILES.items():
                ref=self.references[key];sample=self.snapshot.get(key,{})
                checked=sample.get("checked_at");fresh=checked is not None and -5<=now-checked<=20
                files.append({"id":key,**item,"status":sample.get("status","unknown") if fresh else "unknown",
                              "observed_sha256":sample.get("observed_sha256") if fresh else None,
                              "checked_at":checked,"reason":sample.get("reason") if fresh else "not_checked" if self.root else "not_configured",
                              "approved_sha256":ref["approved_sha256"],"approved_at":ref["approved_at"],"approved_by":ref["approved_by"]})
            events=[]
            if include_events:
                with self.connect() as db:
                    events=[dict(row) for row in db.execute("SELECT * FROM integrity_events WHERE at>=? ORDER BY id DESC LIMIT 100",(now-7*86400,))]
        return {"enabled":self.root is not None,"generated_at":now,"files":files,"events":events}

    def collect(self):
        yield GaugeMetricFamily("security_config_monitor_enabled","File monitor configured",value=int(self.root is not None))
        if self.root is None:return
        rows=self.overview(include_events=False)["files"]
        fields={"check_success":lambda row:int(row["status"] in {"ok","changed","unapproved","missing"}),
                "baseline_ready":lambda row:int(row["approved_sha256"] is not None),
                "readable":lambda row:int(row["observed_sha256"] is not None),
                "changed":lambda row:1 if row["status"] in {"changed","missing"} else 0 if row["status"]=="ok" else None}
        for field,get_value in fields.items():
            metric=GaugeMetricFamily(f"security_config_{field}",field,labels=["file_id","service"])
            for row in rows:
                value=get_value(row)
                if value is not None:metric.add_metric([row["id"],row["service"]],value)
            yield metric

    async def run(self):
        while True:
            try:await asyncio.to_thread(self.sample)
            except (sqlite3.Error,OSError):
                logging.error("Verificação de configurações indisponível; repetindo no próximo ciclo")
                with self.lock:self.snapshot={}
            await asyncio.sleep(5)
