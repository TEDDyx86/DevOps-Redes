import { ArrowUpRight, Mail, Terminal, TriangleAlert } from "lucide-react";
import { formatMetric } from "./api";
import {
  CollectionNote,
  IncidentsList,
  SignalChart,
  StatusBadge,
  timeLabel,
} from "./components";
import type { Incident, SMTPOverview } from "./types";

export default function SMTPView({
  data,
  error,
  incidents,
}: {
  data: SMTPOverview | null;
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
          <Mail size={22} />
        </div>
        <div>
          <strong>
            {service?.status === "ok"
              ? "SMTP aceita conexões e comandos"
              : service?.status === "critical"
                ? "O servidor SMTP não respondeu à sonda"
                : service?.status === "warning"
                  ? "A fila ou a resposta SMTP exige atenção"
                  : "Aguardando coleta SMTP"}
          </strong>
          <p>
            EHLO + NOOP · Última verificação:{" "}
            {timeLabel(service?.checked_at ?? null)}.
          </p>
        </div>
        <StatusBadge status={service?.status ?? "unknown"} />
      </section>
      {data && !stats?.available && (
        <div className="notice error" role="status">
          Estatísticas de entrega indisponíveis. A sonda de conexão é medida
          separadamente.
        </div>
      )}
      <div className="metric-strip">
        <div className="metric">
          <span>
            Mensagens na fila <Mail size={15} />
          </span>
          <strong>{formatMetric(stats?.queue, 0)}</strong>
          <p>Aceitas, aguardando confirmação do receptor</p>
        </div>
        <div className="metric">
          <span>Aceitas no último minuto</span>
          <strong>
            {formatMetric(stats?.last_minute, 0)}
            <small> mensagens</small>
          </strong>
          <p>{formatMetric(stats?.last_hour, 0)} na última hora</p>
        </div>
        <div className="metric">
          <span>Entregues do total aceito</span>
          <strong>
            {formatMetric(stats?.delivery_percent)}
            <small> %</small>
          </strong>
          <p>
            {formatMetric(stats?.delivered, 0)} entregues /{" "}
            {formatMetric(stats?.accepted, 0)} aceitas desde o início
          </p>
        </div>
        <div className="metric">
          <span>Tempo de entrega · p95</span>
          <strong>
            {formatMetric(stats?.delivery_p95_ms)}
            <small> ms</small>
          </strong>
          <p>Aceitação → receptor local · janela de 1 min</p>
        </div>
      </div>
      <section className="service-details panel smtp-summary">
        <div>
          <span>Servidor monitorado</span>
          <strong>smtp:2525</strong>
        </div>
        <div>
          <span>Resposta EHLO + NOOP</span>
          <strong>
            {formatMetric(service?.latency_ms)} <small>ms</small>
          </strong>
        </div>
        <div>
          <span>Disponibilidade da sonda</span>
          <strong>
            {formatMetric(service?.availability_percent)} <small>%</small>
          </strong>
        </div>
        <a
          className="button secondary"
          href="http://localhost:8026"
          target="_blank"
          rel="noreferrer"
        >
          Caixa SMTP <ArrowUpRight size={16} />
        </a>
      </section>
      <div className="charts-grid">
        <SignalChart
          data={data?.series ?? []}
          metric="messages_per_minute"
          title="Volume aceito"
          subtitle="Taxa de aceitação calculada sobre 1 minuto"
          unit="msg/min"
        />
        <SignalChart
          data={data?.series ?? []}
          metric="latency_ms"
          title="Tempo até a entrega"
          subtitle="p95 das mensagens entregues, incluindo espera na fila"
          unit="ms"
        />
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>O caminho da mensagem</h2>
            <p>
              Confirmar a aceitação é o primeiro passo; a entrega exige resposta
              do receptor.
            </p>
          </div>
        </div>
        <div className="service-details smtp-path">
          <div>
            <span>Aceitas · acumulado</span>
            <strong>{formatMetric(stats?.accepted, 0)}</strong>
          </div>
          <div>
            <span>Entregues · acumulado</span>
            <strong>{formatMetric(stats?.delivered, 0)}</strong>
          </div>
          <div>
            <span>Falhas definitivas · acumulado</span>
            <strong>{formatMetric(stats?.failed, 0)}</strong>
          </div>
          <div>
            <span>Destinatários rejeitados · acumulado</span>
            <strong>{formatMetric(stats?.rejected, 0)}</strong>
          </div>
          <div>
            <span>Tentativas de entrega com falha</span>
            <strong>
              {formatMetric(stats?.failed_attempts_per_minute)}{" "}
              <small>/min</small>
            </strong>
          </div>
        </div>
        <CollectionNote />
        <p className="muted small smtp-note">
          Tráfego local a cada 15 s para aluno@aularedes.test. A caixa mantém as
          200 mensagens mais recentes. Os totais persistem na fila. Entrega
          confirma o Mailpit local; não mede leitura pelo destinatário.
        </p>
      </section>
      <div className="bottom-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Incidentes SMTP</h2>
              <p>Fila, disponibilidade e recuperação.</p>
            </div>
          </div>
          <IncidentsList
            incidents={incidents.filter((item) => item.service === "smtp")}
            compact
          />
        </section>
        <section className="panel postgres-runbook smtp-runbook">
          <div className="panel-heading">
            <div>
              <h2>Teste de fila e recuperação</h2>
              <p>Execute no terminal da pasta do projeto.</p>
            </div>
            <Terminal size={18} />
          </div>
          <ol className="runbook-steps">
            <li>
              <strong>Pare o receptor</strong>
              <code>docker compose stop smtp-inbox</code>
              <p>O SMTP aceita mensagens. A fila ≥5 gera aviso após 30 s.</p>
            </li>
            <li>
              <strong>Retome a entrega</strong>
              <code>docker compose start smtp-inbox</code>
              <p>As mensagens pendentes chegam à caixa SMTP.</p>
            </li>
            <li>
              <strong>Teste a indisponibilidade</strong>
              <code>docker compose stop smtp</code>
              <p>
                Alerta crítico após 15 s. Recupere com{" "}
                <code>docker compose start smtp</code>.
              </p>
            </li>
          </ol>
          <a
            className="text-button"
            href="http://localhost:8025"
            target="_blank"
            rel="noreferrer"
          >
            E-mails de alerta · caixa separada <ArrowUpRight size={14} />
          </a>
        </section>
      </div>
    </>
  );
}
