import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { request } from "./api";
import { IncidentsList, timeLabel } from "./components";
import { currentAnalysis, type Severity, type VulnerabilityOverview } from "./vulnerabilityState";
import type { Incident } from "./types";

const labels = { critical: "Achado crítico", warning: "Achado alto", notice: "Achados para revisão", clear: "Nenhum achado conhecido", unknown: "Sem análise atual" };
const colors = { critical: "critical", warning: "warning", notice: "warning", clear: "ok", unknown: "unknown" };
const severities: Record<Severity,string> = {critical:"Crítica",high:"Alta",medium:"Média",low:"Baixa",negligible:"Desprezível",unknown:"Não classificada"};
const reasons:Record<string,string> = {
  not_configured:"Fonte de relatórios não configurada.",inventory_unavailable:"Inventário indisponível ou sem atualização recente.",
  analysis_pending:"Análise em andamento.",report_unavailable:"Aguardando relatório válido desta imagem.",image_changed:"A imagem mudou e precisa de nova análise.",
  analysis_expired:"A análise perdeu a validade. Aguarde nova coleta.",database_expired:"A base de vulnerabilidades está vencida.",scanner_failed:"A última tentativa falhou; o monitor repetirá a análise.",
};

export default function Vulnerabilities({refresh,incidents}:{refresh:number;incidents:Incident[]}) {
  const [data,setData]=useState<VulnerabilityOverview|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [service,setService]=useState("web-demo");
  const [severity,setSeverity]=useState("all");
  const [page,setPage]=useState(1);
  const [now,setNow]=useState(()=>Date.now()/1000);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()/1000),1000);return ()=>clearInterval(timer);},[]);
  useEffect(()=>{
    const controller=new AbortController();let running=false;
    async function load(){
      if(running)return;running=true;
      try{
        const value=await request<VulnerabilityOverview>(`/api/security/vulnerabilities?service=${service}&severity=${severity}&page=${page}`,{signal:controller.signal});
        if(!controller.signal.aborted){
          if(page>Math.max(1,Math.ceil(value.findings.total/50)))setPage(1);
          setData(value);setError(null);
        }
      }catch(reason){if(!controller.signal.aborted){setData(null);setError(reason instanceof Error?reason.message:"Relatórios indisponíveis.");}}
      finally{running=false;}
    }
    setData(null);void load();const timer=setInterval(()=>void load(),5000);
    return ()=>{controller.abort();clearInterval(timer);};
  },[refresh,service,severity,page]);
  const rows=data?.services.map(row=>currentAnalysis(row,now))??[];
  const selected=rows.find(row=>row.id===service);
  const available=selected && selected.status!=="unknown";
  const findings=available?data?.findings.items??[]:[];
  const total=available?data?.findings.total??0:0;
  return <>
    <section className="panel vulnerability-panel">
      <div className="panel-heading"><div><h2><ShieldAlert size={18}/> Vulnerabilidades conhecidas</h2><p>Imagens locais · inventário Syft + análise Grype · nova análise a cada 6 horas</p></div></div>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="table-scroll"><table className="service-table vulnerability-table">
        <thead><tr><th>Serviço / imagem em uso</th><th>Estado da análise</th><th>Críticas</th><th>Altas</th><th>Demais</th><th>Última análise</th></tr></thead>
        <tbody>{rows.map(row=><tr key={row.id}><td><strong>{row.name}</strong><small><code title={row.image_id??undefined}>{row.image_id?`${row.image_id.slice(0,19)}…`:"Imagem não identificada"}</code></small></td><td><span className={`status status-${colors[row.status]}`}>{labels[row.status]}</span>{row.scan_status==="running"&&<small>Reanálise em andamento</small>}</td><td>{row.counts?.critical??"—"}</td><td>{row.counts?.high??"—"}</td><td>{row.counts?row.counts.medium+row.counts.low+row.counts.negligible+row.counts.unknown:"—"}</td><td>{timeLabel(row.scanned_at,true)}<small>{row.package_count!==null?`${row.package_count.toLocaleString("pt-BR")} pacotes catalogados`:"Sem inventário de pacotes"}</small></td></tr>)}</tbody>
      </table></div>
      <p className="security-note muted">Um achado associa um aviso de segurança a um pacote e versão da imagem; exige revisão de aplicabilidade. HTTP e SMTP compartilham a imagem. O resultado não determina a disponibilidade do protocolo.</p>
      <div className="vulnerability-filters"><label htmlFor="vulnerability-service">Serviço analisado<select id="vulnerability-service" value={service} onChange={event=>{setService(event.target.value);setPage(1);}}><option value="web-demo">HTTP</option><option value="postgres">PostgreSQL</option><option value="dns">DNS</option><option value="smtp">SMTP</option></select></label><label htmlFor="vulnerability-severity">Severidade<select id="vulnerability-severity" value={severity} onChange={event=>{setSeverity(event.target.value);setPage(1);}}><option value="all">Todas as severidades</option>{Object.entries(severities).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label></div>
      {selected && <div className="vulnerability-metadata"><p><strong>{selected.name}</strong> · Grype {selected.scanner_version??"—"} · Base: {timeLabel(selected.db_built_at,true)}</p>{selected.reason && <p role="status">{reasons[selected.reason]??"Análise indisponível."}</p>}<p>Análise válida por até 24 h, com base de até 5 dias e inventário das imagens atualizado em até 2 min.</p></div>}
      <div className="table-scroll"><table className="service-table vulnerability-findings"><thead><tr><th>Aviso / severidade</th><th>Pacote</th><th>Versão instalada</th><th>Versões corrigidas</th></tr></thead><tbody>{findings.map(item=><tr key={`${item.id}:${item.package_type}:${item.package}:${item.installed_version}`}><td>{item.url?<a href={item.url} target="_blank" rel="noreferrer">{item.id}</a>:<strong>{item.id}</strong>}<small>{severities[item.severity]}</small></td><td><code>{item.package}</code><small>{item.package_type}</small></td><td><code>{item.installed_version}</code></td><td><code>{item.fixed_versions.length?item.fixed_versions.join(", "):"Sem correção informada"}</code><small>{item.fix_state==="wont-fix"?"Fornecedor não prevê correção":"Conferir compatibilidade antes de atualizar"}</small></td></tr>)}</tbody></table></div>
      {!findings.length && <p className="security-note muted">{!selected?"Aguardando consulta de relatórios.":!available?"Achados atuais indisponíveis. A última análise não confirma o estado atual.":severity==="all"?"Nenhum achado conhecido na análise desta imagem e base.":"Nenhum achado nesta severidade. Confira as demais classificações."}</p>}
      <div className="vulnerability-pagination"><span>{available?`${total.toLocaleString("pt-BR")} achados · Página ${page} de ${Math.max(1,Math.ceil(total/50))}`:"Sem paginação disponível"}</span><div><button className="button secondary" disabled={!available||page<=1} onClick={()=>setPage(value=>value-1)}>Anterior</button><button className="button secondary" disabled={!available||page*50>=total} onClick={()=>setPage(value=>value+1)}>Próxima</button></div></div>
      <p className="security-note muted">O monitor local é iniciado por scripts/start.ps1. Relatórios antigos, leitura incompleta e falhas ficam sem análise atual. A cobertura não inclui volumes, host ou garantia de detectar dependências JavaScript embutidas no frontend.</p>
    </section>
    <section className="panel vulnerability-incidents"><div className="panel-heading"><div><h2>Incidentes de vulnerabilidade</h2><p>Achados altos/críticos e indisponibilidade da análise.</p></div></div><IncidentsList incidents={incidents.filter(item=>["VulnerabilidadeCritica","VulnerabilidadeAlta","VulnerabilidadeAnaliseIndisponivel"].includes(item.name))} compact/></section>
  </>;
}
