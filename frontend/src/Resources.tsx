import { useEffect, useState } from "react";
import { Cpu, TriangleAlert } from "lucide-react";
import { formatMetric, request } from "./api";
import { IncidentsList, SignalChart, timeLabel } from "./components";
import { currentResources, type ResourceOverview } from "./resourceState";
import type { Incident, Window } from "./types";

const labels = {ok: "Dentro do orçamento", warning: "Acima do orçamento", partial: "Coleta parcial", unknown: "Sem dados atuais"};
const colors = {ok: "ok", warning: "warning", partial: "unknown", unknown: "unknown"};
const reasons: Record<string, string> = {not_configured: "Coletor não configurado.", expired: "A medição venceu.",
  ambiguous_container: "Contêiner duplicado ou identidade ambígua neste serviço.",
  source_unavailable: "Coletor sem atualização recente.", container_not_running: "Contêiner parado ou ausente.",
  sampling_failed: "Falha ao consultar o Engine.", container_changed: "Execução mudou durante a leitura.",
  invalid_stats: "Estatísticas indisponíveis ou inconsistentes.", warming_or_partial: "Aguardando duas amostras ou campo não informado pelo Engine."};
const scaled = (value: number | null, divisor: number) => value === null ? null : value / divisor;

export default function Resources({window, refresh, incidents}: {window: Window; refresh: number; incidents: Incident[]}) {
  const [service, setService] = useState("postgres");
  const [data, setData] = useState<ResourceOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {const timer = setInterval(() => setNow(Date.now()/1000), 1000); return () => clearInterval(timer);}, []);
  useEffect(() => {
    const controller = new AbortController(); let running = false;
    setData(null);
    async function load() {
      if (running) return; running = true;
      try {
        const value = await request<ResourceOverview>(`/api/resources?service=${service}&window=${window}`, {signal: controller.signal});
        if (!controller.signal.aborted) {setData(value); setError(null);}
      } catch (reason) {
        if (!controller.signal.aborted) {setData(null); setError(reason instanceof Error ? reason.message : "Recursos indisponíveis.");}
      } finally {running = false;}
    }
    void load(); const timer = setInterval(() => void load(), 5000);
    return () => {controller.abort(); clearInterval(timer);};
  }, [service, window, refresh]);
  const current = data ? currentResources(data, now) : null;
  const selected = current?.services.find(row => row.id === service);
  const series = current?.series.map(row => ({...row, latency_ms: null,
    memory_mib: scaled(row.memory_bytes, 1024**2), read_kibps: scaled(row.read_bps, 1024),
    write_kibps: scaled(row.write_bps, 1024)})) ?? [];
  return <>
    {error && <div className="notice error" role="alert"><TriangleAlert size={17}/>{error}</div>}
    <section className="panel resource-panel">
      <div className="panel-heading"><div><h2><Cpu size={18}/> Consumo por serviço</h2><p>CPU, memória e movimentação de blocos dos contêineres · coleta local a cada 5 s</p></div></div>
      <div className="table-scroll"><table className="service-table resource-table"><thead><tr>
        <th>Serviço / estado</th><th>CPU · núcleos</th><th>RAM · MiB</th><th>Leitura · KiB/s</th><th>Gravação · KiB/s</th><th>Última medição</th>
      </tr></thead><tbody>{current?.services.map(row => <tr key={row.id}>
        <td><strong>{row.name}</strong><small><span className={`status status-${colors[row.status]}`}>{labels[row.status]}</span></small></td>
        <td><strong className="resource-number">{formatMetric(row.values.cpu_cores, 3)}</strong>
          <small>Orçamento: {formatMetric(row.budgets.cpu_cores, 1)}</small>
          {row.values.cpu_cores !== null && <span className={`resource-meter ${row.values.cpu_cores > row.budgets.cpu_cores ? "over-budget" : ""}`} aria-hidden="true"><i style={{width: `${Math.min(100, row.values.cpu_cores / row.budgets.cpu_cores * 100)}%`}}/></span>}</td>
        <td><strong className="resource-number">{formatMetric(scaled(row.values.memory_bytes, 1024**2), 1)}</strong><small>Orçamento: {row.budgets.memory_bytes / 1024**2} MiB</small></td>
        <td className="resource-number">{formatMetric(scaled(row.values.read_bps, 1024), 2)}</td>
        <td className="resource-number">{formatMetric(scaled(row.values.write_bps, 1024), 2)}</td>
        <td>{timeLabel(row.observed_at)}{row.reason && <small>{reasons[row.reason] ?? "Verifique a coleta."}</small>}</td>
      </tr>)}</tbody></table></div>
      {!current && <p className="security-note muted">Aguardando medições de recursos.</p>}
      <p className="security-note muted">1,0 núcleo equivale a uma CPU ocupada; pode haver uso de vários núcleos. RAM mostra o uso menos cache inativo (working set). Os orçamentos orientam a observação e não impõem limites aos serviços.</p>
      <p className="security-note muted">I/O mede bytes de blocos contabilizados pelo Engine, sujeitos ao cache e ao armazenamento da VM. Não representa espaço ocupado, IOPS ou latência do disco. Ausência de dados aparece como —, nunca como zero saudável.</p>
    </section>
    <section className="panel resource-selection"><label htmlFor="resource-service">Histórico do serviço<select id="resource-service" value={service} onChange={event => setService(event.target.value)}>
      <option value="web-demo">HTTP</option><option value="postgres">PostgreSQL</option><option value="dns">DNS</option><option value="smtp">SMTP</option>
    </select></label><p>{selected?.container_id ? `Contêiner ${selected.container_id.slice(0,12)} · iniciado em ${timeLabel(selected.started_at, true)}` : "Aguardando identidade do contêiner."}</p></section>
    {current && !current.history_available && <div className="notice" role="status">Histórico temporariamente indisponível. As medições atuais são apresentadas separadamente.</div>}
    <div className="charts-grid">
      <SignalChart data={series} metric="cpu_cores" title="CPU utilizada" subtitle={`Histórico de ${selected?.name ?? service}`} unit="núcleos"/>
      <SignalChart data={series} metric="memory_mib" title="Memória de trabalho" subtitle="Uso menos cache inativo" unit="MiB"/>
      <SignalChart data={series} metric="read_kibps" title="Leitura de blocos" subtitle="Taxa medida entre amostras válidas" unit="KiB/s"/>
      <SignalChart data={series} metric="write_kibps" title="Gravação de blocos" subtitle="Reinícios e falhas interrompem a série" unit="KiB/s"/>
    </div>
    <section className="panel"><div className="panel-heading"><div><h2>Incidentes de recursos</h2><p>Orçamentos excedidos e indisponibilidade da coleta.</p></div></div>
      <IncidentsList incidents={incidents.filter(row => ["RecursoCPUElevada", "RecursoMemoriaElevada", "RecursoIOElevado", "RecursosColetaIndisponivel"].includes(row.name))} compact/>
    </section>
  </>;
}
