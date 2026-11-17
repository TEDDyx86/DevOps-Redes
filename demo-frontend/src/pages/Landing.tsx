import { PixelNavHeader } from "../components/PixelNavHeader";
import { PixelHeroScene } from "../components/PixelHeroScene";
import { navigate } from "../api";

const capabilities = [
  {
    label: "Sinal do serviço",
    detail: "Verificação real de disponibilidade do web-demo.",
  },
  {
    label: "Requisições medidas",
    detail: "O endpoint /work responde com duração observável.",
  },
  {
    label: "Métricas HTTP",
    detail: "Contadores de requisições e códigos coletados pelo Prometheus.",
  },
];

export default function Landing() {
  return (
    <main className="min-h-screen bg-[#05060f] font-mono text-parchment">
      <PixelNavHeader />

      <section id="hero" className="mx-auto max-w-6xl px-4 pt-6 pb-10 sm:px-6 sm:pt-10">
        <PixelHeroScene onStartClick={() => navigate("/login")} />
      </section>

      <section
        id="recursos"
        aria-labelledby="capabilities-title"
        className="mx-auto max-w-6xl px-4 pb-16 sm:px-6 sm:pb-20"
      >
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-panel-edge pb-4">
          <div>
            <p className="font-pixel text-[9px] tracking-[0.18em] text-cyan">
              OBSERVABILIDADE DO SERVIÇO
            </p>
            <h2 id="capabilities-title" className="mt-3 text-lg font-semibold text-parchment sm:text-xl">
              Uma visão direta do que está acontecendo.
            </h2>
          </div>
          <span className="text-xs text-parchment/50">Ambiente local de demonstração</span>
        </div>

        <div className="grid gap-px overflow-hidden border border-panel-edge bg-panel-edge md:grid-cols-3">
          {capabilities.map((capability) => (
            <article key={capability.label} className="min-h-32 bg-[#090b16] p-5 sm:p-6">
              <h3 className="mt-4 text-sm font-semibold text-parchment">{capability.label}</h3>
              <p className="mt-2 text-xs leading-relaxed text-parchment/60">
                {capability.detail}
              </p>
            </article>
          ))}
        </div>

        <p className="mt-5 max-w-3xl text-xs leading-relaxed text-parchment/45">
          Acesse o painel para acompanhar o sinal, executar uma requisição de trabalho e consultar
          os contadores HTTP observados. Os controles de falha são restritos ao laboratório.
        </p>
      </section>

      <footer className="border-t border-panel-edge bg-[#080912] px-4 py-6 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-xs text-parchment/50 sm:flex-row sm:items-center sm:justify-between">
          <span className="font-pixel text-[9px] text-parchment/70">WORKBYTE // LABORATÓRIO DE REDES</span>
          <span>Docker Compose · Prometheus · CoreDNS · PostgreSQL · SMTP</span>
        </div>
      </footer>
    </main>
  );
}
