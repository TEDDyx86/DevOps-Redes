import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Play,
  ShieldAlert,
  Square,
  Swords,
  Terminal,
} from "lucide-react";
import { request } from "./api";

export interface AttackParam {
  name: string;
  type: "int" | "str";
  default: number | string;
  min?: number;
  max?: number;
  options?: string[];
}

export interface AttackSpec {
  id: string;
  name: string;
  target: string;
  description: string;
  params: AttackParam[];
  expected_alerts: string[];
}

export interface AttackVerification {
  available: boolean;
  fired: string[];
  missing: string[];
}

export interface QueueEntry {
  entry_id: string;
  attack: string;
  status: string;
  params: Record<string, number | string>;
  expected_alerts: string[];
  counters: Record<string, number>;
  verification: AttackVerification | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface QueueSnapshot {
  current: QueueEntry | null;
  queue: QueueEntry[];
  history: QueueEntry[];
}

export interface AttackEvent {
  seq: number;
  type: string;
  entry_id?: string;
  attack?: string;
  status?: string;
  message?: string;
  counters?: Record<string, number>;
  data?: AttackVerification;
}

const STATUS_LABELS: Record<string, string> = {
  agendado: "Na fila",
  preparando: "Preparando",
  executando: "Executando",
  verificando: "Verificando alertas",
  concluido: "Concluído",
  interrompendo: "Interrompendo",
  interrompido: "Interrompido",
  falhou: "Falhou",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function verificationSummary(v: AttackVerification | null): string {
  if (!v) return "Aguardando verificação no Prometheus";
  if (!v.available) return "Prometheus indisponível durante a verificação";
  if (v.fired.length === 0 && v.missing.length === 0) {
    return "Telemetria gerada (sem alerta crítico esperado)";
  }
  const parts: string[] = [];
  if (v.fired.length > 0) parts.push(`Disparou: ${v.fired.join(", ")}`);
  if (v.missing.length > 0) parts.push(`Não disparou: ${v.missing.join(", ")}`);
  return parts.join(" · ");
}

function formatCounters(counters: Record<string, number>): string {
  return Object.entries(counters)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
}

function statusClass(status: string): string {
  if (status === "concluido") return "ok";
  if (status === "falhou") return "critical";
  if (status === "interrompido" || status === "interrompendo") return "warning";
  return "active";
}

type TargetFilter = "all" | "http" | "infra" | "auth";

function matchesFilter(attack: AttackSpec, filter: TargetFilter): boolean {
  if (filter === "all") return true;
  if (filter === "auth") return attack.id.startsWith("bruteforce-");
  if (filter === "http") {
    return (
      attack.target.includes("web-demo") && !attack.id.startsWith("bruteforce-")
    );
  }
  return !attack.target.includes("web-demo") && !attack.id.startsWith("bruteforce-");
}

export default function Attacks({ onChanged }: { onChanged?: () => void }) {
  const [attacks, setAttacks] = useState<AttackSpec[]>([]);
  const [queue, setQueue] = useState<QueueSnapshot | null>(null);
  const [events, setEvents] = useState<AttackEvent[]>([]);
  const [params, setParams] = useState<Record<string, Record<string, string>>>({});
  const [filter, setFilter] = useState<TargetFilter>("all");
  const [busyAttack, setBusyAttack] = useState<string | null>(null);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async () => {
    try {
      const [catalogRes, queueRes] = await Promise.all([
        request<{ attacks: AttackSpec[] }>("/api/attacks"),
        request<QueueSnapshot>("/api/queue"),
      ]);
      setAttacks(catalogRes.attacks);
      setQueue(queueRes);
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Erro ao carregar catálogo de ataques.",
      );
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot]);

  useEffect(() => {
    setParams((current) => {
      const next: Record<string, Record<string, string>> = {};
      for (const attack of attacks) {
        const previous = current[attack.id] ?? {};
        next[attack.id] = Object.fromEntries(
          attack.params.map((p) => [p.name, String(previous[p.name] ?? p.default)]),
        );
      }
      return next;
    });
  }, [attacks]);

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const source = new EventSource("/api/events");
    source.onmessage = (msg) => {
      try {
        const evt = JSON.parse(msg.data) as AttackEvent;
        setEvents((prev) => {
          const filtered = prev.some((item) => item.seq === evt.seq)
            ? prev
            : [...prev, evt];
          return filtered.slice(-40);
        });
        if (evt.type === "status" || evt.type === "verification") {
          void request<QueueSnapshot>("/api/queue")
            .then((snap) => {
              setQueue(snap);
              if (evt.status === "concluido" || evt.type === "verification") {
                onChanged?.();
              }
            })
            .catch(() => undefined);
        } else if (evt.type === "progress" && evt.counters) {
          setQueue((prev) =>
            prev?.current
              ? {
                  ...prev,
                  current: { ...prev.current, counters: evt.counters! },
                }
              : prev,
          );
        }
      } catch {
        // Ignora mensagens malformadas do stream
      }
    };
    return () => source.close();
  }, [onChanged]);

  const filteredAttacks = useMemo(
    () => attacks.filter((item) => matchesFilter(item, filter)),
    [attacks, filter],
  );

  async function handleStart(attack: AttackSpec) {
    if (busyAttack) return;
    setBusyAttack(attack.id);
    setError(null);
    try {
      const raw = params[attack.id] ?? {};
      const parsed: Record<string, number | string> = {};
      for (const spec of attack.params) {
        const val = raw[spec.name] ?? String(spec.default);
        parsed[spec.name] = spec.type === "int" ? Number.parseInt(val, 10) : val;
      }
      await request("/api/attacks/" + encodeURIComponent(attack.id) + "/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ params: parsed }),
      });
      await loadSnapshot();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao enfileirar ataque.");
    } finally {
      setBusyAttack(null);
    }
  }

  async function handleCancel(entryId: string) {
    if (cancelBusy) return;
    setCancelBusy(true);
    try {
      await request("/api/queue/" + encodeURIComponent(entryId) + "/cancel", {
        method: "POST",
      });
      await loadSnapshot();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao interromper ataque.");
    } finally {
      setCancelBusy(false);
    }
  }

  const running = queue?.current ?? null;
  const history = [...(queue?.history ?? [])].reverse();

  return (
    <div className="attacks-layout">
      {error && (
        <div className="notice error" role="alert">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Execução atual e fila */}
      <section className="panel" aria-labelledby="attacks-queue-heading">
        <div className="panel-heading">
          <div>
            <h2 id="attacks-queue-heading">Fila de execução (um ataque por vez)</h2>
            <p>
              Os ataques alteram o ambiente de forma controlada e restauram os arquivos,
              contêineres e modos ao concluir ou interromper.
            </p>
          </div>
          <Activity size={20} />
        </div>

        {running ? (
          <div className="attack-running-box">
            <div className="attack-running-head">
              <div>
                <span className={`attack-status-pill ${statusClass(running.status)}`}>
                  {statusLabel(running.status)}
                </span>
                <strong className="attack-running-name">{running.attack}</strong>
              </div>
              <button
                type="button"
                className="button secondary"
                disabled={cancelBusy}
                onClick={() => void handleCancel(running.entry_id)}
              >
                <Square size={14} /> Interromper
              </button>
            </div>
            {Object.keys(running.counters).length > 0 && (
              <p className="attack-counters numeric">{formatCounters(running.counters)}</p>
            )}
            <p className="small muted">{verificationSummary(running.verification)}</p>
          </div>
        ) : (
          <p className="small muted">Nenhum ataque em execução no momento.</p>
        )}

        {queue && queue.queue.length > 0 && (
          <div className="attack-pending-list">
            <span className="small muted">Na fila ({queue.queue.length}):</span>
            {queue.queue.map((entry) => (
              <span key={entry.entry_id} className="attack-queue-chip">
                {entry.attack}
              </span>
            ))}
          </div>
        )}
      </section>

      {/* Catálogo de ataques */}
      <section className="panel" aria-labelledby="attacks-catalog-heading">
        <div className="panel-heading">
          <div>
            <h2 id="attacks-catalog-heading">Catálogo de ataques ({filteredAttacks.length})</h2>
            <p>Escolha o vetor, ajuste os parâmetros e acompanhe os alertas no painel.</p>
          </div>
          <div className="filter-pills" role="tablist" aria-label="Filtrar ataques">
            {(
              [
                ["all", "Todos"],
                ["http", "Loja / HTTP"],
                ["auth", "Autenticação"],
                ["infra", "Banco / Rede / Infra"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`filter-pill ${filter === key ? "active" : ""}`}
                onClick={() => setFilter(key)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="attacks-grid">
          {filteredAttacks.map((attack) => {
            const values = params[attack.id] ?? {};
            const disabled = busyAttack !== null || running !== null;
            return (
              <article key={attack.id} className="attack-card">
                <div className="attack-card-head">
                  <h3>
                    <Swords size={15} /> {attack.name}
                  </h3>
                  <span className="attack-target-badge">{attack.target}</span>
                </div>

                <p className="attack-description">{attack.description}</p>

                <div className="attack-alerts-row">
                  {attack.expected_alerts.length > 0 ? (
                    attack.expected_alerts.map((alert) => (
                      <span key={alert} className="attack-alert-badge">
                        <ShieldAlert size={12} /> {alert}
                      </span>
                    ))
                  ) : (
                    <span className="attack-alert-badge muted-badge">
                      Sem alerta específico (métrica / disponibilidade)
                    </span>
                  )}
                </div>

                <div className="attack-params">
                  {attack.params.map((spec) => (
                    <label key={spec.name} className="attack-param-label">
                      <span>{spec.name}</span>
                      {spec.options ? (
                        <select
                          value={values[spec.name] ?? String(spec.default)}
                          onChange={(e) =>
                            setParams((prev) => ({
                              ...prev,
                              [attack.id]: {
                                ...(prev[attack.id] ?? {}),
                                [spec.name]: e.target.value,
                              },
                            }))
                          }
                        >
                          {spec.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={spec.type === "int" ? "number" : "text"}
                          min={spec.min}
                          max={spec.max}
                          value={values[spec.name] ?? String(spec.default)}
                          onChange={(e) =>
                            setParams((prev) => ({
                              ...prev,
                              [attack.id]: {
                                ...(prev[attack.id] ?? {}),
                                [spec.name]: e.target.value,
                              },
                            }))
                          }
                        />
                      )}
                    </label>
                  ))}
                </div>

                <button
                  type="button"
                  className="button primary attack-start-btn"
                  disabled={disabled}
                  onClick={() => void handleStart(attack)}
                >
                  <Play size={14} />{" "}
                  {busyAttack === attack.id
                    ? "Enfileirando…"
                    : running?.attack === attack.id
                      ? "Em execução…"
                      : "Iniciar ataque"}
                </button>
              </article>
            );
          })}
        </div>
      </section>

      {/* Histórico e Log ao vivo */}
      <div className="attacks-bottom-grid">
        <section className="panel" aria-labelledby="attacks-history-heading">
          <div className="panel-heading">
            <div>
              <h2 id="attacks-history-heading">Histórico recente</h2>
              <p>Últimos testes executados e confirmação no Prometheus.</p>
            </div>
            <CheckCircle2 size={18} />
          </div>

          {history.length === 0 ? (
            <p className="small muted">Nenhum ataque finalizado nesta sessão ainda.</p>
          ) : (
            <div className="attack-history-list">
              {history.map((item) => (
                <div key={item.entry_id} className="attack-history-row">
                  <div className="attack-history-top">
                    <strong>{item.attack}</strong>
                    <span className={`attack-status-pill ${statusClass(item.status)}`}>
                      {statusLabel(item.status)}
                    </span>
                  </div>
                  {Object.keys(item.counters).length > 0 && (
                    <p className="numeric muted">{formatCounters(item.counters)}</p>
                  )}
                  <p className="small muted">
                    {item.error
                      ? `Erro: ${item.error}`
                      : verificationSummary(item.verification)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel" aria-labelledby="attacks-log-heading">
          <div className="panel-heading">
            <div>
              <h2 id="attacks-log-heading">Log de eventos ao vivo</h2>
              <p>Acompanhamento em tempo real via Server-Sent Events.</p>
            </div>
            <Terminal size={18} />
          </div>

          {events.length === 0 ? (
            <p className="small muted">Aguardando eventos da fila de ataques.</p>
          ) : (
            <div className="attack-log-box numeric">
              {events
                .slice(-20)
                .reverse()
                .map((evt) => (
                  <div key={evt.seq} className="attack-log-line">
                    <span className="muted">#{evt.seq}</span>{" "}
                    <span className="attack-log-tag">{evt.attack ?? "motor"}</span>{" "}
                    <span>
                      {evt.message ??
                        (evt.type === "verification"
                          ? verificationSummary(evt.data ?? null)
                          : evt.counters
                            ? formatCounters(evt.counters)
                            : evt.status ?? evt.type)}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
