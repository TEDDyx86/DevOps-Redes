interface Feature {
  icon: string;
  title: string;
  description: string;
}

const features: Feature[] = [
  { icon: "▶", title: "PROCESSAMENTO", description: "Tarefas /work executadas com latência medida em tempo real." },
  { icon: "◆", title: "MODOS DE OPERAÇÃO", description: "Normal, lento e offline — cada fase com o próprio sinal." },
  { icon: "◈", title: "OBSERVABILIDADE", description: "Contadores e histogramas expostos em /metrics no formato Prometheus." },
  { icon: "✉", title: "ALERTAS", description: "Incidentes viram alertas e e-mails antes de virarem problema." },
];

export function FeatureGrid() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {features.map((f) => (
        <div key={f.title} className="dialog-rpg border-2 border-panel-edge bg-panel p-6">
          <span className="font-pixel text-sm text-magenta glow-magenta">{f.icon}</span>
          <h3 className="mt-3 font-pixel text-xs text-cyan">{f.title}</h3>
          <p className="mt-2 text-sm opacity-75">{f.description}</p>
        </div>
      ))}
    </div>
  );
}
