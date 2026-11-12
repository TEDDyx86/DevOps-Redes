import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { parseDemoCounters, type RequestCounters } from "../metrics";

interface WorkLogEntry {
  at: string;
  latencyMs: number;
  message: string;
  failure?: string;
}

function StatCard({ label, value, tone, glitch }: { label: string; value: string; tone: "cyan" | "violet" | "amber" | "magenta"; glitch?: boolean }) {
  const toneClass = { cyan: "text-cyan glow-cyan", violet: "text-violet", amber: "text-amber", magenta: "text-magenta glow-magenta" }[tone];
  return (
    <div className="dialog-rpg p-6">
      <p className="font-pixel text-[10px] opacity-60">{label}</p>
      <p className={`font-pixel mt-4 text-sm ${toneClass} ${glitch ? "crt-flicker" : ""}`}>{value}</p>
    </div>
  );
}

export default function Panel() {
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [counters, setCounters] = useState<RequestCounters | null>(null);
  const [log, setLog] = useState<WorkLogEntry[]>([]);
  const [busy, setBusy] = useState(false);

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
    return () => { alive = false; };
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
    const fast = window.setInterval(() => { void refreshHealth(); void refreshMode(); }, 3000);
    const slow = window.setInterval(() => { void refreshMetrics(); }, 10000);
    return () => { window.clearInterval(fast); window.clearInterval(slow); };
  }, [ready, refreshHealth, refreshMode, refreshMetrics]);

  async function runWork() {
    setBusy(true);
    const started = performance.now();
    try {
      const data = await api.work();
      const latencyMs = Math.round(performance.now() - started);
      setLog((entries) => [{ at: new Date().toLocaleTimeString(), latencyMs, message: data.message }, ...entries].slice(0, 8));
    } catch {
      const latencyMs = Math.round(performance.now() - started);
      setLog((entries) => [{ at: new Date().toLocaleTimeString(), latencyMs, message: "", failure: "FALHA — serviço não respondeu" }, ...entries].slice(0, 8));
    } finally {
      setBusy(false);
    }
  }

  const statusLines = counters
    ? Object.entries(counters.byStatus).sort(([a], [b]) => a.localeCompare(b))
    : [];

  return (
    <main className="crt-scanlines min-h-screen bg-bg px-6 py-8 font-mono text-parchment">
      <header className="mx-auto flex max-w-5xl items-center justify-between">
        <h1 className="font-pixel text-xs text-cyan glow-cyan">WORKBYTE // PAINEL</h1>
        <button
          onClick={() => { void api.logout().then(() => window.location.assign("/")); }}
          className="font-pixel border-2 border-magenta px-3 py-2 text-[10px] text-magenta transition-colors hover:bg-magenta/10"
        >
          SAIR
        </button>
      </header>

      <section className="mx-auto mt-8 grid max-w-5xl gap-6 md:grid-cols-3">
        <StatCard label="SINAL" value={online === null ? "..." : online ? "● ONLINE" : "✖ SIGNAL LOST"} tone={online ? "cyan" : "magenta"} glitch={online === false} />
        <StatCard label="MODO" value={mode === null ? "..." : mode.toUpperCase()} tone="violet" />
        <StatCard label="REQUISIÇÕES" value={counters ? String(Math.round(counters.total)) : "AGUARDANDO DADOS"} tone="amber" />
      </section>

      <section className="mx-auto mt-6 grid max-w-5xl gap-6 md:grid-cols-2">
        <div className="dialog-rpg p-6">
          <p className="font-pixel text-[10px] opacity-60">CONSOLE DE TRABALHO</p>
          <button
            onClick={() => { void runWork(); }}
            disabled={busy}
            className="font-pixel mt-4 border-2 border-cyan px-4 py-3 text-[10px] text-cyan transition-colors hover:bg-cyan/10 disabled:opacity-50"
          >
            {busy ? "PROCESSANDO..." : "▶ EXECUTAR /WORK"}
          </button>
          <div className="mt-4 max-h-56 space-y-2 overflow-y-auto font-mono text-xs">
            {log.length === 0 && <p className="opacity-50">* Sem execuções nesta sessão.</p>}
            {log.map((entry, index) => (
              <p key={`${entry.at}-${index}`} className={entry.failure ? "text-magenta" : "opacity-80"}>
                [{entry.at}] {entry.failure ?? `${entry.message} — ${entry.latencyMs} ms`}
              </p>
            ))}
          </div>
        </div>
        <div className="dialog-rpg p-6">
          <p className="font-pixel text-[10px] opacity-60">CONTADORES POR STATUS</p>
          <div className="mt-4 space-y-2 font-mono text-xs">
            {statusLines.length === 0 && <p className="opacity-50">AGUARDANDO DADOS</p>}
            {statusLines.map(([status, value]) => (
              <p key={status} className="flex justify-between opacity-80">
                <span>HTTP {status}</span>
                <span className="text-cyan">{Math.round(value)}</span>
              </p>
            ))}
            {counters && counters.work > 0 && (
              <p className="flex justify-between border-t border-panel-edge pt-2 opacity-80">
                <span>/work</span>
                <span className="text-violet">{Math.round(counters.work)}</span>
              </p>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
