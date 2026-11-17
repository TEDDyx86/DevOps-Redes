import React, { useState } from "react";
import { RetroWindow } from "./RetroWindow";

interface DesktopItem {
  id: string;
  name: string;
  icon: string;
  tag: string;
  contentTitle: string;
  content: React.ReactNode;
}

interface RetroDesktopProps {
  onOpenWork?: () => void;
  onOpenMode?: () => void;
  onOpenMetrics?: () => void;
  workLogs?: Array<{ at: string; latencyMs: number; message: string; failure?: string }>;
}

export function RetroDesktop({
  onOpenWork,
  onOpenMode,
  onOpenMetrics,
  workLogs = [],
}: RetroDesktopProps) {
  const [activeWindow, setActiveWindow] = useState<string | null>(null);

  const desktopIcons: DesktopItem[] = [
    {
      id: "computer",
      name: "COMPUTER",
      icon: "💻",
      tag: "SYS",
      contentTitle: "HARDWARE & STACK AULAREDES",
      content: (
        <div className="space-y-3 text-xs leading-relaxed">
          <p className="font-pixel text-[10px] text-cyan">STATUS DA TOPOLOGIA:</p>
          <div className="grid grid-cols-2 gap-2 text-[11px] border border-panel-edge p-2 bg-black/50">
            <div>• Container: app-http-demo</div>
            <div>• Host: 127.0.0.1:8001</div>
            <div>• Prometheus: 9090</div>
            <div>• Alertmanager: 9093</div>
            <div>• Postgres 17: 5432</div>
            <div>• CoreDNS: 53</div>
          </div>
          <p className="text-[10px] opacity-75">
            Ambiente isolado em Docker com volumes montados para persistência de métricas e incidentes.
          </p>
        </div>
      ),
    },
    {
      id: "debug",
      name: "DEBUG",
      icon: "🐞",
      tag: "EXE",
      contentTitle: "DEBUGGER / CONSOLE /WORK",
      content: (
        <div className="space-y-3 text-xs">
          <p className="font-pixel text-[10px] text-magenta">ÚLTIMAS EXECUÇÕES REGISTRADAS:</p>
          <div className="max-h-40 overflow-y-auto space-y-1 font-mono text-[10px] bg-black/60 p-2 border border-panel-edge">
            {workLogs.length === 0 ? (
              <p className="opacity-50">* Nenhuma requisição executada nesta sessão.</p>
            ) : (
              workLogs.map((log, idx) => (
                <div key={idx} className={log.failure ? "text-magenta" : "text-cyan"}>
                  [{log.at}] {log.failure ?? `${log.message} (${log.latencyMs}ms)`}
                </div>
              ))
            )}
          </div>
          {onOpenWork && (
            <button
              onClick={onOpenWork}
              className="retro-bevel-btn bg-magenta text-black px-3 py-1.5 font-pixel text-[9px] hover:bg-magenta/90"
            >
              ▶ DISPARAR REQUISIÇÃO
            </button>
          )}
        </div>
      ),
    },
    {
      id: "program",
      name: "PROGRAM",
      icon: "📁",
      tag: "APP",
      contentTitle: "SELETOR DE MODOS DE SERVIÇO",
      content: (
        <div className="space-y-3 text-xs">
          <p className="font-pixel text-[10px] text-amber">MODOS OPERACIONAIS:</p>
          <p className="text-[11px] opacity-80">
            Controle o comportamento do microsserviço de demonstração para testes de observabilidade e alertas:
          </p>
          <div className="flex flex-col gap-2">
            <div className="border border-cyan/40 p-2 bg-cyan/5">
              <span className="font-bold text-cyan">NORMAL:</span> Resposta imediata 200 OK.
            </div>
            <div className="border border-amber/40 p-2 bg-amber/5">
              <span className="font-bold text-amber">SLOW:</span> Atraso artificial de 1.5s para disparar alerta de latência.
            </div>
            <div className="border border-magenta/40 p-2 bg-magenta/5">
              <span className="font-bold text-magenta">OFFLINE:</span> Retorno 503 controlado para testar recuperação de queda.
            </div>
          </div>
          {onOpenMode && (
            <button
              onClick={onOpenMode}
              className="retro-bevel-btn bg-amber text-black px-3 py-1.5 font-pixel text-[9px]"
            >
              CONFIGURAR MODO
            </button>
          )}
        </div>
      ),
    },
    {
      id: "systemlog",
      name: "SYSTEM.LOG",
      icon: "📄",
      tag: "LOG",
      contentTitle: "SYSTEM.LOG // MÉTRICAS EM TEMPO REAL",
      content: (
        <div className="space-y-3 text-xs">
          <p className="font-pixel text-[10px] text-cyan">MÉTRICAS COLETADAS EM /METRICS:</p>
          <pre className="p-2 bg-black/80 border border-panel-edge text-[9px] text-violet overflow-x-auto">
{`# HELP demo_http_requests_total Completed HTTP requests
# TYPE demo_http_requests_total counter
demo_http_requests_total{path="/work",status="200"} 42
demo_http_requests_total{path="/health",status="200"} 128
# HELP demo_http_duration_seconds HTTP duration
# TYPE demo_http_duration_seconds histogram
demo_http_duration_seconds_bucket{le="0.05",path="/work"} 39`}
          </pre>
          {onOpenMetrics && (
            <button
              onClick={onOpenMetrics}
              className="retro-bevel-btn bg-cyan text-black px-3 py-1.5 font-pixel text-[9px]"
            >
              VER /METRICS BRUTO
            </button>
          )}
        </div>
      ),
    },
    {
      id: "config",
      name: "CONFIG.INI",
      icon: "⚙️",
      tag: "INI",
      contentTitle: "CONFIGURAÇÕES DA INSTÂNCIA",
      content: (
        <div className="space-y-3 text-xs font-mono">
          <p className="font-pixel text-[10px] text-parchment">PARÂMETROS LOCAIS (.ENV):</p>
          <div className="bg-black/60 p-2 border border-panel-edge text-[10px] space-y-1">
            <div>ADMIN_USERNAME=admin</div>
            <div>DEMO_PORT=8001</div>
            <div>LAB_TOKEN=•••••••••••• (protegido)</div>
            <div>PROMETHEUS_SCRAPE_INTERVAL=5s</div>
          </div>
          <p className="text-[10px] opacity-60">
            * Valores sincronizados com a stack Docker em compose.yaml.
          </p>
        </div>
      ),
    },
    {
      id: "command",
      name: "COMMAND",
      icon: "⌨️",
      tag: "COM",
      contentTitle: "CONSOLE DE COMANDO",
      content: (
        <div className="space-y-3 text-xs">
          <p className="font-pixel text-[10px] text-cyan">ATALHOS DE TERMINAL:</p>
          <div className="space-y-1 bg-black/60 p-2 border border-panel-edge text-[10px]">
            <div><span className="text-magenta">$</span> curl http://localhost:8001/health</div>
            <div><span className="text-magenta">$</span> curl http://localhost:8001/work</div>
            <div><span className="text-magenta">$</span> curl http://localhost:8001/metrics</div>
          </div>
          <p className="text-[10px] opacity-70">
            Todas as chamadas geram telemetria real ingerida pelo Prometheus da stack.
          </p>
        </div>
      ),
    },
  ];

  const currentWindow = desktopIcons.find((item) => item.id === activeWindow);

  return (
    <div className="relative border-4 border-black bg-[#0a0b14] p-4 sm:p-6 select-none shadow-[8px_8px_0_#000000]">
      {/* Top 1-Bit System Header Bar */}
      <div className="flex items-center justify-between border-b-2 border-white pb-3 mb-6">
        <div className="flex items-center gap-2">
          <span className="font-pixel text-xs text-white">SYSTEM // DESKTOP 1-BIT</span>
          <span className="text-[10px] text-cyan">[v2.6 RETRO WORKBENCH]</span>
        </div>
        <div className="text-[9px] font-pixel text-parchment/60 flex items-center gap-4">
          <span>MEM: 640KB OK</span>
          <span>12:00:00</span>
        </div>
      </div>

      {/* Desktop Icon Grid (Styled as in Image 3) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
        {desktopIcons.map((item) => {
          const isSelected = activeWindow === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveWindow(isSelected ? null : item.id)}
              className={`flex flex-col items-center justify-center p-3 border-2 transition-all cursor-pointer ${
                isSelected
                  ? "border-cyan bg-cyan/20 text-cyan shadow-[0_0_12px_rgba(0,229,255,0.4)]"
                  : "border-dashed border-white/30 bg-black/40 hover:border-white hover:bg-white/5 text-parchment"
              }`}
            >
              <span className="text-2xl filter drop-shadow-[2px_2px_0_#000]">{item.icon}</span>
              <span className="font-pixel text-[9px] mt-2 tracking-wide uppercase">
                {item.name}
              </span>
              <span className="text-[8px] opacity-50 mt-0.5">.{item.tag}</span>
            </button>
          );
        })}
      </div>

      {/* Opened Window Detail Dialog */}
      {currentWindow && (
        <div className="mt-6">
          <RetroWindow
            title={currentWindow.contentTitle}
            variant="cream"
            icon={currentWindow.icon}
            onClose={() => setActiveWindow(null)}
            statusText={`DESKTOP // ${currentWindow.name}.${currentWindow.tag}`}
          >
            {currentWindow.content}
          </RetroWindow>
        </div>
      )}
    </div>
  );
}
