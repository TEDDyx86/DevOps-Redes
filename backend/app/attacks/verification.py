"""Leitura da API do Prometheus para verificar alertas em pending e firing."""


def live_alerts(client, base_url):
    response = client.get(
        base_url.rstrip("/") + "/api/v1/query",
        params={"query": "ALERTS"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError("prometheus_query_failed")
    firing = set()
    pending = set()
    details = []
    for item in payload.get("data", {}).get("result", []):
        metric = item.get("metric", {})
        name = metric.get("alertname")
        if not name:
            continue
        state = metric.get("alertstate", "firing")
        if state == "pending":
            pending.add(name)
        elif state == "firing":
            firing.add(name)
        details.append({
            "alertname": name,
            "alertstate": state,
            "service": metric.get("service", ""),
            "severity": metric.get("severity", ""),
        })
    return {
        "available": True,
        "firing": sorted(firing),
        "pending": sorted(pending - firing),
        "details": details,
    }


def summarize_live(expected, state):
    if state is None:
        return {"available": False, "pending": [], "fired": [], "missing": list(expected)}
    firing_set = set(state.get("firing", []))
    pending_set = set(state.get("pending", []))
    fired = [alert for alert in expected if alert in firing_set]
    pending = [alert for alert in expected if alert in pending_set and alert not in firing_set]
    missing = [alert for alert in expected if alert not in firing_set and alert not in pending_set]
    return {"available": True, "pending": pending, "fired": fired, "missing": missing}


def firing_alerts(client, base_url):
    response = client.get(
        base_url.rstrip("/") + "/api/v1/query",
        params={"query": 'ALERTS{alertstate="firing"}'},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError("prometheus_query_failed")
    return {
        item["metric"]["alertname"]
        for item in payload.get("data", {}).get("result", [])
        if "alertname" in item.get("metric", {})
    }


def verify(expected, firing):
    if firing is None:
        return {"available": False, "fired": [], "missing": list(expected)}
    return {
        "available": True,
        "fired": [alert for alert in expected if alert in firing],
        "missing": [alert for alert in expected if alert not in firing],
    }
