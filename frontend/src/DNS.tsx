import { ArrowUpRight, Globe2, Terminal, TriangleAlert } from "lucide-react";
import { formatMetric } from "./api";
import {
  CollectionNote,
  IncidentsList,
  SignalChart,
  StatusBadge,
  timeLabel,
} from "./components";
import type { DNSOverview, Incident } from "./types";

function protocolState(value: boolean | null | undefined) {
  return value == null ? "unknown" : value ? "ok" : "critical";
}

export default function DNSView({
  data,
  error,
  incidents,
}: {
  data: DNSOverview | null;
  error: string | null;
  incidents: Incident[];
}) {
  const service = data?.service;
  const stats = data?.stats;
  return (
    <>
      {error && (
        <div className="notice error" role="alert">
          <TriangleAlert size={17} />
          {error}
        </div>
      )}
      <section className={`health-strip ${service?.status ?? "unknown"}`}>
        <div className="health-icon">
          <Globe2 size={22} />
        </div>
        <div>
          <strong>
            {service?.status === "ok"
              ? "DNS resolve o registro esperado"
              : service?.status === "critical"
                ? "A resolução DNS falhou ou retornou outro registro"
                : service?.status === "warning"
                  ? "A resolução DNS exige atenção"
                  : "Aguardando coleta DNS"}
          </strong>
          <p>
            Sondas independentes em UDP e TCP. Última verificação:{" "}
            {timeLabel(service?.checked_at ?? null)}.
          </p>
        </div>
        <StatusBadge status={service?.status ?? "unknown"} />
      </section>
      <div className="metric-strip">
        <div className="metric">
          <span>Disponibilidade DNS</span>
          <strong>
            {formatMetric(service?.availability_percent)}
            <small> %</small>
          </strong>
          <p>Registro correto em ambos os protocolos</p>
        </div>
        <div className="metric">
          <span>Tempo de resolução</span>
          <strong>
            {formatMetric(service?.latency_ms, 1)}
            <small> ms</small>
          </strong>
          <p>Maior duração entre UDP e TCP</p>
        </div>
        <div className="metric">
          <span>Consultas por segundo</span>
          <strong>
            {formatMetric(stats?.qps, 2)}
            <small> consultas/s</small>
          </strong>
          <p>Contador nativo do CoreDNS</p>
        </div>
        <div className="metric">
          <span>Erros do servidor</span>
          <strong>
            {formatMetric(stats?.server_error_percent)}
            <small> %</small>
          </strong>
          <p>NXDOMAIN acompanhado separadamente</p>
        </div>
      </div>
      {service?.status === "ok" && !stats?.available && (
        <div className="notice error" role="alert">
          A resolução funciona, mas as métricas do CoreDNS estão indisponíveis.
          Verifique o alvo DNS no Prometheus.
        </div>
      )}
      <section className="panel dns-record">
        <div className="panel-heading">
          <div>
            <h2>Registro verificado</h2>
            <p>Zona local de teste. Não altera o DNS do seu computador.</p>
          </div>
          <span className="count-badge">A</span>
        </div>
        <div className="dns-record-details">
          <div>
            <span>Nome consultado</span>
            <code>{data?.question.name ?? "app.aularedes.test."}</code>
          </div>
          <div>
            <span>Endereço esperado</span>
            <code>{data?.question.expected ?? "192.0.2.10"}</code>
          </div>
          <div>
            <span>
              UDP <small>{stats?.udp_rcode ?? "Sem resposta"}</small>
            </span>
            <StatusBadge status={protocolState(stats?.udp_success)} />
          </div>
          <div>
            <span>
              TCP <small>{stats?.tcp_rcode ?? "Sem resposta"}</small>
            </span>
            <StatusBadge status={protocolState(stats?.tcp_success)} />
          </div>
        </div>
      </section>
      <div className="charts-grid">
        <SignalChart
          data={data?.series ?? []}
          metric="qps"
          title="Consultas DNS"
          subtitle="Consultas recebidas pelo servidor, incluindo as sondas"
          unit="consultas/s"
        />
        <SignalChart
          data={data?.series ?? []}
          metric="latency_ms"
          title="Tempo de resolução"
          subtitle="Maior duração das sondas UDP/TCP, sem cache no cliente"
          unit="ms"
        />
      </div>
      <div className="sql-collection-note">
        <CollectionNote />
      </div>
      <section className="service-details dns-secondary">
        <div>
          <span>Nomes inexistentes, NXDOMAIN</span>
          <strong>
            {formatMetric(stats?.nxdomain_percent)} <small>%</small>
          </strong>
        </div>
        <div>
          <span>Processamento no servidor, p95</span>
          <strong>
            {formatMetric(stats?.server_p95_ms, 2)} <small>ms</small>
          </strong>
        </div>
        <p>
          NXDOMAIN significa nome inexistente. O gerador consulta um nome
          ausente de propósito, sem disparar alerta de indisponibilidade.
        </p>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Incidentes DNS</h2>
            <p>Alertas confirmados e recuperações registradas.</p>
          </div>
          <a
            className="text-button"
            href="http://localhost:8025"
            target="_blank"
            rel="noreferrer"
          >
            Ver e-mails <ArrowUpRight size={15} />
          </a>
        </div>
        <IncidentsList
          incidents={incidents.filter((item) => item.service === "dns")}
          compact
        />
      </section>
      <section className="panel postgres-runbook">
        <div className="panel-heading">
          <div>
            <h2>
              <Terminal size={16} />
              Testar uma falha DNS
            </h2>
            <p>
              Execute na pasta do projeto. HTTP, SQL e o histórico continuam
              disponíveis.
            </p>
          </div>
        </div>
        <div className="runbook-steps">
          <div>
            <span>1. Parar somente o DNS</span>
            <code>docker compose stop dns</code>
          </div>
          <div>
            <span>2. Acompanhar o alerta</span>
            <p>
              Após 15 s de falha observada, confira o incidente e o e-mail
              local.
            </p>
          </div>
          <div>
            <span>3. Restaurar a resolução</span>
            <code>docker compose start dns</code>
          </div>
        </div>
        <p className="collection-note">
          Os endereços 192.0.2.x são registros de documentação usados apenas
          nesta zona de teste.
        </p>
      </section>
    </>
  );
}
