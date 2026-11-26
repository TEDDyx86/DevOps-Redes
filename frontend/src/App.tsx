import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  ChevronRight,
  Database,
  Globe2,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Swords,
  TriangleAlert,
} from "lucide-react";
import { formatMetric, request } from "./api";
import Sidebar from "./Sidebar";
import {
  readSidebarPreference,
  saveSidebarPreference,
} from "./sidebarPreference";
import {
  IncidentsList,
  ServiceDetails,
  SignalChart,
  StatusBadge,
  timeLabel,
} from "./components";
import LabView from "./Lab";
import PostgresView from "./Postgres";
import DNSView from "./DNS";
import SMTPView from "./SMTP";
import SecurityView from "./Security";
import ResourcesView from "./Resources";
import IncidentsView from "./Incidents";
import AttacksView from "./Attacks";
import {
  combinedStatus,
  currentService,
  emptyPostgres,
  emptyDNS,
  emptySMTP,
} from "./serviceState";
import type {
  DNSOverview,
  SMTPOverview,
  Incident,
  Lab,
  LiveAlerts,
  Overview,
  Page,
  PostgresOverview,
  Window,
} from "./types";

const ALL_PAGES: Page[] = [
  "overview",
  "service",
  "postgres",
  "dns",
  "smtp",
  "resources",
  "security",
  "incidents",
  "lab",
  "attacks",
];

const navigation: { id: Page; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Visão geral", icon: LayoutDashboard },
  { id: "service", label: "Serviços", icon: Server },
  { id: "security", label: "Segurança", icon: ShieldCheck },
  { id: "incidents", label: "Incidentes", icon: Bell },
  { id: "attacks", label: "Ataques & Lab", icon: Swords },
];

const SERVICE_TABS: { id: Page; label: string }[] = [
  { id: "service", label: "Aplicação HTTP" },
  { id: "postgres", label: "PostgreSQL" },
  { id: "dns", label: "DNS" },
  { id: "smtp", label: "SMTP" },
  { id: "resources", label: "Recursos (CPU/RAM/I/O)" },
];

const ATTACK_TABS: { id: Page; label: string }[] = [
  { id: "attacks", label: "Ataques automatizados (11)" },
  { id: "lab", label: "Laboratório manual" },
];

const pageTitles: Record<Page, { title: string; subtitle: string }> = {
  resources: {
    title: "Recursos",
    subtitle: "Como cada serviço utiliza CPU, memória e armazenamento.",
  },
  overview: {
    title: "Visão geral",
    subtitle: "Sala de controle: disponibilidade, desempenho e alertas dos 4 serviços.",
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
    subtitle: "Vulnerabilidades, integridade dos arquivos, tráfego e acesso ao painel.",
  },
  lab: {
    title: "Laboratório",
    subtitle: "Provoque uma falha. Entenda o sinal. Acompanhe a recuperação.",
  },
  attacks: {
    title: "Ataques",
    subtitle: "Simule incidentes controlados e acompanhe os alertas no Prometheus em tempo real.",
  },
};

function initialPage(): Page {
  const hash = location.hash.slice(1) as Page;
  return ALL_PAGES.includes(hash) ? hash : "overview";
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
  const [liveAlerts, setLiveAlerts] = useState<LiveAlerts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [incidentError, setIncidentError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const [collapsed, setCollapsed] = useState(readSidebarPreference);
  const [mobileOpen, setMobileOpen] = useState(false);

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
    globalThis.scrollTo?.({ top: 0, behavior: "instant" });
  }, [page]);

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
        request<LiveAlerts>("/api/alerts/live", {
          signal: controller.signal,
        }),
      ]);
      if (controller.signal.aborted) return;
      const [overview, history, laboratory, database, dns, smtp, live] = results;
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
      setLiveAlerts(live.status === "fulfilled" ? live.value : null);
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

  const triggerRefresh = useCallback(() => {
    setRefresh((value) => value + 1);
  }, []);

  function go(next: Page) {
    location.hash = next;
    setPage(next);
  }

  function toggleSidebar() {
    setCollapsed((previous) => {
      const value = !previous;
      saveSidebarPreference(value);
      return value;
    });
  }

  const activeIncidents = incidents.filter(
    (item) => item.status === "firing",
  ).length;
  const httpIncidents = incidents.filter((item) => item.service === "web-demo");
  const httpActiveIncidents = httpIncidents.filter(
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
  const sidebarPage: Page = ["service", "postgres", "dns", "smtp", "resources"].includes(page)
    ? "service"
    : ["attacks", "lab"].includes(page)
      ? "attacks"
      : page;

  return (
    <div
      className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${
        mobileOpen ? "sidebar-open" : ""
      }`}
    >
      {mobileOpen && (
        <div
          className="sidebar-overlay"
          aria-hidden="true"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <Sidebar
        navigation={navigation}
        page={sidebarPage}
        activeIncidents={activeIncidents}
        collapsed={collapsed}
        onToggle={toggleSidebar}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              type="button"
              className="icon-button menu-button mobile-only"
              onClick={() => setMobileOpen(true)}
              aria-label="Abrir navegação"
            >
              <Menu size={18} />
            </button>
            <span>Monitoramento</span>
            <ChevronRight size={13} />
            <strong>{title.title}</strong>
          </div>
          <div className="topbar-right">
            {liveAlerts &&
              (liveAlerts.firing.length > 0 || liveAlerts.pending.length > 0) && (
                <a
                  href="#incidents"
                  className={`topbar-alert-pill ${
                    liveAlerts.firing.length > 0 ? "firing" : "pending"
                  }`}
                  title="Alertas em andamento no Prometheus"
                >
                  <i />
                  {liveAlerts.firing.length > 0
                    ? `${liveAlerts.firing.length} ${liveAlerts.firing.length === 1 ? "alerta ativo" : "alertas ativos"}`
                    : `${liveAlerts.pending.length} detectando (pending)`}
                </a>
              )}
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
              {!["security", "incidents", "lab", "attacks"].includes(page) && (
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
          {sidebarPage === "service" && (
            <div className="sub-tabs" role="navigation" aria-label="Serviços e recursos">
              {SERVICE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`filter-pill ${page === tab.id ? "active" : ""}`}
                  onClick={() => go(tab.id)}
                  aria-current={page === tab.id ? "page" : undefined}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
          {sidebarPage === "attacks" && (
            <div className="sub-tabs" role="navigation" aria-label="Simulação e ataques">
              {ATTACK_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`filter-pill ${page === tab.id ? "active" : ""}`}
                  onClick={() => go(tab.id)}
                  aria-current={page === tab.id ? "page" : undefined}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
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
          {page === "resources" ? (
            <ResourcesView window={window} refresh={refresh} incidents={incidents}/>
          ) : page === "security" ? (
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
            <LabView state={lab} onChanged={triggerRefresh} />
          ) : page === "attacks" ? (
            <AttacksView
              onChanged={triggerRefresh}
              services={[httpCurrent, pgCurrent, dnsCurrent, smtpCurrent]}
              liveAlerts={liveAlerts}
            />
          ) : page === "incidents" ? (
            <IncidentsView incidents={incidents} liveAlerts={liveAlerts} />
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
              {page === "service" ? (
                <>
                  <div className="metric-strip">
                    <div className="metric">
                      <span>
                        Latência da sonda <Activity size={15} />
                      </span>
                      <strong>
                        {formatMetric(service?.latency_ms, 0)}
                        <small> ms</small>
                      </strong>
                      <p>Tempo da última verificação /health</p>
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
                        Incidentes HTTP ativos <Bell size={15} />
                      </span>
                      <strong>
                        {incidentError
                          ? "—"
                          : String(httpActiveIncidents).padStart(2, "0")}
                      </strong>
                      <p>
                        {httpActiveIncidents
                          ? "Verifique os eventos confirmados"
                          : "Nenhum alerta confirmado em aberto"}
                      </p>
                    </div>
                  </div>
                  <ServiceDetails
                    service={service}
                    onTestFailure={() => go("attacks")}
                  />
                </>
              ) : (
                <section className="control-grid" aria-label="Serviços monitorados">
                  <article className={`panel control-card status-${httpCurrent.status}`}>
                    <div className="control-card-head">
                      <div>
                        <h2>
                          <Server size={16} /> Aplicação HTTP
                        </h2>
                        <p>{httpCurrent.target} · Workbyte Store</p>
                      </div>
                      <StatusBadge status={httpCurrent.status} />
                    </div>
                    <div className="control-metrics">
                      <div>
                        <span>Disponib.</span>
                        <strong>{formatMetric(httpCurrent.availability_percent)} %</strong>
                      </div>
                      <div>
                        <span>RPS</span>
                        <strong>{formatMetric(service?.rps, 2)}</strong>
                      </div>
                      <div>
                        <span>Latência p95</span>
                        <strong>{formatMetric(service?.p95_ms, 0)} ms</strong>
                      </div>
                      <div>
                        <span>Erros 4xx/5xx</span>
                        <strong>{formatMetric(service?.error_percent)} %</strong>
                      </div>
                    </div>
                    <div className="control-card-foot">
                      <span>
                        Conexões ativas: {formatMetric(service?.connections ?? null, 0)} · Sonda:{" "}
                        {formatMetric(httpCurrent.latency_ms, 0)} ms
                      </span>
                      <button className="text-button" onClick={() => go("service")}>
                        Detalhes <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>

                  <article className={`panel control-card status-${pgCurrent.status}`}>
                    <div className="control-card-head">
                      <div>
                        <h2>
                          <Database size={16} /> PostgreSQL
                        </h2>
                        <p>{pgCurrent.target}</p>
                      </div>
                      <StatusBadge status={pgCurrent.status} />
                    </div>
                    <div className="control-metrics">
                      <div>
                        <span>Disponib.</span>
                        <strong>{formatMetric(pgCurrent.availability_percent)} %</strong>
                      </div>
                      <div>
                        <span>QPS</span>
                        <strong>{formatMetric(pgDisplay?.stats.qps, 2)}</strong>
                      </div>
                      <div>
                        <span>Conexões</span>
                        <strong>
                          {formatMetric(pgDisplay?.stats.connections, 0)} /{" "}
                          {formatMetric(pgDisplay?.stats.connection_limit, 0)}
                        </strong>
                      </div>
                      <div>
                        <span>Slow (&gt;100ms)</span>
                        <strong>{formatMetric(pgDisplay?.stats.slow_statements, 0)}</strong>
                      </div>
                    </div>
                    <div className="control-card-foot">
                      <span>
                        Tamanho:{" "}
                        {formatMetric(
                          pgDisplay?.stats.database_bytes == null
                            ? null
                            : pgDisplay.stats.database_bytes / 1048576,
                        )}{" "}
                        MiB · Rollbacks: {formatMetric(pgDisplay?.stats.rollbacks_per_second, 2)}/s
                      </span>
                      <button className="text-button" onClick={() => go("postgres")}>
                        Detalhes <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>

                  <article className={`panel control-card status-${dnsCurrent.status}`}>
                    <div className="control-card-head">
                      <div>
                        <h2>
                          <Globe2 size={16} /> DNS CoreDNS
                        </h2>
                        <p>{dnsCurrent.target}</p>
                      </div>
                      <StatusBadge status={dnsCurrent.status} />
                    </div>
                    <div className="control-metrics">
                      <div>
                        <span>Disponib.</span>
                        <strong>{formatMetric(dnsCurrent.availability_percent)} %</strong>
                      </div>
                      <div>
                        <span>QPS</span>
                        <strong>{formatMetric(dnsDisplay?.stats.qps, 2)}</strong>
                      </div>
                      <div>
                        <span>Resolução</span>
                        <strong>{formatMetric(dnsCurrent.latency_ms, 1)} ms</strong>
                      </div>
                      <div>
                        <span>Erros serv.</span>
                        <strong>{formatMetric(dnsDisplay?.stats.server_error_percent)} %</strong>
                      </div>
                    </div>
                    <div className="control-card-foot">
                      <span>
                        UDP: {dnsDisplay?.stats.udp_rcode ?? "—"} · TCP:{" "}
                        {dnsDisplay?.stats.tcp_rcode ?? "—"} · NXDOMAIN:{" "}
                        {formatMetric(dnsDisplay?.stats.nxdomain_percent)} %
                      </span>
                      <button className="text-button" onClick={() => go("dns")}>
                        Detalhes <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>

                  <article className={`panel control-card status-${smtpCurrent.status}`}>
                    <div className="control-card-head">
                      <div>
                        <h2>
                          <Mail size={16} /> SMTP Local
                        </h2>
                        <p>{smtpCurrent.target} · aiosmtpd</p>
                      </div>
                      <StatusBadge status={smtpCurrent.status} />
                    </div>
                    <div className="control-metrics">
                      <div>
                        <span>Disponib.</span>
                        <strong>{formatMetric(smtpCurrent.availability_percent)} %</strong>
                      </div>
                      <div>
                        <span>Fila</span>
                        <strong>{formatMetric(smtpDisplay?.stats.queue, 0)}</strong>
                      </div>
                      <div>
                        <span>Entrega</span>
                        <strong>{formatMetric(smtpDisplay?.stats.delivery_percent)} %</strong>
                      </div>
                      <div>
                        <span>Latência p95</span>
                        <strong>{formatMetric(smtpDisplay?.stats.delivery_p95_ms, 0)} ms</strong>
                      </div>
                    </div>
                    <div className="control-card-foot">
                      <span>
                        Última hora: {formatMetric(smtpDisplay?.stats.last_hour, 0)} msg ·
                        Rejeições: {formatMetric(smtpDisplay?.stats.rejected, 0)}
                      </span>
                      <button className="text-button" onClick={() => go("smtp")}>
                        Detalhes <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>
                </section>
              )}
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
                      <h2>
                        {page === "service" ? "Incidentes HTTP" : "Incidentes recentes"}
                      </h2>
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
                  <IncidentsList
                    incidents={page === "service" ? httpIncidents : incidents}
                    compact
                  />
                </section>
                <aside className="lab-invitation">
                  <span className="invitation-icon">
                    <Swords size={23} />
                  </span>
                  <span className="eyebrow">SIMULAÇÃO AO VIVO</span>
                  <h2>Teste um ataque agora.</h2>
                  <p>
                    Dispare falhas ou floods controlados e acompanhe alertas
                    pending/firing em tempo real.
                  </p>
                  <button className="button primary" onClick={() => go("attacks")}>
                    Abrir ataques <ArrowUpRight size={17} />
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
              <span className="version">v0.8</span>
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
