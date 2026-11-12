from demo.session import make_session, read_session


def test_session_roundtrip():
    token = make_session("admin", "demo-secret")
    assert read_session(token, "demo-secret") == "admin"


def test_session_rejects_bad_signature():
    token = make_session("admin", "demo-secret")
    assert read_session(token + "x", "demo-secret") is None
    assert read_session(token, "outra-chave") is None


def test_session_rejects_expired():
    token = make_session("admin", "demo-secret", ttl_seconds=-1)
    assert read_session(token, "demo-secret") is None


def test_session_rejects_garbage():
    assert read_session("", "demo-secret") is None
    assert read_session("sem-ponto", "demo-secret") is None
    assert read_session("###.fedcba", "demo-secret") is None
