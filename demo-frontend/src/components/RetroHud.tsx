import { useEffect, useState } from "react";

interface RetroHudProps {
  workCount?: number;
  lastLatencyMs?: number;
  online?: boolean | null;
  mode?: string | null;
  onRequestWork?: () => void;
  busy?: boolean;
}

export function RetroHud({
  workCount = 0,
  lastLatencyMs,
  online = true,
  mode = "normal",
  onRequestWork,
  busy = false,
}: RetroHudProps) {
  const [pulse, setPulse] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setPulse((p) => (p + 1) % 100);
    }, 120);
    return () => clearInterval(timer);
  }, []);

  // Compute active segments for thruster output (10 segments)
  const thrusterSegments = 10;
  const activeThrusters = busy
    ? 9
    : Math.min(10, Math.max(2, (workCount % 8) + 2));

  // Compute power bars
  const powerA = Math.min(100, Math.max(30, (pulse * 2) % 100));
  const powerB = mode === "slow" ? 85 : mode === "offline" ? 10 : 65;
  const powerC = online ? 92 : 0;

  return (
    <div className="relative border-2 border-cyan/60 bg-[#05060f] p-4 sm:p-6 font-mono text-cyan select-none shadow-[0_0_30px_rgba(0,229,255,0.15)]">
      {/* Top Console Bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-cyan/40 pb-3 gap-2">
        <div className="flex items-center gap-3">
          <div className="size-2 rounded-none bg-magenta animate-ping" />
          <span className="font-pixel text-[10px] tracking-widest text-parchment">
            REDS // EXPLORER MK.3
          </span>
          <span className="text-[10px] opacity-70">
            • RCS: LABORATÓRIO REDES
          </span>
        </div>
        <div className="flex items-center gap-2 text-[9px] font-pixel">
          <span className={online ? "text-cyan glow-cyan" : "text-magenta glow-magenta"}>
            {online ? "● SINAL NOMINAL" : "✖ CARRIER LOST"}
          </span>
          <span className="opacity-40">|</span>
          <span className="text-amber">MODO: {mode?.toUpperCase()}</span>
        </div>
      </div>

      {/* Main Grid Display: Left = 3D Course View, Right = Telemetry & Power */}
      <div className="mt-4 grid gap-4 lg:grid-cols-12">
        {/* Course View (Wireframe 3D grid with perspective horizon) */}
        <div className="relative lg:col-span-7 h-56 sm:h-64 border border-cyan/40 bg-black/80 overflow-hidden flex flex-col justify-between p-3">
          <div className="flex items-center justify-between text-[9px] opacity-60">
            <span>COURSE VIEW // PERSPECTIVE VECTOR</span>
            <span>GRID: 40x40 U</span>
          </div>

          {/* Perspective grid animation */}
          <div className="absolute inset-x-0 bottom-0 top-10 overflow-hidden">
            <div className="absolute inset-0 flex items-center justify-center">
              {/* Wireframe sun / target orb */}
              <div
                className={`size-12 rounded-full border-2 transition-all duration-300 ${
                  busy
                    ? "border-magenta bg-magenta/20 scale-125 glow-magenta"
                    : "border-cyan/70 bg-cyan/10"
                }`}
              />
              <div className="absolute size-24 rounded-full border border-cyan/20 animate-spin" />
              <div className="absolute size-36 rounded-full border border-dashed border-cyan/15" />
            </div>

            {/* Ground grid lines */}
            <div className="absolute inset-x-0 bottom-0 h-28 perspective-grid">
              <div className="w-full h-full perspective-plane" />
            </div>

            {/* Target coordinates floating box */}
            <div className="absolute top-4 left-4 border border-cyan/40 bg-black/60 px-2 py-1 text-[9px]">
              TGT: 127.0.0.1:8001
              <br />
              PATH: /work
            </div>
            {lastLatencyMs !== undefined && (
              <div className="absolute top-4 right-4 border border-amber/40 bg-black/60 px-2 py-1 text-[9px] text-amber">
                LAT: {lastLatencyMs} ms
              </div>
            )}
          </div>

          <div className="relative z-10 flex items-center justify-between text-[8px] opacity-50">
            <span>AZIMUTH: 284°</span>
            <span>SCALE: 1:1 LIVE</span>
          </div>
        </div>

        {/* Right Side: Power distribution, approach grid, radiation */}
        <div className="lg:col-span-5 flex flex-col justify-between gap-4">
          {/* Power distribution bars */}
          <div className="border border-cyan/40 bg-black/60 p-3">
            <span className="font-pixel text-[9px] opacity-70">DISTRIBUIÇÃO DE FLUXO</span>
            <div className="mt-2 grid grid-cols-3 gap-2 h-14">
              <div className="border border-cyan/30 flex flex-col justify-end p-1 bg-cyan/5">
                <div
                  className="w-full bg-cyan transition-all duration-300"
                  style={{ height: `${powerA}%` }}
                />
                <span className="text-[7px] text-center mt-1">CPU</span>
              </div>
              <div className="border border-magenta/30 flex flex-col justify-end p-1 bg-magenta/5">
                <div
                  className="w-full bg-magenta transition-all duration-300"
                  style={{ height: `${powerB}%` }}
                />
                <span className="text-[7px] text-center mt-1">REDE</span>
              </div>
              <div className="border border-amber/30 flex flex-col justify-end p-1 bg-amber/5">
                <div
                  className="w-full bg-amber transition-all duration-300"
                  style={{ height: `${powerC}%` }}
                />
                <span className="text-[7px] text-center mt-1">SESSÃO</span>
              </div>
            </div>
          </div>

          {/* Celestial Grid / Radar of microservices */}
          <div className="border border-cyan/40 bg-black/60 p-3">
            <span className="font-pixel text-[9px] opacity-70">RADAR DE SERVIÇOS</span>
            <div className="mt-2 grid grid-cols-2 gap-2 text-[9px]">
              <div className="border border-panel-edge p-1.5 flex items-center justify-between">
                <span>POSTGRES</span>
                <span className="text-cyan">5432 ●</span>
              </div>
              <div className="border border-panel-edge p-1.5 flex items-center justify-between">
                <span>COREDNS</span>
                <span className="text-cyan">53 ●</span>
              </div>
              <div className="border border-panel-edge p-1.5 flex items-center justify-between">
                <span>SMTP MON</span>
                <span className="text-cyan">25 ●</span>
              </div>
              <div className="border border-panel-edge p-1.5 flex items-center justify-between">
                <span>PROMETHEUS</span>
                <span className="text-cyan">9090 ●</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Thruster Output Segmented Bar Gauge (Pink / Coral Neon as in Image 2) */}
      <div className="mt-4 border border-cyan/40 bg-black/60 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="font-pixel text-[9px] text-magenta glow-magenta">
            VAZÃO PRINCIPAL DE REQUISIÇÕES // THROUGHPUT
          </span>
          <span className="text-[9px] text-parchment/70">
            {busy ? "TRANSMITINDO..." : `${workCount} REQUISITADAS`}
          </span>
        </div>
        <div className="grid grid-cols-10 gap-1.5 h-6">
          {Array.from({ length: thrusterSegments }).map((_, i) => {
            const isActive = i < activeThrusters;
            return (
              <div
                key={i}
                className={`border border-magenta/40 transition-all duration-150 ${
                  isActive
                    ? "bg-magenta shadow-[0_0_8px_rgba(255,47,214,0.7)]"
                    : "bg-magenta/10"
                }`}
              />
            );
          })}
        </div>
      </div>

      {/* Bottom System Information banner & Interactive trigger */}
      <div className="mt-4 flex flex-wrap items-center justify-between border-t border-cyan/40 pt-3 gap-3">
        <div className="text-[10px] space-y-0.5 opacity-80">
          <p className="font-pixel text-[9px] text-parchment">SYSTEM INFORMATION // STACK AULAREDES</p>
          <p className="text-[9px] opacity-60">// Prometheus Exporter: Active • Retenção: 7 dias • Docker Stack</p>
        </div>

        {onRequestWork && (
          <button
            type="button"
            onClick={onRequestWork}
            disabled={busy}
            className="retro-bevel-btn bg-cyan text-black px-4 py-2 font-pixel text-[9px] font-bold hover:bg-cyan/90 disabled:opacity-50 select-none cursor-pointer"
          >
            {busy ? "DISPARANDO..." : "▶ DISPARAR /WORK"}
          </button>
        )}
      </div>
    </div>
  );
}
