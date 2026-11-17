import { useState } from "react";
import { RetroWindow } from "./RetroWindow";

interface RetroPopupsProps {
  onScanHealth?: () => Promise<boolean>;
}

export function RetroPopups({ onScanHealth }: RetroPopupsProps) {
  const [downloadDismissed, setDownloadDismissed] = useState(false);
  const [watchDismissed, setWatchDismissed] = useState(false);
  const [errorDismissed, setErrorDismissed] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);

  async function handleScan() {
    setScanning(true);
    setScanResult(null);
    try {
      if (onScanHealth) {
        const ok = await onScanHealth();
        setScanResult(ok ? "REDE 100% OPERACIONAL" : "SINAL INDISPONÍVEL");
      } else {
        await new Promise((r) => setTimeout(r, 600));
        setScanResult("REDE 100% OPERACIONAL");
      }
    } catch {
      setScanResult("ERRO NA CONEXÃO");
    } finally {
      setScanning(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {/* 1. PROBLEMS.EXE (Downloading popup from Image 0) */}
      {!downloadDismissed && (
        <RetroWindow
          title="DOWNLOADING"
          variant="cream"
          icon="💾"
          onClose={() => setDownloadDismissed(true)}
          statusText="8760 HORAS RESTANTES"
        >
          <div className="space-y-3 font-mono text-black">
            <h4 className="font-pixel text-[11px] font-bold">PROBLEMS.EXE</h4>
            <p className="text-[10px] opacity-75">
              CARREGANDO LATÊNCIA "C:/" PARA "DESKTOP"
            </p>

            {/* Segmented 99% progress bar */}
            <div className="border-2 border-black p-1 bg-white">
              <div className="flex items-center gap-0.5 h-4 bg-black/10">
                {Array.from({ length: 18 }).map((_, i) => (
                  <div key={i} className="flex-1 h-full bg-black" />
                ))}
                <div className="flex-1 h-full bg-transparent" />
              </div>
            </div>
            <div className="flex justify-between text-[9px] font-pixel">
              <span>PROGRESSO: 99%</span>
              <span>1 B/s</span>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setDownloadDismissed(true)}
                className="retro-bevel-btn bg-[#dedea8] text-black px-4 py-1.5 font-pixel text-[9px]"
              >
                CANCELAR
              </button>
            </div>
          </div>
        </RetroWindow>
      )}

      {/* 2. CREATIVE-WATCH / NETWORK-WATCH-WARE (From Image 0) */}
      {!watchDismissed && (
        <RetroWindow
          title="NETWORK-WATCH-WARE"
          variant="cyan"
          icon="🛡️"
          onClose={() => setWatchDismissed(true)}
          statusText="VERIFICAÇÃO DE PERÍMETRO"
        >
          <div className="space-y-3 text-cyan">
            <div className="flex items-start gap-3">
              {/* Pixel Detective / Shield Badge SVG */}
              <div className="size-12 shrink-0 border-2 border-cyan bg-cyan/10 flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-3zm0 4a3 3 0 110 6 3 3 0 010-6zm5 11.2c-1.42 1.4-3.23 2.37-5 2.76-1.77-.39-3.58-1.36-5-2.76v-1.7c0-1.66 3.34-2.5 5-2.5s5 .84 5 2.5v1.7z" />
                </svg>
              </div>
              <div>
                <h4 className="font-pixel text-[10px] text-parchment">VARREDURA DE REDE</h4>
                <p className="mt-1 text-[10px] opacity-80 leading-relaxed">
                  DESEJA EXECUTAR UMA VERIFICAÇÃO DE TELEMETRIA NOS MICROSSERVIÇOS LOCAIS?
                </p>
              </div>
            </div>

            {scanResult && (
              <div className="p-2 border border-cyan/40 bg-cyan/10 font-pixel text-[9px] text-center text-cyan glow-cyan">
                {scanResult}
              </div>
            )}

            <div className="pt-2 flex justify-between items-center">
              <span className="text-[9px] opacity-50">PROMETHEUS SYNC</span>
              <button
                type="button"
                onClick={handleScan}
                disabled={scanning}
                className="retro-bevel-btn bg-cyan text-black px-4 py-1.5 font-pixel text-[9px] disabled:opacity-50"
              >
                {scanning ? "VARRENDO..." : "EXECUTAR SCAN"}
              </button>
            </div>
          </div>
        </RetroWindow>
      )}

      {/* 3. ERROR: IDEAS MISSING / LATENCY SPIKE (From Image 0) */}
      {!errorDismissed && (
        <RetroWindow
          title="ALERTA"
          variant="cream"
          icon="⚠️"
          onClose={() => setErrorDismissed(true)}
          statusText="CÓDIGO 0x404_IDEAS"
        >
          <div className="space-y-4 font-mono text-black">
            <div className="border border-black p-3 bg-white text-center">
              <h4 className="font-pixel text-[11px] font-bold text-red-600">
                IDEAS MISSING // PAINEL PRONTO
              </h4>
              <p className="mt-2 text-[10px] opacity-75">
                NENHUMA FALHA NÃO MONITORADA ENCONTRADA. TODA ROTA POSSUI MÉTRICA DEDICADA.
              </p>
            </div>

            <div className="flex justify-center">
              <button
                type="button"
                onClick={() => setErrorDismissed(true)}
                className="retro-bevel-btn bg-black text-white px-6 py-2 font-pixel text-[10px]"
              >
                OK
              </button>
            </div>
          </div>
        </RetroWindow>
      )}
    </div>
  );
}
