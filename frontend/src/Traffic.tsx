import { useEffect, useState } from "react";
import { ArrowUpRight, Activity, TriangleAlert } from "lucide-react";
import { formatMetric, request } from "./api";
import { IncidentsList, timeLabel } from "./components";
import {
  currentTraffic,
  trafficValue,
  type TrafficOverview,
} from "./trafficState";
import type { Incident } from "./types";

const labels = {
  normal: "Volume normal",
  anomalous: "Acima do limiar",
  learning: "Aprendendo",
  unknown: "Sem dados",
};
const colors = {
  normal: "ok",
  anomalous: "warning",
  learning: "unknown",
  unknown: "unknown",
};

export default function Traffic({
  refresh,
  incidents,
}: {
  refresh: number;
  incidents: Incident[];
}) {
  const [data, setData] = useState<TrafficOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const [token, setToken] = useState("");
  const [selected, setSelected] = useState("web-demo");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{
    text: string;
    error: boolean;
  } | null>(null);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let running = false;
    async function load() {
      if (running) return;
      running = true;
      try {
        const value = await request<TrafficOverview>("/api/security/traffic", {
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
            reason instanceof Error
              ? reason.message
              : "Coleta de tráfego indisponível.",
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
  const rows = data?.services.map((row) => currentTraffic(row, now)) ?? [];
  const current = rows.find((row) => row.id === selected);
  async function calibrate() {
    setBusy(true);
    setFeedback(null);
    try {
      setData(
        await request<TrafficOverview>("/api/security/traffic/calibrate", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Lab-Token": token },
          body: JSON.stringify({ service: selected }),
        }),
      );
      setFeedback({
        text: "Nova referência em aprendizado. Mantenha o serviço em operação habitual por pelo menos 2 minutos.",
        error: false,
      });
    } catch (reason) {
      setFeedback({
        text:
          reason instanceof Error
            ? reason.message
            : "Não foi possível recalibrar.",
        error: true,
      });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel traffic-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <Activity size={18} /> Tráfego dos serviços
            </h2>
            <p>Taxa do último minuto comparada à referência inicial fixa.</p>
          </div>
          <a className="text-button" href="#lab">
            Testar carga local <ArrowUpRight size={14} />
          </a>
        </div>
        {error && (
          <div className="notice error" role="alert">
            <TriangleAlert size={17} />
            {error}
          </div>
        )}
        <div className="table-scroll">
          <table className="service-table traffic-table">
            <thead>
              <tr>
                <th>Serviço / unidade</th>
                <th>Taxa atual</th>
                <th>Referência</th>
                <th>Limiar de aviso</th>
                <th>Estado observado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.name}</strong>
                    <small>{row.unit}</small>
                  </td>
                  <td>{formatMetric(trafficValue(row.rate, row.scale), 2)}</td>
                  <td>
                    {formatMetric(trafficValue(row.baseline, row.scale), 2)}
                    <small>
                      {row.calibrated_at
                        ? timeLabel(row.calibrated_at, true)
                        : "Aguardando referência"}
                    </small>
                  </td>
                  <td>
                    {formatMetric(trafficValue(row.threshold, row.scale), 2)}
                  </td>
                  <td>
                    <span className={`status status-${colors[row.status]}`}>
                      {labels[row.status]}
                    </span>
                    {row.status === "learning" && (
                      <small>
                        {Math.floor(row.learning_seconds)} / 120 s válidos
                      </small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data && (
          <p className="security-note muted">Aguardando consulta de tráfego.</p>
        )}
        <p className="security-note muted">
          O limiar é o maior valor entre 3× a referência e o piso do serviço. O
          alerta exige 30 s acima do limiar. A referência usa pelo menos 2 min
          contínuos de coleta válida; mantenha o ambiente em operação habitual
          nesse período. Aumento de volume não comprova um ataque.
        </p>
        <details className="traffic-calibration">
          <summary>Recalibrar referência em operação habitual</summary>
          <p>
            Use após uma mudança intencional no padrão de uso. Recalibrar inicia
            uma nova janela de aprendizado; não é permitido durante o teste de
            carga ou com volume já acima do limiar.
          </p>
          <div className="traffic-calibration-form">
            <label>
              Serviço
              <select
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
              >
                {rows.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Token do laboratório
              <input
                type="password"
                autoComplete="off"
                placeholder="LAB_TOKEN do .env"
                value={token}
                onChange={(event) => setToken(event.target.value)}
              />
            </label>
            <button
              className="button secondary"
              disabled={busy || !token.trim() || current?.status !== "normal"}
              onClick={() => {
                void calibrate();
              }}
            >
              {busy ? "Recalibrando…" : "Recalibrar referência"}
            </button>
          </div>
          {feedback && (
            <p
              className={`notice ${feedback.error ? "error" : "success"}`}
              role={feedback.error ? "alert" : "status"}
            >
              {feedback.text}
            </p>
          )}
        </details>
      </section>
      <section className="panel traffic-incidents">
        <div className="panel-heading">
          <div>
            <h2>Incidentes de tráfego</h2>
            <p>Volumes elevados e falhas na coleta dos serviços.</p>
          </div>
        </div>
        <IncidentsList
          incidents={incidents.filter((item) =>
            ["TrafegoAnormal", "TrafegoColetaIndisponivel"].includes(item.name),
          )}
          compact
        />
      </section>
    </>
  );
}
