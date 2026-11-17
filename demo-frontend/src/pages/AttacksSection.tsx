import { useEffect, useState } from "react";
import type { Attack, AttackEvent, QueueEntry, QueueSnapshot } from "../api";
import { statusLabel, verificationLine } from "./attacksView";

const LATEST_EVENTS = 30;

interface AttacksSectionProps {
  attacks: Attack[];
  queue: QueueSnapshot | null;
  busyId: string | null;
  events: AttackEvent[];
  onStart: (attack: Attack, params: Record<string, string>) => void;
  onCancel: (entryId: string) => void;
}

function alertaTone(status: string): string {
  if (status === "concluido") return "text-emerald-300";
  if (status === "falhou") return "text-rose-300";
  if (status === "interrompido" || status === "interrompendo") return "text-amber-300";
  return "text-cyan";
}

function contadores(counters: Record<string, number>): string {
  return Object.entries(counters)
    .map(([name, value]) => `${name}: ${value}`)
    .join(" · ");
}

export default function AttacksSection({ attacks, queue, busyId, events, onStart, onCancel }: AttacksSectionProps) {
  const [params, setParams] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    setParams((current) => {
      const next: Record<string, Record<string, string>> = {};
      for (const attack of attacks) {
        const anterior = current[attack.id] ?? {};
        next[attack.id] = Object.fromEntries(
          attack.params.map((param) => [param.name, String(anterior[param.name] ?? param.default)]),
        );
      }
      return next;
    });
  }, [attacks]);

  return (
    <div className="space-y-8">
      <section aria-labelledby="attacks-catalog-title">
        <div className="mb-4">
          <p className="font-pixel text-[9px] tracking-wide text-cyan">CATÁLOGO</p>
          <h2 id="attacks-catalog-title" className="mt-2 text-base font-semibold">
            Ataques disponíveis
          </h2>
          <p className="mt-1 text-xs text-parchment/55">
            Efeitos controlados e reversíveis contra o laboratório; cada ataque verifica o alerta esperado no Prometheus.
          </p>
        </div>
        <div className="grid gap-px border border-panel-edge bg-panel-edge sm:grid-cols-2">
          {attacks.map((attack) => {
            const busy = busyId === attack.id;
            return (
              <article key={attack.id} className="bg-[#090b16] p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-pixel text-[10px] leading-relaxed text-parchment">{attack.name}</h3>
                  <span className="shrink-0 border border-panel-edge px-2 py-1 text-[10px] text-parchment/60">
                    {attack.target}
                  </span>
                </div>
                <p className="mt-3 text-xs text-parchment/60">{attack.description}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {attack.expected_alerts.map((alert) => (
                    <span
                      key={alert}
                      className="border border-cyan/40 bg-cyan/10 px-2 py-0.5 text-[10px] text-cyan"
                      title="Alerta esperado no painel de monitoramento"
                    >
                      {alert}
                    </span>
                  ))}
                </div>
                <div className="mt-4 space-y-2">
                  {attack.params.map((param) => (
                    <label key={param.name} className="block text-[11px] text-parchment/65">
                      {param.name}
                      <input
                        type={param.type === "int" ? "number" : "text"}
                        value={params[attack.id]?.[param.name] ?? String(param.default)}
                        min={param.min}
                        max={param.max}
                        onChange={(event) =>
                          setParams((current) => ({
                            ...current,
                            [attack.id]: { ...(current[attack.id] ?? {}), [param.name]: event.target.value },
                          }))
                        }
                        className="mt-1 w-full border border-panel-edge bg-[#05060f] px-2 py-1.5 text-sm text-parchment outline-none focus:border-cyan"
                      />
                    </label>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => onStart(attack, params[attack.id] ?? {})}
                  disabled={busy || busyId !== null}
                  className="mt-4 w-full border border-cyan bg-cyan/10 px-3 py-2 text-xs font-semibold text-cyan transition-colors hover:bg-cyan hover:text-[#05060f] disabled:cursor-wait disabled:opacity-50"
                >
                  {busy ? "Na fila…" : "Iniciar"}
                </button>
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="attacks-queue-title" className="border border-panel-edge bg-[#090b16]">
        <div className="border-b border-panel-edge px-5 py-4">
          <p className="font-pixel text-[9px] tracking-wide text-cyan">FILA</p>
          <h2 id="attacks-queue-title" className="mt-2 text-base font-semibold">
            Execução (uma por vez)
          </h2>
        </div>
        <div className="space-y-4 p-5">
          {queue?.current ? (
            <div className="border border-cyan/40 bg-black/30 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className={`text-sm font-semibold ${alertaTone(queue.current.status)}`}>
                  {queue.current.attack} — {statusLabel(queue.current.status)}
                </p>
                <button
                  type="button"
                  onClick={() => onCancel(queue.current!.entry_id)}
                  className="border border-rose-400/50 px-3 py-1.5 text-[11px] text-rose-300 transition-colors hover:border-rose-300 hover:bg-rose-300/10"
                >
                  Interromper
                </button>
              </div>
              {Object.keys(queue.current.counters).length > 0 && (
                <p className="mt-2 font-mono text-[11px] text-parchment/60">
                  {contadores(queue.current.counters)}
                </p>
              )}
              <p className="mt-2 text-xs text-parchment/55">
                {verificationLine(queue.current.verification)}
              </p>
            </div>
          ) : (
            <p className="text-xs text-parchment/45">Nenhum ataque em execução.</p>
          )}

          {queue && queue.queue.length > 0 && (
            <ul className="space-y-1.5">
              {queue.queue.map((entry) => (
                <li key={entry.entry_id} className="flex items-center justify-between text-xs text-parchment/65">
                  <span>{entry.attack}</span>
                  <span className="text-amber-300">{statusLabel(entry.status)}</span>
                </li>
              ))}
            </ul>
          )}

          {queue && queue.history.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-parchment/75">Histórico recente</h3>
              <ul className="mt-2 space-y-1.5">
                {queue.history.map((entry) => (
                  <li key={entry.entry_id} className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className={alertaTone(entry.status)}>
                      {entry.attack} — {statusLabel(entry.status)}
                      {entry.error ? ` (${entry.error})` : ""}
                    </span>
                    <span className="text-parchment/55">{verificationLine(entry.verification)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section aria-labelledby="attacks-log-title" className="border border-panel-edge bg-[#090b16]">
        <div className="flex items-center justify-between border-b border-panel-edge px-5 py-3">
          <h3 id="attacks-log-title" className="text-xs font-semibold text-parchment/75">
            Log do motor (ao vivo)
          </h3>
          <span className="text-[10px] text-parchment/40">SSE · /api/events</span>
        </div>
        <div className="max-h-56 overflow-y-auto p-5">
          {events.length === 0 ? (
            <p className="text-xs text-parchment/45">Sem eventos ainda; dispare um ataque.</p>
          ) : (
            <ul className="space-y-1 font-mono text-[11px]">
              {events.map((event) => (
                <li key={event.seq} className="text-parchment/70">
                  <span className="mr-2 text-parchment/35">#{event.seq}</span>
                  <span className="mr-2 text-cyan">{event.type}</span>
                  {event.attack ? <span className="mr-2 text-parchment/50">{event.attack}</span> : null}
                  {event.message ?? (event.status ? statusLabel(event.status) : "")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
