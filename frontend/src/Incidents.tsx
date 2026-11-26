import { useMemo, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { IncidentsList } from "./components";
import type { Incident, LiveAlerts } from "./types";

type StatusFilter = "all" | "firing" | "resolved" | "reconciled";

const SERVICE_NAMES: Record<string, string> = {
  "web-demo": "HTTP (web-demo)",
  postgres: "PostgreSQL",
  dns: "DNS",
  smtp: "SMTP",
  platform: "Plataforma",
  monitoring: "Coleta",
};

const PAGE_SIZE = 20;

export default function IncidentsView({
  incidents,
  liveAlerts,
}: {
  incidents: Incident[];
  liveAlerts?: LiveAlerts | null;
}) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [serviceFilter, setServiceFilter] = useState("all");
  const [page, setPage] = useState(1);

  const counts = useMemo(() => {
    const firing = incidents.filter((item) => item.status === "firing").length;
    const reconciled = incidents.filter(
      (item) =>
        item.status === "resolved" &&
        item.resolution_source === "later_resolved_event",
    ).length;
    const resolved = incidents.filter(
      (item) =>
        item.status === "resolved" &&
        item.resolution_source !== "later_resolved_event",
    ).length;
    return {
      all: incidents.length,
      firing,
      resolved,
      reconciled,
    };
  }, [incidents]);

  const services = useMemo(
    () => Array.from(new Set(incidents.map((item) => item.service))).sort(),
    [incidents],
  );

  const filtered = useMemo(
    () =>
      incidents.filter((item) => {
        if (serviceFilter !== "all" && item.service !== serviceFilter) {
          return false;
        }
        if (statusFilter === "firing") return item.status === "firing";
        if (statusFilter === "reconciled") {
          return (
            item.status === "resolved" &&
            item.resolution_source === "later_resolved_event"
          );
        }
        if (statusFilter === "resolved") {
          return (
            item.status === "resolved" &&
            item.resolution_source !== "later_resolved_event"
          );
        }
        return true;
      }),
    [incidents, serviceFilter, statusFilter],
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const startIndex = (safePage - 1) * PAGE_SIZE;
  const visibleIncidents = filtered.slice(startIndex, startIndex + PAGE_SIZE);

  const hasLive =
    !!liveAlerts &&
    (liveAlerts.firing.length > 0 || liveAlerts.pending.length > 0);

  return (
    <>
      {hasLive && liveAlerts && (
        <section className="panel incidents-live-panel" aria-label="Alertas ativos no Prometheus">
          <div className="panel-heading">
            <div>
              <h2>Alertas ativos no Prometheus (ao vivo)</h2>
              <p>
                Detecção instantânea em estado pending (confirmando) e firing (notificado por e-mail).
              </p>
            </div>
            <a
              className="text-button"
              href="http://localhost:8025"
              target="_blank"
              rel="noreferrer"
            >
              Abrir Mailpit <ArrowUpRight size={15} />
            </a>
          </div>
          <div className="attacks-panel-body">
            <div className="attacks-live-alerts">
              {liveAlerts.firing.map((item) => (
                <span
                  key={`f-${item.alertname}-${item.service}`}
                  className="attack-status-pill critical"
                >
                  FIRING · {item.alertname} ({item.service || "plataforma"})
                </span>
              ))}
              {liveAlerts.pending.map((item) => (
                <span
                  key={`p-${item.alertname}-${item.service}`}
                  className="attack-status-pill warning"
                >
                  PENDING · {item.alertname} ({item.service || "plataforma"})
                </span>
              ))}
            </div>
          </div>
        </section>
      )}
      <div className="metric-strip incidents-summary">
        <div className="metric">
          <span>Registros no histórico</span>
          <strong>{counts.all}</strong>
          <p>Últimos 100 eventos persistidos</p>
        </div>
        <div className="metric">
          <span>Incidentes ativos</span>
          <strong>{counts.firing}</strong>
          <p>Alertas em estado firing</p>
        </div>
        <div className="metric">
          <span>Resolvidos diretos</span>
          <strong>{counts.resolved}</strong>
          <p>Com horário original confirmado</p>
        </div>
        <div className="metric">
          <span>Reconciliados</span>
          <strong>{counts.reconciled}</strong>
          <p>Confirmados por ciclo posterior</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-heading incidents-heading">
          <div>
            <h2>Histórico de incidentes</h2>
            <p>
              Eventos persistidos após confirmação das regras de alerta.
            </p>
          </div>
          <div className="incidents-toolbar">
            <div className="filter-pills" role="group" aria-label="Filtrar por estado">
              {(
                [
                  ["all", `Todos (${counts.all})`],
                  ["firing", `Ativos (${counts.firing})`],
                  ["resolved", `Resolvidos (${counts.resolved})`],
                  ["reconciled", `Reconciliados (${counts.reconciled})`],
                ] as [StatusFilter, string][]
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={`filter-pill ${statusFilter === id ? "active" : ""}`}
                  onClick={() => {
                    setStatusFilter(id);
                    setPage(1);
                  }}
                  aria-pressed={statusFilter === id}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="inline-select">
              <span className="sr-only">Filtrar por serviço</span>
              <select
                value={serviceFilter}
                onChange={(event) => {
                  setServiceFilter(event.target.value);
                  setPage(1);
                }}
              >
                <option value="all">Todos os serviços</option>
                {services.map((service) => (
                  <option key={service} value={service}>
                    {SERVICE_NAMES[service] ?? service}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <IncidentsList incidents={visibleIncidents} />
        {filtered.length > PAGE_SIZE && (
          <div className="incidents-pagination">
            <span>
              Mostrando {startIndex + 1}–{Math.min(startIndex + PAGE_SIZE, filtered.length)} de{" "}
              {filtered.length} · Página {safePage} de {totalPages}
            </span>
            <div>
              <button
                type="button"
                className="button secondary"
                disabled={safePage <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </button>
              <button
                type="button"
                className="button secondary"
                disabled={safePage >= totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}
