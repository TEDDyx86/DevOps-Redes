import threading
import time

from backend.app.attacks.engine import Cancelled, Engine


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def verify_ok(expected, cancelled):
    assert callable(cancelled)
    return {"available": True, "fired": list(expected), "missing": []}


def make_engine(runner):
    return Engine(runners={"bruteforce-servico": runner}, verifier=verify_ok)


def test_fila_executa_um_ataque_por_vez_com_fases_e_verificacao():
    def runner(ctx, params):
        ctx.set_expected_alerts(["AutenticacaoServicoSuspeita"])
        ctx.log("executando")
        ctx.progress(tentativas=1)
    engine = make_engine(runner)
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: any(e.get("status") == "concluido" for e in engine.recent_events(500)))
    statuses = [e["status"] for e in engine.recent_events(500) if e["type"] == "status"]
    assert "agendado" in statuses and "executando" in statuses and "verificando" in statuses and "concluido" in statuses
    assert "executando" in [e["message"] for e in engine.recent_events(500) if e["type"] == "log"]
    historico = engine.snapshot()["history"]
    assert historico[0]["verification"]["fired"] == ["AutenticacaoServicoSuspeita"]
    assert historico[0]["counters"] == {"tentativas": 1}
    engine.stop()


def test_entrada_desconhecida_e_parametros_invalidos_sao_rejeitados():
    engine = make_engine(lambda ctx, params: None)
    try:
        engine.enqueue("ataque-inexistente")
        raise AssertionError("deveria falhar")
    except ValueError as error:
        assert "ataque_desconhecido" in str(error)
    try:
        engine.enqueue("bruteforce-servico", {"tentativas": 9999})
        raise AssertionError("deveria falhar")
    except ValueError as error:
        assert "parametro_fora_da_faixa" in str(error)
    engine.stop()


def test_cancelamento_da_fila_remove_entrada_sem_executar():
    executados = []
    liberar = threading.Event()

    def runner(ctx, params):
        executados.append(1)
        liberar.wait(timeout=10)

    engine = make_engine(runner)
    primeira = engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is not None
                    and engine.snapshot()["current"]["entry_id"] == primeira["entry_id"])
    segunda = engine.enqueue("bruteforce-servico")
    assert engine.cancel(segunda["entry_id"]) is not None
    assert engine.cancel(segunda["entry_id"]) is None
    assert engine.cancel("inexistente") is None
    assert engine.snapshot()["queue"] == []
    liberar.set()
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    assert len(executados) == 1
    engine.stop()


def test_interrupcao_do_ataque_em_execucao_resulta_em_interrompido():
    def runner(ctx, params):
        while not ctx.cancelled():
            ctx.progress(segundos=1)
            time.sleep(0.02)
        raise Cancelled()

    engine = make_engine(runner)
    entrada = engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is not None)
    engine.cancel(entrada["entry_id"])
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    assert engine.snapshot()["history"][0]["status"] == "interrompido"
    engine.stop()


def test_falha_do_runner_registra_tipo_do_erro_sem_expor_detalhes():
    def runner(ctx, params):
        raise RuntimeError("detalhe sensÃ­vel do erro")

    engine = make_engine(runner)
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: any(e.get("status") == "falhou" for e in engine.recent_events(500)))
    historico = engine.snapshot()["history"][0]
    assert historico["status"] == "falhou"
    assert historico["error"] == "RuntimeError"
    corpo = str(engine.recent_events(500))
    assert "detalhe sensÃ­vel" not in corpo
    engine.stop()


def test_subscribe_reproduz_eventos_anteriores():
    engine = make_engine(lambda ctx, params: ctx.log("linha"))
    engine.enqueue("bruteforce-servico")
    assert wait_for(lambda: engine.snapshot()["current"] is None)
    stream = engine.subscribe()
    primeiro = next(stream)
    assert primeiro.startswith("data: ") and "agendado" in primeiro
    engine.stop()


def test_alerta_confirmado_durante_ataque_emite_sse_e_preserva_verificacao():
    def runner(ctx, params):
        ctx.set_expected_alerts(["HTTPLento"])
        ctx.report_alerts({"available": True, "pending": ["HTTPLento"], "fired": [], "missing": []})
        ctx.report_alerts({"available": True, "pending": [], "fired": ["HTTPLento"], "missing": []})

    def verifier_pos_restauracao(expected, cancelled):
        return {"available": True, "fired": [], "missing": list(expected)}

    engine = Engine(runners={"lentidao-http": runner}, verifier=verifier_pos_restauracao)
    engine.enqueue("lentidao-http")
    assert wait_for(lambda: any(e.get("status") == "concluido" for e in engine.recent_events(500)))
    eventos_alerta = [e for e in engine.recent_events(500) if e["type"] == "alerts"]
    assert len(eventos_alerta) == 2
    assert eventos_alerta[0]["data"]["pending"] == ["HTTPLento"]
    assert eventos_alerta[1]["data"]["fired"] == ["HTTPLento"]
    historico = engine.snapshot()["history"][0]
    assert historico["verification"] == {"available": True, "fired": ["HTTPLento"], "missing": []}
    engine.stop()
