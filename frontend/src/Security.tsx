import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck, TriangleAlert } from "lucide-react";
import { request } from "./api";
import { IncidentsList, timeLabel } from "./components";
import type { Incident } from "./types";
import Traffic from "./Traffic";
import Integrity from "./Integrity";

interface SecurityData {
  generated_at: number;
  window_seconds: number;
  ip_limit: number;
  account_limit: number;
  totals: { success: number; failure: number; blocked: number };
  failures_recent: { ip: number; account: number };
  blocked_recent: number;
  events: {
    id: number;
    at: number;
    username: string;
    ip: string;
    outcome: string;
  }[];
}
const outcomes: Record<string, string> = {
  success: "Entrada autorizada",
  failure: "Credencial inválida",
  blocked: "Tentativa bloqueada",
  logout: "Sessão encerrada",
};

export default function Security({
  incidents,
  refresh,
}: {
  incidents: Incident[];
  refresh: number;
}) {
  const [data, setData] = useState<SecurityData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let running = false;
    async function load() {
      if (running) return;
      running = true;
      try {
        const value = await request<SecurityData>("/api/security", {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setData(value);
          setError(null);
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setData(null);
          setError(
            reason instanceof Error ? reason.message : "Eventos indisponíveis.",
          );
        }
      } finally {
        running = false;
      }
    }
    void load();
    const timer = setInterval(() => {
      void load();
    }, 5000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [refresh]);
  const suspect =
    !!data &&
    (data.failures_recent.ip >= data.ip_limit ||
      data.failures_recent.account >= data.account_limit);
  return (
    <>
      <Integrity refresh={refresh} incidents={incidents} />
      <Traffic refresh={refresh} incidents={incidents} />
      <h2 className="security-section-title">Acesso ao painel</h2>
      {error && (
        <div className="notice error" role="alert">
          <TriangleAlert size={17} />
          {error}
        </div>
      )}
      <section
        className={`health-strip ${data ? (suspect ? "warning" : "ok") : "unknown"}`}
      >
        <div className="health-icon">
          <ShieldCheck size={22} />
        </div>
        <div>
          <strong>
            {data
              ? suspect
                ? "Tentativas repetidas de acesso detectadas"
                : "Nenhum limite de falhas atingido na última janela"
              : "Aguardando eventos de autenticação"}
          </strong>
          <p>
            Proteção do acesso ao painel · Última consulta:{" "}
            {timeLabel(data?.generated_at ?? null)}.
          </p>
        </div>
      </section>
      <div className="metric-strip">
        <div className="metric">
          <span>
            Entradas autorizadas <KeyRound size={15} />
          </span>
          <strong>{data?.totals.success ?? "—"}</strong>
          <p>Acumulado desde o início do volume</p>
        </div>
        <div className="metric">
          <span>Credenciais inválidas</span>
          <strong>{data?.totals.failure ?? "—"}</strong>
          <p>Acumulado · não inclui bloqueios prévios</p>
        </div>
        <div className="metric">
          <span>Maior número de falhas por IP</span>
          <strong>
            {data?.failures_recent.ip ?? "—"}
            <small> / 5</small>
          </strong>
          <p>Janela móvel de 60 segundos</p>
        </div>
        <div className="metric">
          <span>Tentativas bloqueadas</span>
          <strong>{data?.blocked_recent ?? "—"}</strong>
          <p>Na última janela de 60 segundos</p>
        </div>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Histórico de acesso</h2>
            <p>Últimos 100 eventos · retenção de 7 dias · horários locais</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="service-table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Usuário informado</th>
                <th>IP da conexão</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {data?.events.map((event) => (
                <tr key={event.id}>
                  <td>{timeLabel(event.at, true)}</td>
                  <td>{event.username}</td>
                  <td>
                    <code>{event.ip}</code>
                  </td>
                  <td>
                    <span
                      className={`status status-${event.outcome === "success" || event.outcome === "logout" ? "ok" : "warning"}`}
                    >
                      {outcomes[event.outcome] ?? event.outcome}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data?.events.length && (
          <p className="security-note muted">
            {data
              ? "Nenhum evento registrado."
              : "Os eventos aparecerão após a consulta."}
          </p>
        )}
        <p className="security-note muted">
          Após 5 falhas por IP ou 10 por usuário em 60 s, novos logins recebem
          bloqueio temporário. Tentativas bloqueadas não prolongam essa janela.
          Sessões existentes continuam válidas.
        </p>
      </section>
      <section className="panel security-incidents">
        <div className="panel-heading">
          <div>
            <h2>Incidentes de autenticação</h2>
            <p>O alerta exige 10 s de confirmação do limite observado.</p>
          </div>
        </div>
        <IncidentsList
          incidents={incidents.filter((item) => item.service === "platform")}
          compact
        />
      </section>
      <p className="security-note muted">
        O monitoramento de vulnerabilidades dos serviços será integrado na próxima etapa.
      </p>
    </>
  );
}
