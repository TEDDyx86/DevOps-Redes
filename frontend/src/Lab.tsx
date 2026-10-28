import { useState } from "react";
import {
  ArrowUpRight,
  CircleCheck,
  FlaskConical,
  KeyRound,
  Play,
  TriangleAlert,
  Zap,
} from "lucide-react";
import { request } from "./api";
import type { Lab as LabState, Mode } from "./types";

const modes: { mode: Mode; title: string; text: string; icon: typeof Play }[] =
  [
    {
      mode: "normal",
      title: "Operação normal",
      text: "Respostas HTTP 200. Encerra as falhas e permite acompanhar a recuperação.",
      icon: CircleCheck,
    },
    {
      mode: "slow",
      title: "Resposta lenta",
      text: "Adiciona 850 ms às respostas. Atenção após 30 segundos acima do limite.",
      icon: Zap,
    },
    {
      mode: "offline",
      title: "Indisponibilidade",
      text: "Retorna HTTP 503. Alerta crítico após 15 segundos de falha na sonda.",
      icon: TriangleAlert,
    },
  ];

export default function Lab({
  state,
  onChanged,
}: {
  state: LabState | null;
  onChanged: () => void;
}) {
  const [token, setToken] = useState("");
  const [pending, setPending] = useState<Mode | null>(null);
  const [message, setMessage] = useState<{
    text: string;
    error: boolean;
  } | null>(null);

  async function change(mode: Mode) {
    setPending(mode);
    setMessage(null);
    try {
      await request("/api/lab/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Lab-Token": token },
        body: JSON.stringify({ mode }),
      });
      setMessage({
        text: `Modo aplicado: ${modes.find((item) => item.mode === mode)?.title}. A próxima sonda atualizará o dashboard.`,
        error: false,
      });
      onChanged();
    } catch (error) {
      setMessage({
        text:
          error instanceof Error ? error.message : "Falha ao alterar o modo.",
        error: true,
      });
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="lab-layout">
      <section className="panel lab-controls">
        <div className="panel-heading">
          <div>
            <h2>Controle do serviço HTTP</h2>
            <p>Falhas controladas para testar o monitoramento.</p>
          </div>
          <FlaskConical size={21} />
        </div>
        <div className="token-field">
          <label htmlFor="lab-token">
            <KeyRound size={15} />
            Token do laboratório
          </label>
          <input
            id="lab-token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Cole o LAB_TOKEN do arquivo .env"
          />
          <p>
            Usado apenas nesta sessão. Necessário para alterar o serviço de
            demonstração.
          </p>
        </div>
        {state && !state.available && (
          <p className="notice error">
            Serviço de demonstração sem conexão. Confira se o container web-demo
            está executando.
          </p>
        )}
        <div className="mode-list">
          {modes.map(({ mode, title, text, icon: Icon }) => (
            <div
              className={`mode-row ${state?.mode === mode ? "selected" : ""}`}
              key={mode}
            >
              <span className="mode-icon">
                <Icon size={22} />
              </span>
              <div>
                <h3>
                  {title}{" "}
                  {state?.mode === mode && (
                    <span className="current-mode">Atual</span>
                  )}
                </h3>
                <p>{text}</p>
              </div>
              <button
                className="button secondary"
                disabled={
                  !token.trim() ||
                  !!pending ||
                  !state?.available ||
                  state.mode === mode
                }
                onClick={() => change(mode)}
              >
                {pending === mode ? "Aplicando…" : "Aplicar"}
              </button>
            </div>
          ))}
        </div>
        {message && (
          <p
            role={message.error ? "alert" : "status"}
            className={`notice ${message.error ? "error" : "success"}`}
          >
            {message.text}
          </p>
        )}
      </section>
      <aside className="lab-guide">
        <span className="eyebrow">ROTEIRO DE DEMONSTRAÇÃO</span>
        <h2>Observe o ciclo completo.</h2>
        <ol>
          <li>
            <strong>Comece em operação normal.</strong>
            <span>Aguarde as primeiras amostras no dashboard.</span>
          </li>
          <li>
            <strong>Provoque uma falha.</strong>
            <span>
              Aplique lentidão ou indisponibilidade e acompanhe o estado.
            </span>
          </li>
          <li>
            <strong>Confira o alerta.</strong>
            <span>Após a confirmação, veja o incidente e o e-mail local.</span>
          </li>
          <li>
            <strong>Restaure o serviço.</strong>
            <span>Volte ao normal e confirme a resolução.</span>
          </li>
        </ol>
        <a
          className="button primary"
          href="http://localhost:8025"
          target="_blank"
          rel="noreferrer"
        >
          Abrir caixa de e-mail <ArrowUpRight size={16} />
        </a>
        <p className="small muted">
          As mensagens ficam no Mailpit local. Nenhum e-mail é enviado para uma
          conta externa.
        </p>
      </aside>
    </div>
  );
}
