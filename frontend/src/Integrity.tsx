import { useEffect, useRef, useState } from "react";
import { FileCheck2 } from "lucide-react";
import { request } from "./api";
import { IncidentsList, timeLabel } from "./components";
import { approvalCandidates,currentFile,reviewStillCurrent,type Approval,type IntegrityOverview } from "./integrityState";
import type { Incident } from "./types";

const labels={ok:"Íntegro",unapproved:"Referência pendente",changed:"Alterado",missing:"Ausente",unreadable:"Leitura indisponível",unknown:"Sem dados atuais"};
const colors={ok:"ok",unapproved:"warning",changed:"critical",missing:"critical",unreadable:"warning",unknown:"unknown"};
const events:Record<string,string>={observed:"Primeira observação",approved:"Referência aprovada",changed:"Alteração detectada",missing:"Arquivo ausente",unreadable:"Falha de leitura",restored:"Conteúdo restaurado"};

export default function Integrity({refresh,incidents}:{refresh:number;incidents:Incident[]}) {
  const [data,setData]=useState<IntegrityOverview|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [now,setNow]=useState(()=>Date.now()/1000);
  const [selected,setSelected]=useState("pending");
  const [token,setToken]=useState("");
  const [review,setReview]=useState<Approval[]>([]);
  const [busy,setBusy]=useState(false);
  const [feedback,setFeedback]=useState<{text:string;error:boolean}|null>(null);
  const generation=useRef(0);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()/1000),1000);return ()=>clearInterval(timer);},[]);
  useEffect(()=>{
    const controller=new AbortController();let running=false;
    async function load(){
      if(running)return;running=true;const version=generation.current;
      try{const value=await request<IntegrityOverview>("/api/security/integrity",{signal:controller.signal});if(!controller.signal.aborted && version===generation.current){setData(value);setError(null);}}
      catch(reason){if(!controller.signal.aborted && version===generation.current){setData(null);setError(reason instanceof Error?reason.message:"Verificação indisponível.");}}
      finally{running=false;}
    }
    void load();const timer=setInterval(()=>void load(),5000);
    return ()=>{controller.abort();clearInterval(timer);};
  },[refresh]);
  const rows=data?.files.map(row=>currentFile(row,now))??[];
  const candidates=approvalCandidates(rows,selected);
  const validReview=reviewStillCurrent(review,rows);
  async function approve(){
    setBusy(true);setFeedback(null);generation.current++;
    try{
      const value=await request<IntegrityOverview>("/api/security/integrity/approve",{method:"POST",headers:{"Content-Type":"application/json","X-Lab-Token":token},body:JSON.stringify({items:review})});
      generation.current++;setData(value);setReview([]);setToken("");
      setFeedback({text:"Referência persistida. Alterações futuras continuarão sendo detectadas.",error:false});
    }catch(reason){setFeedback({text:reason instanceof Error?reason.message:"Não foi possível aprovar.",error:true});}
    finally{setBusy(false);}
  }
  return <>
    <section className="panel integrity-panel">
      <div className="panel-heading"><div><h2><FileCheck2 size={18}/> Integridade das configurações</h2><p>8 arquivos do laboratório · SHA-256 · verificação a cada 5 segundos</p></div></div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {data && !data.enabled && <p className="notice" role="status">Monitor de arquivos não configurado neste ambiente.</p>}
      <div className="table-scroll"><table className="service-table integrity-table"><thead><tr><th>Arquivo / serviço</th><th>Estado observado</th><th>SHA-256 observado</th><th>Referência aprovada</th><th>Última verificação</th></tr></thead><tbody>
        {rows.map(row=><tr key={row.id}><td><strong>{row.name}</strong><small><code>{row.path}</code></small></td><td><span className={`status status-${colors[row.status]}`}>{labels[row.status]}</span></td><td><code title={row.observed_sha256??undefined}>{row.observed_sha256?`${row.observed_sha256.slice(0,12)}…`:"—"}</code></td><td><code title={row.approved_sha256??undefined}>{row.approved_sha256?`${row.approved_sha256.slice(0,12)}…`:"Pendente"}</code><small>{row.approved_at?`${timeLabel(row.approved_at,true)} · ${row.approved_by}`:"Aprovação inicial necessária"}</small></td><td>{timeLabel(row.checked_at)}</td></tr>)}
      </tbody></table></div>
      <p className="security-note muted">Mudança ou ausência confirmada por 15 s gera alerta. Falha de leitura e dados antigos ficam indisponíveis. O hash acompanha o arquivo em disco; aplicar a configuração no serviço pode exigir reinicialização.</p>
      <details className="traffic-calibration"><summary>Revisar e aprovar uma referência</summary>
        <p>Confira os arquivos no repositório antes da primeira aprovação ou após uma mudança intencional. Aprovar um conteúdo alterado passa a considerá-lo a nova referência.</p>
        <div className="traffic-calibration-form"><label>Arquivo para revisão<select value={selected} disabled={busy} onChange={event=>{setSelected(event.target.value);setReview([]);setFeedback(null);}}><option value="pending">Todas as referências iniciais pendentes</option>{rows.map(row=><option key={row.id} value={row.id}>{row.name} · {row.path}</option>)}</select></label><button className="button secondary" disabled={busy||!data?.enabled||!candidates.length} onClick={()=>{setReview(candidates.map(row=>({file_id:row.id,observed_sha256:row.observed_sha256!})));setFeedback(null);}}>Preparar revisão dos hashes</button></div>
        {!!review.length && <div className="integrity-review"><p>Hashes selecionados para aprovação:</p><ul>{review.map(item=><li key={item.file_id}><strong>{data?.files.find(row=>row.id===item.file_id)?.path}</strong><code>{item.observed_sha256}</code></li>)}</ul>
          {!validReview && <p className="notice error" role="alert">A observação mudou ou expirou. Atualize a revisão antes de aprovar.</p>}
          <div className="traffic-calibration-form"><label>Token para aprovar referência<input type="password" autoComplete="off" value={token} onChange={event=>setToken(event.target.value)} placeholder="LAB_TOKEN do .env"/></label><button className="button secondary" disabled={busy||!validReview||!token.trim()} onClick={()=>void approve()}>{busy?"Aprovando…":"Aprovar estes hashes"}</button></div>
        </div>}
        {feedback && <p className={`notice ${feedback.error?"error":"success"}`} role={feedback.error?"alert":"status"}>{feedback.text}</p>}
      </details>
    </section>
    <section className="panel integrity-events"><div className="panel-heading"><div><h2>Eventos de configuração</h2><p>Últimos 100 eventos · retenção de 7 dias · hashes completos na revisão</p></div></div><div className="table-scroll"><table className="service-table"><thead><tr><th>Quando</th><th>Arquivo</th><th>Evento</th><th>Responsável pela aprovação</th></tr></thead><tbody>{data?.events.map(event=><tr key={event.id}><td>{timeLabel(event.at,true)}</td><td><code>{data.files.find(row=>row.id===event.file_id)?.path??event.file_id}</code></td><td>{events[event.kind]??event.kind}</td><td>{event.actor??"—"}</td></tr>)}</tbody></table></div>{!data?.events.length && <p className="security-note muted">{data?"Nenhum evento registrado.":"Aguardando consulta de eventos."}</p>}</section>
    <section className="panel security-incidents"><div className="panel-heading"><div><h2>Incidentes de configuração</h2><p>Alterações, arquivos ausentes e falhas de verificação.</p></div></div><IncidentsList incidents={incidents.filter(item=>["ConfiguracaoAlterada","ConfiguracaoVerificacaoIndisponivel","ConfiguracaoReferenciaPendente"].includes(item.name))} compact/></section>
  </>;
}
