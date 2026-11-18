"""Leitura da API do Prometheus para verificar alertas em firing."""


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
