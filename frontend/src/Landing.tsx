import { ArrowRight, Database, Globe2, Mail, Server } from "lucide-react";

const pillars = [
  { icon: Server, title: "HTTP", text: "Disponibilidade e tráfego do serviço." },
  { icon: Database, title: "PostgreSQL", text: "Consultas, conexões e desempenho SQL." },
  { icon: Globe2, title: "DNS", text: "Resolução de nomes do laboratório." },
  { icon: Mail, title: "SMTP", text: "Fila e entrega do correio local." },
];

export default function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <main className="landing-shell">
      <header className="landing-top">
        <div className="landing-brand-wrap">
          <span className="landing-brand">
            WORK<span>BYTE</span>
          </span>
          <small className="landing-brand-sub">AulaRedes · Observabilidade</small>
        </div>
        <button type="button" className="button primary" onClick={onEnter}>
          Entrar
          <ArrowRight size={17} />
        </button>
      </header>
      <section className="landing-hero">
        <span className="eyebrow">OBSERVABILIDADE DE REDES</span>
        <h1>
          Quatro serviços.
          <br />
          <span className="landing-glow">Um ponto de observação.</span>
        </h1>
        <p>
          Da primeira sonda ao alerta: acompanhe o caminho de uma falha no
          laboratório local — em tempo real.
        </p>
        <button
          type="button"
          className="button primary landing-cta"
          onClick={onEnter}
        >
          Acessar o painel
          <ArrowRight size={17} />
        </button>
      </section>
      <section className="landing-pillars" aria-label="Serviços monitorados">
        {pillars.map(({ icon: Icon, title, text }) => (
          <article key={title} className="landing-pillar">
            <Icon size={20} />
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </section>
      <footer className="landing-foot">
        <p>Projeto final · Redes de Computadores</p>
      </footer>
    </main>
  );
}
