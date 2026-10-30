import copy
import json
import time

import pytest

IMAGE="sha256:"+"a"*64
OTHER="sha256:"+"b"*64


def documents(now=1000):
    source={"type":"image","target":{"imageID":IMAGE}}
    sbom={"source":{"type":"image","metadata":{"imageID":IMAGE}},"artifacts":[{"id":"pkg-1","name":"sample","version":"1.0","type":"python"}]}
    match={"vulnerability":{"id":"CVE-2099-1234","severity":"High","dataSource":"https://nvd.nist.gov/vuln/detail/CVE-2099-1234","fix":{"versions":["1.1"],"state":"fixed"}},"artifact":{"id":"pkg-1","name":"sample","version":"1.0","type":"python"}}
    raw={"source":source,"matches":[match],"descriptor":{"name":"grype","version":"0.121.0","db":{"status":{"valid":True,"built":"1970-01-01T00:10:00Z"}}}}
    return sbom,raw


def report(now=1000):
    from backend.app.vulnerability_report import normalize_report
    sbom,raw=documents(now)
    return normalize_report(raw,sbom,IMAGE,now)


def fixture_source(tmp_path,now=1000):
    root=tmp_path/"reports";root.mkdir()
    inventory={"schema_version":1,"checked_at":now,"ok":True,"services":{key:{"image_id":IMAGE,"running":True} for key in ["web-demo","postgres","dns","smtp"]},"attempts":{IMAGE:{"status":"completed","at":now,"error":None}}}
    (root/"inventory.json").write_text(json.dumps(inventory))
    (root/("a"*64+".json")).write_text(json.dumps(report(now)))
    return root,inventory


def test_normalizer_deduplicates_and_keeps_highest_severity_and_fixes():
    from backend.app.vulnerability_report import normalize_report
    sbom,raw=documents();duplicate=copy.deepcopy(raw["matches"][0])
    duplicate["vulnerability"].update(severity="Critical",fix={"versions":["1.2"],"state":"fixed"})
    raw["matches"].append(duplicate)
    value=normalize_report(raw,sbom,IMAGE,1000)
    assert value["package_count"]==1 and len(value["findings"])==1
    assert value["counts"]["critical"]==1 and value["counts"]["high"]==0
    assert value["findings"][0]["fixed_versions"]==["1.1","1.2"]
    assert "configuration" not in str(value) and "locations" not in str(value)


def test_empty_matches_require_real_inventory_and_unknown_severity_is_not_lost():
    from backend.app.vulnerability_report import normalize_report
    sbom,raw=documents();raw["matches"] = []
    assert sum(normalize_report(raw,sbom,IMAGE,1000)["counts"].values())==0
    sbom["artifacts"]=[]
    with pytest.raises(ValueError):normalize_report(raw,sbom,IMAGE,1000)
    sbom,raw=documents();raw["matches"][0]["vulnerability"].update(severity="new-level",dataSource="javascript:alert(1)")
    value=normalize_report(raw,sbom,IMAGE,1000)
    assert value["counts"]["unknown"]==1 and value["findings"][0]["url"] is None


def test_oci_index_identity_and_config_digest_are_distinct_and_both_verified():
    from backend.app.vulnerability_report import normalize_report
    sbom,raw=documents()
    value=normalize_report(raw,sbom,OTHER,1000,expected_config=IMAGE)
    assert value["image_id"]==OTHER and value["config_id"]==IMAGE
    with pytest.raises(ValueError):normalize_report(raw,sbom,OTHER,1000,expected_config=OTHER)


@pytest.mark.parametrize("failure",["mismatched_image","invalid_db","missing_matches","unknown_package","future_db"])
def test_invalid_scanner_reports_are_rejected(failure):
    from backend.app.vulnerability_report import normalize_report
    sbom,raw=documents()
    if failure=="mismatched_image":raw["source"]={"type":"image","target":{"imageID":OTHER}}
    elif failure=="invalid_db":raw["descriptor"]["db"]["status"]["valid"]=False
    elif failure=="missing_matches":del raw["matches"]
    elif failure=="unknown_package":raw["matches"][0]["artifact"]["id"]="not-in-inventory"
    else:raw["descriptor"]["db"]["status"]["built"]="2099-01-01T00:00:00Z"
    with pytest.raises(ValueError):normalize_report(raw,sbom,IMAGE,1000)


def test_monitor_pages_fresh_results_without_cve_or_image_metric_labels(tmp_path):
    from backend.app.vulnerabilities import VulnerabilityMonitor
    from prometheus_client import generate_latest
    now=time.time();root,_=fixture_source(tmp_path,now)
    # Refresh database timestamp for a genuinely current report.
    path=root/("a"*64+".json");value=json.loads(path.read_text());value["db_built_at"]=now-60;path.write_text(json.dumps(value))
    monitor=VulnerabilityMonitor(root);monitor.sample(now=now)
    overview=monitor.overview(now=now)
    assert len(overview["services"])==4 and all(row["status"]=="warning" for row in overview["services"])
    assert overview["findings"]["total"]==1 and overview["findings"]["items"][0]["id"]=="CVE-2099-1234"
    metrics=generate_latest(monitor.registry).decode()
    assert 'security_vulnerability_analysis_success{service="dns"} 1.0' in metrics
    assert "CVE-" not in metrics and IMAGE not in metrics and "sample" not in metrics


@pytest.mark.parametrize("failure",["inventory_stale","scan_stale","db_stale","future","mismatched_image","worker_failure","malformed","empty_packages","counts_tampered"])
def test_unavailable_reports_never_publish_a_healthy_zero(tmp_path,failure):
    from backend.app.vulnerabilities import VulnerabilityMonitor
    now=1000;root,inventory=fixture_source(tmp_path,now)
    path=root/("a"*64+".json");value=json.loads(path.read_text())
    if failure=="inventory_stale":inventory["checked_at"]=now-121
    elif failure=="scan_stale":value["scanned_at"]=now-86401
    elif failure=="db_stale":value["db_built_at"]=now-120*3600-1
    elif failure=="future":value["scanned_at"]=now+10
    elif failure=="mismatched_image":value["image_id"]=OTHER
    elif failure=="worker_failure":inventory["attempts"][IMAGE]={"status":"failed","at":now,"error":"scanner_failed"}
    elif failure=="empty_packages":value["package_count"]=0
    elif failure=="counts_tampered":value["counts"]["high"]=0
    (root/"inventory.json").write_text(json.dumps(inventory));path.write_text("invalid json" if failure=="malformed" else json.dumps(value))
    monitor=VulnerabilityMonitor(root);monitor.sample(now=now)
    assert all(row["status"]=="unknown" and row["counts"] is None for row in monitor.overview(now=now)["services"])


def test_routes_require_login_and_invalid_filters_are_rejected(tmp_path):
    from backend.tests.auth_helpers import authenticated_app,AuthenticatedClient
    from backend.app.config import Settings
    with AuthenticatedClient(authenticated_app(Settings(database_path=tmp_path/"events.sqlite",enable_probe=False))) as client:
        response=client.get("/api/security/vulnerabilities")
        assert response.status_code==200 and response.json()["enabled"] is False
        assert client.get("/api/security/vulnerabilities?service=external").status_code==422
        assert client.get("/api/security/vulnerabilities?page=0").status_code==422
        assert client.post("/api/security/vulnerabilities").status_code==405
