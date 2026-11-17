import { useCallback, useEffect, useState } from "react";
import { api, type Mode } from "../api";
import { parseDemoCounters, type RequestCounters } from "../metrics";

interface WorkLogEntry {
  at: string;
  latencyMs: number;
  message: string;
  failure?: string;
}

export default function Panel() {
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [counters, setCounters] = useState<RequestCounters | null>(null);
  const [log, setLog] = useState<WorkLogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [lastLatency, setLastLatency] = useState<number | undefined>(undefined);
  const [workCount, setWorkCount] = useState(0);
  const [labToken, setLabToken] = useState("");
  const [modeBusy, setModeBusy] = useState(false);
  const [modeMessage, setModeMessage] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.authenticated().then((ok) => {
      if (!alive) return;
      if (!ok) {
        window.location.assign("/login");
        return;
      }
      setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const refreshHealth = useCallback(async () => setOnline(await api.health()), []);
  const refreshMode = useCallback(async () => {
    try {
      setMode((await api.mode()).mode);
    } catch {
      setMode(null);
    }
  }, []);
  const refreshMetrics = useCallback(async () => {
    try {
      setCounters(parseDemoCounters(await api.metrics()));
    } catch {
      setCounters(null);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    void refreshHealth();
    void refreshMode();
    void refreshMetrics();
    const fast = window.setInterval(() => {
      void refreshHealth();
      void refreshMode();
    }, 3000);
    const slow = window.setInterval(() => {
      void refreshMetrics();
    }, 8000);
    return () => {
      window.clearInterval(fast);
      window.clearInterval(slow);
    };
  }, [ready, refreshHealth, refreshMode, refreshMetrics]);

  async function runWork() {
    setBusy(true);
    const started = performance.now();
    try {
      const data = await api.work();
      const latencyMs = Math.round(performance.now() - started);
      setLastLatency(latencyMs);
      setWorkCount((count) => count + 1);
      setOnline(true);
      setLog((entries) => [
        { at: new Date().toLocaleTimeString(), latencyMs, message: data.message },
        ...entries.slice(0, 11),
      ]);
      void refreshMetrics();
    } catch {
      const latencyMs = Math.round(performance.now() - started);
      setLastLatency(latencyMs);
      setOnline(false);
      setLog((entries) => [
        {
          at: new Date().toLocaleTimeString(),
          latencyMs,
          message: "",
          failure: "Falha 503 ou timeout — serviço indisponível ou lento.",
        },
        ...entries.slice(0, 11),
      ]);
      void refreshMetrics();
    } finally {
      setBusy(false);
    }
  }

  async function applyMode(newMode: Mode) {
    if (!labToken.trim()) {
      setModeMessage("Informe o LAB_TOKEN do .env para alterar o modo do serviço.");
      return;
    }
    setModeBusy(true);
    setModeMessage(null);
    try {
      const ok = await api.setMode(newMode, labToken.trim());
      if (ok) {
        setModeMessage(`Modo alterado para ${newMode.toUpperCase()}.`);
        void refreshMode();
        void refreshHealth();
      } else {
        setModeMessage("Token de laboratório inválido (401).");
      }
    } catch {
      setModeMessage("Não foi possível comunicar com o endpoint /mode.");
    } finally {
      setModeBusy(false);
    }
  }

  const statusLines = counters
    ? Object.entries(counters.byStatus).sort(([left], [right]) => left.localeCompare(right))
    : [];
  const statusLabel = online === null ? "Aguardando verificação" : online ? "Operacional" : "Indisponível";
  const statusTone =
    online === null ? "text-parchment/60" : online ? "text-emerald-300" : "text-rose-300";

  return (
    <main className="min-h-screen bg-[#05060f] font-mono text-parchment">
      <header className="border-b border-panel-edge bg-[#080912]">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <a href="/" className="font-pixel text-[10px] tracking-wider text-parchment">
            WORKBYTE<span className="text-cyan">.EXE</span>
            <span className="ml-3 hidden font-mono text-xs font-normal tracking-normal text-parchment/45 sm:inline">
              / Painel do serviço
            </span>
          </a>
          <button
            onClick={() => {
              void api.logout().then(() => window.location.assign("/"));
            }}
            className="border border-panel-edge px-3 py-2 text-xs text-parchment/70 transition-colors hover:border-cyan/60 hover:text-cyan focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan"
          >
            Sair
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6 sm:py-10">
        <section aria-labelledby="overview-title">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="font-pixel text-[9px] tracking-[0.16em] text-cyan">VISÃO DO SERVIÇO</p>
              <h1 id="overview-title" className="mt-3 text-xl font-semibold sm:text-2xl">
                Estado atual
              </h1>
            </div>
            <span className="text-xs text-parchment/45">Atualização automática</span>
          </div>

          <div className="grid overflow-hidden border border-panel-edge bg-panel-edge sm:grid-cols-3">
            <div className="bg-[#090b16] p-5 sm:p-6">
              <p className="text-xs text-parchment/55">SINAL DO SERVIÇO</p>
              <p className={`mt-3 text-lg font-semibold ${statusTone}`} aria-live="polite">
                <span aria-hidden="true">{online === null ? "○" : online ? "●" : "●"}</span>{" "}
                {statusLabel}
              </p>
              <p className="mt-2 text-xs text-parchment/40">Verificação HTTP do web-demo</p>
            </div>
            <div className="border-t border-panel-edge bg-[#090b16] p-5 sm:border-l sm:border-t-0 sm:p-6">
              <p className="text-xs text-parchment/55">MODO DE OPERAÇÃO</p>
              <p className="mt-3 text-lg font-semibold capitalize text-parchment">
                {mode ?? "Sem dados"}
              </p>
              <p className="mt-2 text-xs text-parchment/40">Estado informado pelo serviço</p>
            </div>
            <div className="border-t border-panel-edge bg-[#090b16] p-5 sm:border-l sm:border-t-0 sm:p-6">
              <p className="text-xs text-parchment/55">ÚLTIMA LATÊNCIA /WORK</p>
              <p className="mt-3 text-lg font-semibold text-cyan">
                {lastLatency === undefined ? "Sem medição" : `${lastLatency} ms`}
              </p>
              <p className="mt-2 text-xs text-parchment/40">
                {workCount} {workCount === 1 ? "resposta bem-sucedida nesta sessão" : "respostas bem-sucedidas nesta sessão"}
              </p>
            </div>
          </div>
        </section>

        <section aria-labelledby="work-title" className="border border-panel-edge bg-[#090b16]">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-panel-edge px-5 py-4 sm:px-6">
            <div>
              <p className="font-pixel text-[9px] tracking-wide text-cyan">REQUISIÇÃO REAL</p>
              <h2 id="work-title" className="mt-2 text-base font-semibold">Executar /work</h2>
              <p className="mt-1 text-xs text-parchment/55">
                Envia uma requisição ao serviço e mede o tempo de resposta neste navegador.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void runWork()}
              disabled={busy}
              className="border border-cyan bg-cyan/10 px-4 py-3 text-xs font-semibold text-cyan transition-colors hover:bg-cyan hover:text-[#05060f] disabled:cursor-wait disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan"
            >
              {busy ? "Executando…" : "▶ Executar /work"}
            </button>
          </div>

          <div className="p-5 sm:px-6">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-xs font-semibold text-parchment/75">Atividade recente</h3>
              <button
                type="button"
                onClick={() => setLog([])}
                disabled={log.length === 0}
                className="text-xs text-parchment/50 underline decoration-panel-edge underline-offset-4 hover:text-cyan disabled:no-underline disabled:opacity-40"
              >
                Limpar
              </button>
            </div>
            <div className="max-h-56 space-y-2 overflow-y-auto">
              {log.length === 0 ? (
                <p className="border border-panel-edge px-3 py-4 text-xs text-parchment/45">
                  Nenhuma requisição executada nesta sessão.
                </p>
              ) : (
                log.map((entry, index) => (
                  <div
                    key={`${entry.at}-${index}`}
                    className="flex flex-wrap items-start justify-between gap-2 border-l-2 border-cyan/50 bg-black/25 px-3 py-2 text-xs"
                  >
                    <p className={entry.failure ? "text-rose-300" : "text-parchment/75"}>
                      <span className="mr-2 text-parchment/40">{entry.at}</span>
                      {entry.failure ?? entry.message}
                    </p>
                    <span className="shrink-0 text-parchment/50">{entry.latencyMs} ms</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <section aria-labelledby="metrics-title">
          <div className="mb-4">
            <p className="font-pixel text-[9px] tracking-wide text-cyan">DADOS OBSERVADOS</p>
            <h2 id="metrics-title" className="mt-2 text-base font-semibold">Métricas HTTP</h2>
          </div>
          <div className="grid gap-px border border-panel-edge bg-panel-edge sm:grid-cols-2">
            <article className="bg-[#090b16] p-5 sm:p-6">
              <p className="text-xs text-parchment/55">TOTAL DE REQUISIÇÕES</p>
              <p className="mt-3 text-2xl font-semibold text-parchment">
                {counters ? Math.round(counters.total).toLocaleString() : "Aguardando dados"}
              </p>
              <p className="mt-2 text-xs text-parchment/40">Contador exposto pelo serviço</p>
            </article>
            <article className="bg-[#090b16] p-5 sm:p-6">
              <p className="text-xs text-parchment/55">CHAMADAS /WORK</p>
              <p className="mt-3 text-2xl font-semibold text-cyan">
                {counters ? Math.round(counters.work).toLocaleString() : "Aguardando dados"}
              </p>
              <p className="mt-2 text-xs text-parchment/40">Contador Prometheus para path /work</p>
            </article>
          </div>

          <div className="mt-4 border border-panel-edge bg-[#090b16]">
            <div className="flex items-center justify-between gap-3 border-b border-panel-edge px-5 py-3">
              <h3 className="text-xs font-semibold text-parchment/75">Distribuição por código HTTP</h3>
              <span className="text-[10px] text-parchment/40">Scrape Prometheus · 5 s</span>
            </div>
            {statusLines.length === 0 ? (
              <p className="px-5 py-4 text-xs text-parchment/45">Aguardando dados de scrape.</p>
            ) : (
              <ul className="divide-y divide-panel-edge">
                {statusLines.map(([status, value]) => (
                  <li key={status} className="flex items-center justify-between px-5 py-3 text-xs">
                    <span className="flex items-center gap-2 text-parchment/70">
                      <span
                        aria-hidden="true"
                        className={`size-2 ${status === "200" ? "bg-emerald-300" : "bg-rose-300"}`}
                      />
                      HTTP {status}
                    </span>
                    <span className="text-parchment/60">{Math.round(value).toLocaleString()} reqs</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <details className="group border border-panel-edge bg-[#080a14]">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm text-parchment/75 marker:content-none hover:text-cyan focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan">
            <span>
              <span className="block font-semibold">Ferramentas do laboratório</span>
              <span className="mt-1 block text-xs text-parchment/45">
                Controles de falha para demonstração de alertas.
              </span>
            </span>
            <span aria-hidden="true" className="text-cyan transition-transform group-open:rotate-45">+</span>
          </summary>
          <div className="space-y-4 border-t border-panel-edge p-5 sm:p-6">
            <p className="text-xs text-parchment/55">
              Alterar o modo modifica o comportamento do serviço monitorado. Use apenas no laboratório local.
              Modo atual: <strong className="font-semibold text-parchment">{mode ?? "sem dados"}</strong>.
            </p>
            <label className="block max-w-xl">
              <span className="text-xs text-parchment/65">LAB_TOKEN</span>
              <input
                type="password"
                value={labToken}
                onChange={(event) => setLabToken(event.target.value)}
                placeholder="Cole o LAB_TOKEN do arquivo .env"
                className="mt-2 w-full border border-panel-edge bg-[#05060f] px-3 py-2.5 text-sm text-parchment outline-none placeholder:text-parchment/30 focus:border-cyan focus-visible:ring-2 focus-visible:ring-cyan/40"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              {(["normal", "slow", "offline"] as const).map((newMode) => (
                <button
                  key={newMode}
                  type="button"
                  onClick={() => void applyMode(newMode)}
                  disabled={modeBusy}
                  className="border border-panel-edge px-3 py-2 text-xs text-parchment/70 transition-colors hover:border-cyan/60 hover:text-cyan disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan"
                >
                  {newMode === "normal" ? "Normal (200)" : newMode === "slow" ? "Lento (+1,5 s)" : "Offline (503)"}
                </button>
              ))}
            </div>
            {modeMessage && (
              <p role="status" className="text-xs text-parchment/70">
                {modeMessage}
              </p>
            )}
          </div>
        </details>
      </div>
    </main>
  );
}
