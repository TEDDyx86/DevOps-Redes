import { useEffect, useState } from "react";
import { Activity, Square, Play } from "lucide-react";
import { request } from "./api";
import { timeLabel } from "./components";

interface Job {
  status: "idle" | "running" | "completed" | "cancelled" | "failed";
  duration: number;
  started_at: number | null;
  ended_at: number | null;
  services: Record<
    string,
    {
      attempted: number;
      successful: number;
      failed: number;
      cancelled: number;
      rate_limit: number;
    }
  >;
}
const names: Record<string, string> = {
  "web-demo": "HTTP",
  postgres: "PostgreSQL",
  dns: "DNS",
  smtp: "SMTP",
};
const statuses = {
  idle: "Nenhum teste iniciado",
  running: "Carga em execução",
  completed: "Carga concluída",
  cancelled: "Carga cancelada",
  failed: "Carga interrompida por falha",
};
export default function TrafficLab({ token }: { token: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [service, setService] = useState("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let running = false;
    async function load() {
      if (running) return;
      running = true;
      try {
        const value = await request<Job>("/api/lab/traffic", {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setJob(value);
          setPollError(null);
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setJob(null);
          setPollError(
            reason instanceof Error
              ? reason.message
              : "Estado da carga indisponível.",
          );
        }
      } finally {
        running = false;
      }
    }
    void load();
    const timer = setInterval(() => {
      void load();
    }, 2000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);
  async function change(stop = false) {
    setBusy(true);
    setError(null);
    try {
      setJob(
        await request<Job>("/api/lab/traffic", {
          method: stop ? "DELETE" : "POST",
          headers: { "Content-Type": "application/json", "X-Lab-Token": token },
          ...(stop ? {} : { body: JSON.stringify({ service, duration: 90 }) }),
        }),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Não foi possível executar a carga.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel traffic-lab">
      <div className="panel-heading">
        <div>
          <h2>
            <Activity size={19} /> Teste de tráfego
          </h2>
          <p>
            Protocolos reais, alvos locais e encerramento automático em 90 s.
          </p>
        </div>
        <a className="text-button" href="#security">
          Acompanhar detecção
        </a>
      </div>
      <div className="traffic-controls">
        <label htmlFor="traffic-service">
          Serviço
          <select
            id="traffic-service"
            value={service}
            onChange={(event) => setService(event.target.value)}
            disabled={job?.status === "running" || busy}
          >
            <option value="all">Todos os quatro serviços</option>
            {Object.entries(names).map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button primary"
          disabled={!job || job.status === "running" || busy || !token.trim()}
          onClick={() => {
            void change();
          }}
        >
          <Play size={15} /> Iniciar carga de 90 s
        </button>
        <button
          className="button secondary"
          disabled={job?.status !== "running" || busy || !token.trim()}
          onClick={() => {
            void change(true);
          }}
        >
          <Square size={14} /> Encerrar carga
        </button>
      </div>
      <p className="security-note muted">
        Use o token informado acima. Aguarde as referências prontas e o volume
        normal na aba Segurança. Limites: HTTP 5 req/s, SQL 10 comandos/s, DNS
        10 consultas/s e SMTP 1 mensagem/s. Um teste por vez; operações em
        andamento têm timeout de até 3 s.
      </p>
      {pollError && (
        <p className="notice error" role="alert">
          {pollError}
        </p>
      )}
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      <div className="traffic-job-state" role="status">
        <strong>
          {job ? statuses[job.status] : "Consultando estado da carga…"}
        </strong>
        <span>
          {job?.started_at
            ? `Início: ${timeLabel(job.started_at)}${job.ended_at ? ` · Fim: ${timeLabel(job.ended_at)}` : ""}`
            : "O teste altera apenas o volume de tráfego do laboratório."}
        </span>
      </div>
      {job && Object.keys(job.services).length > 0 && (
        <div className="table-scroll">
          <table className="service-table">
            <thead>
              <tr>
                <th>Serviço</th>
                <th>Tentativas</th>
                <th>Sucessos</th>
                <th>Falhas</th>
                <th>Canceladas em voo</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(job.services).map(([id, counts]) => (
                <tr key={id}>
                  <td>{names[id]}</td>
                  <td>{counts.attempted}</td>
                  <td>{counts.successful}</td>
                  <td>{counts.failed}</td>
                  <td>{counts.cancelled}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
