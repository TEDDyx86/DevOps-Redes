import { useMemo, useState } from "react";
import { IncidentsList } from "./components";
import type { Incident } from "./types";

type StatusFilter = "all" | "firing" | "resolved" | "reconciled";

const SERVICE_NAMES: Record<string, string> = {
  "web-demo": "HTTP (web-demo)",
  postgres: "PostgreSQL",
  dns: "DNS",
  smtp: "SMTP",
  platform: "Plataforma",
  monitoring: "Coleta",
};

export default function IncidentsView({ incidents }: { incidents: Incident[] }) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [serviceFilter, setServiceFilter] = useState("all");

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

  return (
    <>
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
                  onClick={() => setStatusFilter(id)}
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
                onChange={(event) => setServiceFilter(event.target.value)}
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
        <IncidentsList incidents={filtered} />
      </section>
    </>
  );
}
