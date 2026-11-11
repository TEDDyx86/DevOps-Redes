import { ArrowUpRight, Database, Terminal, TriangleAlert } from "lucide-react";
import { formatMetric } from "./api";
import {
  CollectionNote,
  IncidentsList,
  SignalChart,
  StatusBadge,
  timeLabel,
} from "./components";
import type { Incident, PostgresOverview } from "./types";

export function PostgresRunbook() {
  return (
    <section className="panel postgres-runbook">
      <div className="panel-heading">
        <div>
          <h2>
            <Terminal size={16} /> Testar a interrupção do banco
          </h2>
          <p>
            Execute na pasta do projeto. O dashboard e o histórico permanecem
            disponíveis.
          </p>
        </div>
      </div>
      <div className="runbook-steps">
        <div>
          <span>1. Parar somente o banco</span>
          <code>docker compose stop postgres</code>
        </div>
        <div>
          <span>2. Aguardar o incidente e conferir o e-mail</span>
          <p>
            A regra exige 15 s de falha observada, além dos intervalos de coleta
            e avaliação.
          </p>
        </div>
        <div>
          <span>3. Restaurar o serviço</span>
          <code>docker compose start postgres</code>
        </div>
      </div>
      <p className="collection-note">
        A parada é real e controlada pelo terminal. A API não recebe acesso ao
        mecanismo Docker.
      </p>
    </section>
  );
}

export default function PostgresView({
  data,
  incidents,
  error,
}: {
  data: PostgresOverview | null;
  incidents: Incident[];
  error: string | null;
}) {
  const service = data?.service;
  const stats = data?.stats;
  const diskValues = [stats?.disk_read_ms, stats?.disk_write_ms].filter(
    (value): value is number => value !== null && value !== undefined,
  );
  const diskLatency =
    diskValues.length > 0
      ? diskValues.reduce((total, value) => total + value, 0) /
        diskValues.length
      : null;
  const databaseIncidents = incidents.filter(
    (item) => item.service === "postgres",
  );
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
          <Database size={22} />
        </div>
        <div>
          <strong>
            {service?.status === "ok"
              ? "PostgreSQL responde às consultas"
              : service?.status === "critical"
                ? "Não foi possível consultar o PostgreSQL"
                : service?.status === "warning"
                  ? "PostgreSQL exige atenção"
                  : "Aguardando coleta do PostgreSQL"}
          </strong>
          <p>
            Verificação real de conexão e SELECT 1. Última sonda:{" "}
            {timeLabel(service?.checked_at ?? null)}.
          </p>
        </div>
        <StatusBadge status={service?.status ?? "unknown"} />
      </section>
      <div className="metric-strip">
        <div className="metric">
          <span>Disponibilidade SQL</span>
          <strong>
            {formatMetric(service?.availability_percent)}
            <small> %</small>
          </strong>
          <p>Sondas bem-sucedidas no período</p>
        </div>
        <div className="metric">
          <span>Conexão + SELECT 1</span>
          <strong>
            {formatMetric(service?.latency_ms, 0)}
            <small> ms</small>
          </strong>
          <p>Inclui abertura da conexão SQL</p>
        </div>
        <div className="metric">
          <span>Conexões abertas</span>
          <strong>
            {formatMetric(stats?.connections, 0)}
            <small> / {formatMetric(stats?.connection_limit, 0)}</small>
          </strong>
          <p>
            Ativas {formatMetric(stats?.connections_active, 0)} · ociosas{" "}
            {formatMetric(stats?.connections_idle, 0)}
          </p>
        </div>
        <div className="metric">
          <span>Tamanho do banco</span>
          <strong>
            {formatMetric(
              stats?.database_bytes == null
                ? null
                : stats.database_bytes / 1048576,
            )}
            <small> MiB</small>
          </strong>
          <p>Medido por pg_database_size</p>
        </div>
      </div>
      {service?.status === "ok" && !stats?.available && (
        <div className="notice error" role="alert">
          SQL responde, mas as estatísticas estão indisponíveis. Verifique a
          extensão pg_stat_statements e as permissões do monitor.
        </div>
      )}
      <section className="service-details sql-details">
        <div>
          <span>Comandos SQL do laboratório</span>
          <strong>
            {formatMetric(stats?.qps, 2)} <small>comandos/s</small>
          </strong>
        </div>
        <div>
          <span>Transações confirmadas</span>
          <strong>
            {formatMetric(stats?.commits_per_second, 2)}{" "}
            <small>commits/s</small>
          </strong>
        </div>
        <div>
          <span>Transações desfeitas</span>
          <strong>
            {formatMetric(stats?.rollbacks_per_second, 2)}{" "}
            <small>rollbacks/s</small>
          </strong>
        </div>
        <div>
          <span>Consultas lentas</span>
          <strong>
            {formatMetric(stats?.slow_statements, 0)}{" "}
            <small>acima de 100 ms</small>
          </strong>
        </div>
        <div>
          <span>Latência de disco</span>
          <strong>
            {formatMetric(diskLatency, 2)} <small>ms</small>
          </strong>
        </div>
        <div>
          <span>Crescimento do banco</span>
          <strong>
            {formatMetric(
              stats?.growth_bytes_per_day == null
                ? null
                : stats.growth_bytes_per_day / 1024 ** 3,
              3,
            )}{" "}
            <small>GiB/dia</small>
          </strong>
        </div>
      </section>
      <div className="charts-grid">
        <SignalChart
          data={data?.series ?? []}
          metric="qps"
          title="Atividade SQL"
          subtitle="Comandos executados pelo usuário de laboratório"
          unit="comandos/s"
        />
        <SignalChart
          data={data?.series ?? []}
          metric="latency_ms"
          title="Tempo de conexão e consulta"
          subtitle="Duração da conexão SQL e SELECT 1, por sonda"
          unit="ms"
        />
      </div>
      <div className="sql-collection-note">
        <CollectionNote />
      </div>
      <div className="bottom-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Incidentes do PostgreSQL</h2>
              <p>Alertas confirmados e resoluções registradas.</p>
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
          <IncidentsList incidents={databaseIncidents} compact />
        </section>
        <aside className="lab-invitation">
          <span className="eyebrow">CARGA REAL E LIMITADA</span>
          <h2>SQL em movimento.</h2>
          <p>
            Um usuário restrito lê e atualiza uma tabela de 1.000 registros a
            cada 2 s. Uma em cada cinco transações é desfeita intencionalmente.
          </p>
          <p className="workload-note">
            Comandos/s vêm do pg_stat_statements. Commits e rollbacks incluem
            também conexões de monitoramento. A latência de disco vem dos
            contadores de I/O do próprio PostgreSQL (pg_stat_io).
          </p>
        </aside>
      </div>
      <PostgresRunbook />
    </>
  );
}
