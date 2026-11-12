import { PixelHero } from "../components/PixelHero";
import { FeatureGrid } from "../components/FeatureGrid";
import { navigate } from "../api";

const marqueeItems = [
  "WORKBYTE",
  "SINAL DE VERDADE",
  "PROCESSAMENTO EM TEMPO REAL",
  "8-BIT // FUTURISTA",
  "PROMETHEUS INSIDE",
  "WORKBYTE",
  "SINAL DE VERDADE",
  "PROCESSAMENTO EM TEMPO REAL",
  "8-BIT // FUTURISTA",
  "PROMETHEUS INSIDE",
];

export default function Landing() {
  return (
    <main className="font-mono text-parchment">
      <section className="crt-scanlines synth-grid relative min-h-screen overflow-hidden">
        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
          <span className="font-pixel text-xs text-magenta glow-magenta">WORKBYTE</span>
          <button
            onClick={() => navigate("/login")}
            className="font-pixel border-2 border-cyan px-4 py-2 text-[10px] text-cyan transition-colors hover:bg-cyan/10"
          >
            ENTRAR
          </button>
        </header>
        <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-10 px-6 pt-10 pb-24 md:grid-cols-2">
          <div className="crt-flicker">
            <h1 className="font-pixel text-3xl leading-relaxed md:text-4xl">
              <span className="text-parchment">TRABALHO</span>{" "}
              <span className="text-cyan glow-cyan">REAL</span>
              <br />
              <span className="text-magenta glow-magenta">EM PIXELS</span>
            </h1>
            <p className="mt-6 max-w-md text-sm leading-relaxed opacity-75">
              * O processador de tarefas do laboratório: cada requisição medida,
              cada falha observada, cada alerta entregue. Sem rotas falsas.
            </p>
            <button
              onClick={() => navigate("/login")}
              className="font-pixel mt-8 border-4 border-magenta bg-magenta/10 px-8 py-4 text-xs text-magenta glow-magenta transition-transform hover:translate-y-[-2px]"
            >
              ▶ ABRIR PAINEL
            </button>
          </div>
          <div className="border-2 border-panel-edge shadow-[0_0_40px_rgba(139,92,246,0.25)]">
            <PixelHero />
          </div>
        </div>
      </section>

      <section className="overflow-hidden border-y-2 border-panel-edge bg-panel py-3">
        <div className="marquee-track flex w-max gap-12 font-pixel text-[10px] text-violet">
          {marqueeItems.map((item, index) => (
            <span key={`${item}-${index}`}>{item} ✦</span>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="font-pixel text-sm text-cyan glow-cyan">SISTEMA EM CAMADAS</h2>
        <p className="mt-3 text-sm opacity-70">* Tudo que o WORKBYTE expõe, o Prometheus coleta.</p>
        <div className="mt-10">
          <FeatureGrid />
        </div>
      </section>

      <footer className="border-t-2 border-panel-edge bg-panel px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 text-center">
          <div className="flex gap-8 font-pixel text-[10px] text-parchment opacity-70">
            <span>♥</span><span>▶</span><span>◆</span><span>✉</span>
          </div>
          <p className="text-xs opacity-60">WORKBYTE — laboratório de redes · serviços medidos de verdade</p>
          <p className="text-[10px] opacity-40">/health · /work · /metrics · /mode</p>
        </div>
      </footer>
    </main>
  );
}
