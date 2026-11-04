import subprocess

import pytest

from scripts.collect_resources import local_endpoint, fetch_stats, run_command, parse_containers


def test_local_context_only_and_service_inventory_is_unambiguous():
    assert local_endpoint("npipe:////./pipe/dockerDesktopLinuxEngine")
    assert local_endpoint("unix:///var/run/docker.sock")
    for endpoint in ("tcp://remote:2375", "ssh://user@host", "http://localhost:2375", "unix:///tmp/socket?secret"):
        with pytest.raises(ValueError): local_endpoint(endpoint)
    rows = [{"Service": "postgres", "ID": "a" * 64}, {"Service": "api", "ID": "b" * 64}]
    assert parse_containers(rows) == {"postgres": "a" * 64}
    assert parse_containers(rows + [rows[0]]) == {"postgres": None}


def test_ambiguous_service_is_isolated_in_actual_collection(tmp_path, monkeypatch):
    import json
    import sys
    from datetime import datetime, timezone
    from pathlib import Path
    from scripts import collect_resources as worker
    from backend.tests.test_resources import raw, BOOT
    identities = {name: str(i+1)*64 for i,name in enumerate(worker.SERVICES)}
    inventory = [{"Service":name,"ID":identity} for name,identity in identities.items()]
    inventory.append({"Service":"postgres","ID":"f"*64})
    def command(args, **kwargs):
        if args[:3] == ['docker','context','inspect']: return json.dumps('unix:///var/run/docker.sock').encode()
        if args[:2] == ['docker','ps']: return json.dumps(inventory).encode()
        request = json.loads(kwargs['request'])
        assert 'postgres' not in request['containers']
        result = {}
        for name, identity in request['containers'].items():
            data=raw(at=worker.time.time());data['id']=identity;result[name]=data
        return json.dumps(result).encode()
    monkeypatch.setattr(worker,'run_command',command)
    monkeypatch.setattr(worker,'inspect_states',lambda ids:{identity:{'id':identity,'boot':BOOT,'running':True} for identity in ids})
    monkeypatch.setattr(worker,'DIRECTORY',tmp_path)
    result=worker.collect_once(Path(sys.executable),{})
    assert result['services']['postgres']['error']=='ambiguous_container'
    assert all(result['services'][name]['source_ok'] for name in ('web-demo','dns','smtp'))


def test_disappeared_container_does_not_discard_other_inspect_results(monkeypatch):
    import json
    from scripts import collect_resources as worker
    output=json.dumps({'id':'a'*64,'boot':'1970-01-01T00:00:01Z','running':True}).encode()
    def missing(*args,**kwargs): raise subprocess.CalledProcessError(1,args,output=output)
    monkeypatch.setattr(worker,'run_command',missing)
    result=worker.inspect_states(['a'*64,'b'*64])
    assert set(result)=={'a'*64}


def test_fetch_is_bounded_get_for_fixed_identity_not_inspect_or_mutation():
    calls = []
    class Response:
        def raise_for_status(self): pass
        def iter_content(self, size): yield b'{"id":"' + b'a' * 64 + b'"}'
        def close(self): pass
    class Client:
        base_url = "http+docker://localnpipe"
        def __init__(self, **kwargs): calls.append(kwargs)
        def get(self, url, **kwargs): calls.append((url, kwargs)); return Response()
        def close(self): pass
    assert fetch_stats("npipe:////./pipe/dockerDesktopLinuxEngine", "a" * 64, Client)["id"] == "a" * 64
    url, options = calls[1]
    assert url.endswith('/v1.44/containers/'+ 'a'*64 + '/stats')
    assert options["stream"] and options["params"] == {"stream": "false", "one-shot": "true"}
    assert calls[0]["timeout"] == 5 and calls[0]["version"] == "1.44"


def test_command_output_limit_is_enforced_during_read_and_process_is_reaped():
    import sys
    with pytest.raises(ValueError, match="output_too_large"):
        run_command([sys.executable, '-c', 'import sys;sys.stdout.write("x"*100000)'], limit=1000)
    with pytest.raises(subprocess.TimeoutExpired):
        run_command([sys.executable, '-c', 'import time;time.sleep(10)'], timeout=.1)


def test_stats_body_limit_closes_response_and_client():
    closed = []
    class Response:
        def raise_for_status(self): pass
        def iter_content(self, size):
            for _ in range(150): yield b'x' * 8192
        def close(self): closed.append('response')
    class Client:
        base_url = "http+docker://localhost"
        def __init__(self, **kwargs): pass
        def get(self, *args, **kwargs): return Response()
        def close(self): closed.append('client')
    with pytest.raises(ValueError): fetch_stats('unix:///var/run/docker.sock', 'a'*64, Client)
    assert closed == ['response', 'client']


def test_background_restart_waits_for_pending_stop_before_launch(tmp_path, monkeypatch):
    import sys
    from contextlib import contextmanager
    from pathlib import Path
    from scripts import collect_resources as worker
    stop = tmp_path / 'stop.request'; stop.write_text('stop')
    lock_calls, launched = [], []
    @contextmanager
    def lock(path):
        lock_calls.append(path)
        if len(lock_calls) == 2: yield  # Old process has now exited.
        else: raise RuntimeError('worker_already_running')
    class Process:
        def __init__(self, *args, **kwargs):
            assert len(lock_calls) >= 2
            launched.append(args); stop.unlink()
        def poll(self): return None
    monkeypatch.setattr(worker,'DIRECTORY',tmp_path)
    monkeypatch.setattr(worker,'ensure_runtime',lambda:Path(sys.executable))
    monkeypatch.setattr(worker,'exclusive_lock',lock)
    monkeypatch.setattr(worker.subprocess,'Popen',Process)
    monkeypatch.setattr(worker.time,'sleep',lambda seconds:None)
    monkeypatch.setattr(sys,'argv',['collect_resources.py','--background'])
    worker.main()
    assert len(launched) == 1 and len(lock_calls) >= 3


def test_background_without_stop_keeps_existing_worker(tmp_path, monkeypatch):
    import sys
    from contextlib import contextmanager
    from pathlib import Path
    from scripts import collect_resources as worker
    @contextmanager
    def lock(path): raise RuntimeError('worker_already_running'); yield
    def launch(*args,**kwargs): raise AssertionError('Cannot launch duplicate worker')
    monkeypatch.setattr(worker,'DIRECTORY',tmp_path)
    monkeypatch.setattr(worker,'ensure_runtime',lambda:Path(sys.executable))
    monkeypatch.setattr(worker,'exclusive_lock',lock)
    monkeypatch.setattr(worker.subprocess,'Popen',launch)
    monkeypatch.setattr(sys,'argv',['collect_resources.py','--background'])
    worker.main()
