import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  ChevronRight,
  Database,
  FlaskConical,
  Globe2,
  LayoutDashboard,
  LogOut,
  Mail,
  Network,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Terminal,
  TriangleAlert,
} from "lucide-react";
import { formatMetric, request } from "./api";
import {
  CollectionNote,
  IncidentsList,
  ServiceTable,
  SignalChart,
  StatusBadge,
  timeLabel,
} from "./components";
import LabView from "./Lab";
import PostgresView from "./Postgres";
import DNSView from "./DNS";
import SMTPView from "./SMTP";
import SecurityView from "./Security";
import {
  combinedStatus,
  currentService,
  emptyPostgres,
  emptyDNS,
  emptySMTP,
  servicePage,
} from "./serviceState";
import type {
  DNSOverview,
  SMTPOverview,
  Incident,
  Lab,
  Overview,
  Page,
  PostgresOverview,
  Window,
} from "./types";

const navigation: { id: Page; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Visão geral", icon: LayoutDashboard },
  { id: "service", label: "Serviço HTTP", icon: Server },
  { id: "postgres", label: "PostgreSQL", icon: Database },
  { id: "dns", label: "DNS", icon: Globe2 },
  { id: "smtp", label: "SMTP", icon: Mail },
  { id: "security", label: "Segurança", icon: ShieldCheck },
  { id: "incidents", label: "Incidentes", icon: Bell },
  { id: "lab", label: "Laboratório", icon: FlaskConical },
];
const pageTitles: Record<Page, { title: string; subtitle: string }> = {
  overview: {
    title: "Visão geral",
    subtitle: "O que está acontecendo com seus serviços, agora.",
  },
  service: {
    title: "Aplicação HTTP",
    subtitle: "Disponibilidade, tráfego e tempo de resposta do serviço.",
  },
  postgres: {
    title: "PostgreSQL",
    subtitle: "Consultas, conexões e transações do banco monitorado.",
  },
  dns: {
    title: "DNS",
    subtitle: "Resolução de nomes, consultas e respostas do servidor local.",
  },
  incidents: {
    title: "Incidentes",
    subtitle: "Acompanhe alertas confirmados e a recuperação dos serviços.",
  },
  smtp: {
    title: "SMTP",
    subtitle: "Da aceitação à entrega: volume, fila e falhas do correio local.",
  },
  security: {
    title: "Segurança",
    subtitle: "Tráfego dos serviços e eventos de autenticação do painel.",
  },
  lab: {
    title: "Laboratório",
    subtitle: "Provoque uma falha. Entenda o sinal. Acompanhe a recuperação.",
  },
};

function initialPage(): Page {
  const hash = location.hash.slice(1);
  return navigation.some((item) => item.id === hash)
    ? (hash as Page)
    : "overview";
}

export default function App({
  username,
  onLogout,
  logoutBusy,
  authError,
}: {
  username: string;
  onLogout: () => void;
  logoutBusy: boolean;
  authError: string | null;
}) {
  const [page, setPage] = useState<Page>(initialPage);
  const [window, setWindow] = useState<Window>("15m");
  const [data, setData] = useState<Overview | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [postgres, setPostgres] = useState<PostgresOverview | null>(null);
  const [postgresError, setPostgresError] = useState<string | null>(null);
  const [dnsData, setDNS] = useState<DNSOverview | null>(null);
  const [dnsError, setDNSError] = useState<string | null>(null);
  const [smtpData, setSMTP] = useState<SMTPOverview | null>(null);
  const [smtpError, setSMTPError] = useState<string | null>(null);
  const [lab, setLab] = useState<Lab | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [incidentError, setIncidentError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const change = () => setPage(initialPage());
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let running = false;
    setLoading(true);
    setData(null);
    setPostgres(null);
    setDNS(null);
    setSMTP(null);
    async function load() {
      if (running) return;
      running = true;
      const results = await Promise.allSettled([
        request<Overview>(`/api/overview?window=${window}`, {
          signal: controller.signal,
        }),
        request<{ incidents: Incident[] }>("/api/incidents", {
          signal: controller.signal,
        }),
        request<Lab>("/api/lab", { signal: controller.signal }),
        request<PostgresOverview>(`/api/postgres?window=${window}`, {
          signal: controller.signal,
        }),
        request<DNSOverview>(`/api/dns?window=${window}`, {
          signal: controller.signal,
        }),
        request<SMTPOverview>(`/api/smtp?window=${window}`, {
          signal: controller.signal,
        }),
      ]);
      if (controller.signal.aborted) return;
      const [overview, history, laboratory, database, dns, smtp] = results;
      if (smtp.status === "fulfilled") {
        setSMTP(smtp.value);
        setSMTPError(null);
      } else {
        setSMTP(null);
        setSMTPError(
          smtp.reason instanceof Error
            ? smtp.reason.message
            : "Sem conexão com as métricas SMTP.",
        );
      }
      if (dns.status === "fulfilled") {
        setDNS(dns.value);
        setDNSError(null);
      } else {
        setDNS(null);
        setDNSError(
          dns.reason instanceof Error
            ? dns.reason.message
            : "Sem conexão com as métricas DNS.",
        );
      }
      if (database.status === "fulfilled") {
        setPostgres(database.value);
        setPostgresError(null);
      } else {
        setPostgres(null);
        setPostgresError(
          database.reason instanceof Error
            ? database.reason.message
            : "Sem conexão com as métricas PostgreSQL.",
        );
      }
      if (overview.status === "fulfilled") {
        setData(overview.value);
        setError(null);
      } else {
        setData(null);
        setError(
          overview.reason instanceof Error
            ? overview.reason.message
            : "Sem conexão com a plataforma.",
        );
      }
      if (history.status === "fulfilled") {
        setIncidents(history.value.incidents);
        setIncidentError(false);
      } else setIncidentError(true);
      setLab(laboratory.status === "fulfilled" ? laboratory.value : null);
      setLoading(false);
      running = false;
    }
    void load();
    const timer = setInterval(() => {
      void load();
    }, 5000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [window, refresh]);

  function go(next: Page) {
    location.hash = next;
    setPage(next);
  }
  const activeIncidents = incidents.filter(
    (item) => item.status === "firing",
  ).length;
  const stale =
    data &&
    (now - data.generated_at > 20 ||
      data.service.checked_at == null ||
      now - data.service.checked_at > 20);
  const displayData = data && !stale ? data : null;
  const service = displayData?.service;
  const pgCurrent = postgres
    ? currentService(postgres.service, postgres.generated_at, now)
    : emptyPostgres;
  const pgStale =
    !!postgres &&
    (now - postgres.generated_at > 20 ||
      postgres.service.checked_at == null ||
      now - postgres.service.checked_at > 20);
  const pgDisplay = postgres
    ? {
        ...postgres,
        service: pgCurrent,
        stats: pgStale
          ? {
              ...postgres.stats,
              available: false,
              connections: null,
              connection_limit: null,
              database_bytes: null,
              commits_per_second: null,
              rollbacks_per_second: null,
              qps: null,
            }
          : postgres.stats,
      }
    : null;
  const dnsCurrent = dnsData
    ? currentService(dnsData.service, dnsData.generated_at, now)
    : emptyDNS;
  const dnsStale =
    !!dnsData &&
    (now - dnsData.generated_at > 20 ||
      dnsData.service.checked_at == null ||
      now - dnsData.service.checked_at > 20 ||
      dnsData.service.checked_at > now + 5);
  const dnsDisplay = dnsData
    ? {
        ...dnsData,
        service: dnsCurrent,
        stats: dnsStale
          ? {
              ...dnsData.stats,
              available: false,
              udp_success: null,
              tcp_success: null,
              udp_rcode: null,
              tcp_rcode: null,
              qps: null,
              server_error_percent: null,
              nxdomain_percent: null,
              server_p95_ms: null,
            }
          : dnsData.stats,
      }
    : null;
  const httpCurrent = service ?? {
    id: "web-demo",
    name: "Aplicação HTTP",
    protocol: "HTTP",
    target: "web-demo:8001",
    status: "unknown" as const,
    checked_at: null,
    latency_ms: null,
    availability_percent: null,
  };
  const smtpCurrent = smtpData
    ? currentService(smtpData.service, smtpData.generated_at, now)
    : emptySMTP;
  const smtpStale =
    !!smtpData &&
    (now - smtpData.generated_at > 20 ||
      smtpData.service.checked_at == null ||
      now - smtpData.service.checked_at > 20 ||
      smtpData.service.checked_at > now + 5);
  const smtpDisplay = smtpData
    ? {
        ...smtpData,
        service: smtpCurrent,
        stats: smtpStale
          ? {
              available: false,
              queue: null,
              accepted: null,
              delivered: null,
              failed: null,
              rejected: null,
              last_minute: null,
              last_hour: null,
              delivery_percent: null,
              delivery_p95_ms: null,
              failed_attempts_per_minute: null,
            }
          : smtpData.stats,
      }
    : null;
  const healthStatus =
    page === "overview"
      ? combinedStatus([
          httpCurrent.status,
          pgCurrent.status,
          dnsCurrent.status,
          smtpCurrent.status,
        ])
      : httpCurrent.status;
  const healthy = healthStatus === "ok";
  const title = pageTitles[page];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="#overview" className="brand" aria-label="AulaRedes, início">
          <span className="brand-mark">
            <Network size={22} />
          </span>
          <span>
            Aula<span className="brand-light">Redes</span>
            <small>OBSERVABILIDADE</small>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-icon">
            <Terminal size={18} />
          </span>
          <div>
            <strong>Projeto de redes</strong>
            <small>Laboratório local</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <div className="nav-caption">MONITORAMENTO</div>
        <nav aria-label="Navegação principal">
          {navigation.map(({ id, label, icon: Icon }) => (
            <a
              href={`#${id}`}
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              aria-label={label}
              aria-current={page === id ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "incidents" && activeIncidents > 0 && (
                <span className="nav-count">{activeIncidents}</span>
              )}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="version-pill">
            ETAPA 06 <span>TRÁFEGO E ACESSO</span>
          </div>
          <p>
            Da requisição ao alerta.
            <br />
            Um sinal de cada vez.
          </p>
          <div className="sidebar-author">
            <span>AR</span>
            <div>
              <strong>Trabalho final</strong>
              <small>Redes de Computadores</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Monitoramento</span>
            <ChevronRight size={13} />
            <strong>{title.title}</strong>
          </div>
          <div className="topbar-right">
            <span className="environment">
              <i />
              Ambiente local
            </span>
            <a
              className="icon-button"
              href="http://localhost:8025"
              target="_blank"
              rel="noreferrer"
              aria-label="Abrir e-mails de alerta"
            >
              <Mail size={18} />
            </a>
            <button
              className="icon-button"
              onClick={onLogout}
              disabled={logoutBusy}
              aria-label={`Sair da conta ${username}`}
              title={`Sair da conta ${username}`}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main id="main">
          {authError && (
            <div className="notice error" role="alert">
              {authError}
            </div>
          )}
          <div className="page-heading">
            <div>
              <span className="eyebrow">LABORATÓRIO DE REDES</span>
              <h1>{title.title}</h1>
              <p>{title.subtitle}</p>
            </div>
            <div className="heading-actions">
              {page !== "security" && (
                <label className="window-select">
                  <SlidersHorizontal size={15} />
                  <span className="sr-only">Período dos gráficos</span>
                  <select
                    value={window}
                    onChange={(event) =>
                      setWindow(event.target.value as Window)
                    }
                  >
                    <option value="15m">Últimos 15 minutos</option>
                    <option value="1h">Última hora</option>
                    <option value="6h">Últimas 6 horas</option>
                    <option value="24h">Últimas 24 horas</option>
                  </select>
                </label>
              )}
              <button
                className="icon-button refresh-button"
                onClick={() => setRefresh((value) => value + 1)}
                disabled={loading}
                aria-label="Atualizar métricas"
              >
                <RefreshCw size={17} className={loading ? "spinning" : ""} />
              </button>
            </div>
          </div>
          {error && (
            <div className="notice error" role="alert">
              <TriangleAlert size={18} />
              <span>{error}</span>
              <button
                className="text-button"
                onClick={() => setRefresh((value) => value + 1)}
              >
                Tentar novamente
              </button>
            </div>
          )}
          {stale && (
            <div className="notice error" role="alert">
              A coleta está desatualizada. Os gráficos mostram o histórico
              recebido; o estado atual está sem dados.
            </div>
          )}
          {incidentError && (
            <div className="notice error" role="alert">
              Não foi possível atualizar os incidentes. O histórico exibido pode
              estar desatualizado.
            </div>
          )}
          {page === "security" ? (
            <SecurityView incidents={incidents} refresh={refresh} />
          ) : page === "smtp" ? (
            <SMTPView
              data={smtpDisplay}
              error={smtpError}
              incidents={incidents}
            />
          ) : page === "dns" ? (
            <DNSView data={dnsDisplay} error={dnsError} incidents={incidents} />
          ) : page === "postgres" ? (
            <PostgresView
              data={pgDisplay}
              incidents={incidents}
              error={postgresError}
            />
          ) : page === "lab" ? (
            <LabView
              state={lab}
              onChanged={() => setRefresh((value) => value + 1)}
            />
          ) : page === "incidents" ? (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Histórico de incidentes</h2>
                  <p>
                    Eventos persistidos após confirmação das regras de alerta.
                  </p>
                </div>
                <span className="muted small">Últimos 100 registros</span>
              </div>
              <IncidentsList incidents={incidents} />
            </section>
          ) : (
            <>
              <section
                className={`health-strip ${healthStatus}`}
                aria-live="polite"
              >
                <div className="health-icon">
                  <Radio size={23} />
                </div>
                <div>
                  <strong>
                    {loading
                      ? "Conectando ao laboratório"
                      : healthy
                        ? page === "overview"
                          ? "Seus serviços estão operacionais"
                          : "Seu serviço está operacional"
                        : healthStatus === "critical"
                          ? "Um serviço está indisponível"
                          : healthStatus === "warning"
                            ? "Um serviço exige atenção"
                            : "Aguardando dados do laboratório"}
                  </strong>
                  <p>
                    {healthy
                      ? page === "overview"
                        ? "As sondas HTTP, SQL, DNS e SMTP responderam com sucesso na última verificação."
                        : "A sonda HTTP respondeu com sucesso na última verificação."
                      : healthStatus === "critical"
                        ? "Uma sonda recebeu uma falha. A regra confirmará o incidente após 15 segundos."
                        : healthStatus === "warning"
                          ? "Consulte o detalhe do serviço para verificar latência e conexões. As regras exigem confirmação persistente."
                          : "A primeira coleta pode levar alguns segundos. Dados ausentes não indicam operação normal."}
                  </p>
                </div>
                <div className="live-label">
                  <span
                    className={`live-dot ${displayData ? "connected" : ""}`}
                  />
                  {displayData ? "Coleta ativa" : "Sem coleta"}
                </div>
              </section>
              <div className="metric-strip">
                <div className="metric">
                  <span>
                    Serviços monitorados <Server size={15} />
                  </span>
                  <strong>
                    04<small> / 04 previstos</small>
                  </strong>
                  <p>HTTP, PostgreSQL, DNS e SMTP integrados</p>
                </div>
                <div className="metric">
                  <span>
                    Disponibilidade HTTP <Activity size={15} />
                  </span>
                  <strong>
                    {formatMetric(service?.availability_percent)}
                    <small> %</small>
                  </strong>
                  <p>Calculada sobre as sondas disponíveis</p>
                </div>
                <div className="metric">
                  <span>
                    Latência HTTP p95 <Radio size={15} />
                  </span>
                  <strong>
                    {formatMetric(service?.p95_ms, 0)}
                    <small> ms</small>
                  </strong>
                  <p>95% das requisições abaixo desse valor</p>
                </div>
                <div className="metric">
                  <span>
                    Incidentes ativos <Bell size={15} />
                  </span>
                  <strong>
                    {incidentError
                      ? "—"
                      : String(activeIncidents).padStart(2, "0")}
                  </strong>
                  <p>
                    {activeIncidents
                      ? "Verifique os eventos confirmados"
                      : "Nenhum alerta confirmado em aberto"}
                  </p>
                </div>
              </div>
              {page === "service" && (
                <section className="service-details">
                  <div>
                    <span>Requisições por segundo</span>
                    <strong>
                      {formatMetric(service?.rps, 2)} <small>req/s</small>
                    </strong>
                  </div>
                  <div>
                    <span>Respostas 4xx e 5xx</span>
                    <strong>
                      {formatMetric(service?.error_percent)} <small>%</small>
                    </strong>
                  </div>
                  <div>
                    <span>Estado da sonda</span>
                    <StatusBadge status={service?.status ?? "unknown"} />
                  </div>
                  <button
                    className="button secondary"
                    onClick={() => go("lab")}
                  >
                    Testar falha <FlaskConical size={16} />
                  </button>
                </section>
              )}
              <section className="panel services-panel">
                <div className="panel-heading">
                  <div>
                    <h2>
                      Serviços monitorados{" "}
                      <span className="count-badge">
                        {page === "overview" ? 4 : 1}
                      </span>
                    </h2>
                    <p>Estado observado na última coleta.</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => go(page === "service" ? "lab" : "service")}
                  >
                    {page === "service" ? "Abrir laboratório" : "Ver serviço"}
                    <ArrowRight size={15} />
                  </button>
                </div>
                <ServiceTable
                  services={
                    page === "overview"
                      ? [httpCurrent, pgCurrent, dnsCurrent, smtpCurrent]
                      : [httpCurrent]
                  }
                  onSelect={(id) => go(servicePage(id))}
                />
                <CollectionNote />
              </section>
              <div className="charts-grid">
                <SignalChart
                  data={data?.series ?? []}
                  metric="rps"
                  title="Tráfego HTTP"
                  subtitle="Requisições processadas por segundo"
                  unit="req/s"
                />
                <SignalChart
                  data={data?.series ?? []}
                  metric="latency_ms"
                  title="Tempo de resposta"
                  subtitle="Percentil 95 das requisições HTTP"
                  unit="ms"
                />
              </div>
              <div className="bottom-grid">
                <section className="panel incidents-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Incidentes recentes</h2>
                      <p>Da detecção à recuperação.</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => go("incidents")}
                    >
                      Ver histórico
                      <ArrowRight size={15} />
                    </button>
                  </div>
                  <IncidentsList incidents={incidents} compact />
                </section>
                <aside className="lab-invitation">
                  <span className="invitation-icon">
                    <FlaskConical size={23} />
                  </span>
                  <span className="eyebrow">APRENDA NA PRÁTICA</span>
                  <h2>E se o serviço parar?</h2>
                  <p>
                    Provoque lentidão ou indisponibilidade e acompanhe o caminho
                    da falha até o alerta por e-mail.
                  </p>
                  <button className="button primary" onClick={() => go("lab")}>
                    Explorar laboratório <ArrowUpRight size={17} />
                  </button>
                </aside>
              </div>
            </>
          )}
          <footer className="page-footer">
            <span>
              <span className={`live-dot ${displayData ? "connected" : ""}`} />
              {displayData
                ? `Atualizado às ${timeLabel(displayData.generated_at)}`
                : "Aguardando conexão"}
              <b>·</b>Atualização a cada 5 s
            </span>
            <span>
              AulaRedes <b>/</b> HTTP · SQL · DNS · SMTP{" "}
              <span className="version">v0.6</span>
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
