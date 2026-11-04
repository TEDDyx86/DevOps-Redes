import {
  Activity,
  ArrowUpRight,
  CircleCheck,
  CircleHelp,
  CircleX,
  Clock3,
  Database,
  Globe2,
  Mail,
  TriangleAlert,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatMetric } from "./api";
import type { ChartSample, Incident, ServiceSummary, Status } from "./types";

export const statusText: Record<Status, string> = {
  ok: "Operacional",
  warning: "Atenção",
  critical: "Indisponível",
  unknown: "Sem dados",
};
const icons = {
  ok: CircleCheck,
  warning: TriangleAlert,
  critical: CircleX,
  unknown: CircleHelp,
};

export function StatusBadge({ status }: { status: Status }) {
  const Icon = icons[status];
  return (
    <span className={`status status-${status}`}>
      <Icon size={13} />
      {statusText[status]}
    </span>
  );
}

export function timeLabel(
  stamp: number | string | null,
  withDate = false,
): string {
  if (!stamp) return "Aguardando coleta";
  const date = new Date(typeof stamp === "number" ? stamp * 1000 : stamp);
  return date.toLocaleString(
    "pt-BR",
    withDate
      ? {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }
      : { hour: "2-digit", minute: "2-digit", second: "2-digit" },
  );
}

export function SignalChart({
  data,
  metric,
  title,
  subtitle,
  unit,
}: {
  data: ChartSample[];
  metric: "rps" | "qps" | "messages_per_minute" | "latency_ms" | "cpu_cores" | "memory_mib" | "read_kibps" | "write_kibps";
  title: string;
  subtitle: string;
  unit: string;
}) {
  const hasData = data.some(
    (row) => row[metric] != null && Number.isFinite(row[metric]),
  );
  return (
    <section className="chart-panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="chart-legend">
          <i />
          {unit}
        </span>
      </div>
      {hasData ? (
        <div
          className="chart"
          role="img"
          aria-label={`${title}. ${data.filter((row) => row[metric] != null).length} amostras no período selecionado.`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 12, right: 12, bottom: 0, left: -18 }}
            >
              <CartesianGrid
                strokeDasharray="3 5"
                vertical={false}
                stroke="#e8e7ee"
              />
              <XAxis
                dataKey="timestamp"
                type="number"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(value) => timeLabel(value).slice(0, 5)}
                tick={{ fill: "#7b7a8b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                minTickGap={42}
              />
              <YAxis
                tick={{ fill: "#7b7a8b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                domain={[0, "auto"]}
                tickFormatter={(value) =>
                  formatMetric(value, metric === "cpu_cores" ? 3 : value < 1 ? 2 : 0)
                }
              />
              <Tooltip
                labelFormatter={(value) => timeLabel(Number(value))}
                formatter={(value) => [
                  `${formatMetric(Number(value), metric === "cpu_cores" ? 3 : 2)} ${unit}`,
                  title,
                ]}
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #dedce8",
                  fontSize: 12,
                }}
              />
              <Line
                type="linear"
                dataKey={metric}
                stroke={metric !== "latency_ms" ? "#7557d3" : "#328c94"}
                strokeWidth={2.4}
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-chart">
          <Activity size={26} />
          <strong>Aguardando amostras</strong>
          <span>
            As taxas aparecem após duas coletas. O laboratório gera tráfego real
            automaticamente.
          </span>
        </div>
      )}
    </section>
  );
}

export function IncidentsList({
  incidents,
  compact = false,
}: {
  incidents: Incident[];
  compact?: boolean;
}) {
  if (!incidents.length)
    return (
      <div className="empty-incidents">
        <CircleCheck size={24} />
        <div>
          <strong>Nenhum incidente registrado</strong>
          <p>
            Os alertas confirmados aparecerão aqui. Use o laboratório para
            testar o primeiro.
          </p>
        </div>
      </div>
    );
  return (
    <div className="incident-list">
      {incidents.slice(0, compact ? 4 : 100).map((item) => (
        <article
          className="incident"
          key={`${item.fingerprint}-${item.started_at}`}
        >
          <span
            className={`incident-symbol ${item.status === "resolved" ? "resolved" : item.severity}`}
          >
            {item.status === "resolved" ? (
              <CircleCheck size={17} />
            ) : (
              <TriangleAlert size={17} />
            )}
          </span>
          <div className="incident-copy">
            <strong>{item.summary}</strong>
            <p>{item.description}</p>
            {item.status === "resolved" && item.resolution_source === "later_resolved_event" && (
              <p>
                Resolução confirmada por evento posterior
                {item.resolution_evidence_ended_at ? ` em ${timeLabel(item.resolution_evidence_ended_at, true)}` : ""}.
                {" "}Término original não recebido.
              </p>
            )}
            <span>
              {item.service} <b>·</b> {timeLabel(item.started_at, true)}
            </span>
          </div>
          <span
            className={`incident-state ${item.status === "resolved" ? "resolved" : item.severity}`}
          >
            {item.status === "resolved"
              ? item.resolution_source === "later_resolved_event" ? "Reconciliado" : "Resolvido"
              : item.severity === "critical"
                ? "Crítico"
                : "Atenção"}
          </span>
        </article>
      ))}
    </div>
  );
}

export function ServiceTable({
  services,
  onSelect,
}: {
  services: ServiceSummary[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="table-scroll">
      <table className="service-table">
        <thead>
          <tr>
            <th>Serviço</th>
            <th>Estado atual</th>
            <th>Disponibilidade¹</th>
            <th>Latência da sonda</th>
            <th>Última coleta</th>
            <th>
              <span className="sr-only">Detalhes</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {services.map((service) => (
            <tr key={service.id}>
              <td>
                <button
                  className="service-link"
                  onClick={() => onSelect(service.id)}
                >
                  <span className="service-icon">
                    {service.id === "postgres" ? (
                      <Database size={18} />
                    ) : service.id === "dns" ? (
                      <Globe2 size={18} />
                    ) : service.id === "smtp" ? (
                      <Mail size={18} />
                    ) : (
                      <Activity size={18} />
                    )}
                  </span>
                  <span>
                    <strong>{service.name}</strong>
                    <small>{service.target}</small>
                  </span>
                </button>
              </td>
              <td>
                <StatusBadge status={service.status} />
              </td>
              <td className="numeric">
                {formatMetric(service.availability_percent)}
                <span className="unit"> %</span>
              </td>
              <td className="numeric">
                {formatMetric(service.latency_ms, 0)}
                <span className="unit"> ms</span>
              </td>
              <td className="muted numeric">{timeLabel(service.checked_at)}</td>
              <td>
                <button
                  className="icon-button"
                  onClick={() => onSelect(service.id)}
                  aria-label={`Ver detalhes de ${service.name}`}
                >
                  <ArrowUpRight size={18} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CollectionNote() {
  return (
    <p className="collection-note">
      <Clock3 size={13} />¹ Percentual de sondas bem-sucedidas nas amostras
      disponíveis do período. Coleta a cada 5 segundos.
    </p>
  );
}
