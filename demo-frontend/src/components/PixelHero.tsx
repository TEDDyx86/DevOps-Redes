/** Cenário 8-bit do hero: sol magenta em scanlines, torre de servidor e chão em grade violeta. */
export function PixelHero() {
  const sunY = 118;
  const stripes = [10, 14, 6, 18, 8, 22, 12, 26, 16, 30, 20];
  const stars: Array<[number, number, number]> = [
    [18, 24, 4], [64, 14, 4], [110, 30, 3], [150, 10, 4], [196, 26, 3],
    [230, 18, 4], [34, 52, 3], [210, 46, 3], [88, 40, 3], [176, 56, 3],
    [240, 40, 3], [10, 44, 3], [130, 52, 3],
  ];
  const windows: Array<[number, number]> = [];
  for (let row = 0; row < 9; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      windows.push([250 + col * 14, 118 + row * 14]);
    }
  }
  return (
    <svg viewBox="0 0 320 200" className="block w-full" shapeRendering="crispEdges" role="img" aria-label="Cena 8-bit: sol magenta sobre torre de servidor com chão em grade violeta">
      <rect width="320" height="200" fill="#05060f" />
      {stars.map(([x, y, size], index) => (
        <rect key={`star-${index}`} x={x} y={y} width={size} height={size} fill={index % 3 === 0 ? "#00e5ff" : "#e8e6f0"} opacity={index % 4 === 0 ? 0.9 : 0.5} />
      ))}

      {/* sol magenta com faixas horizontais (scanlines) */}
      <circle cx="160" cy={sunY} r="46" fill="#ff2fd6" />
      <circle cx="160" cy={sunY} r="46" fill="none" stroke="#ff2fd6" strokeWidth="2" opacity="0.4" />
      <g fill="#05060f">
        {stripes.map((height, index) => (
          <rect key={`band-${index}`} x="100" y={sunY + 4 + index * 8} width="120" height={height} />
        ))}
      </g>
      <circle cx="160" cy={sunY} r="54" fill="#ff2fd6" opacity="0.12" />

      {/* torre de servidor */}
      <rect x="242" y="112" width="64" height="60" fill="#0a0b14" stroke="#8b5cf6" strokeWidth="2" />
      <rect x="252" y="102" width="44" height="10" fill="#0a0b14" stroke="#8b5cf6" strokeWidth="2" />
      {windows.map(([x, y], index) => (
        <rect key={`win-${index}`} x={x} y={y} width="6" height="6" fill={(index + (x > 300 ? 1 : 0)) % 4 === 0 ? "#ffb400" : "#00e5ff"} opacity={(index % 5 === 3) ? 0.25 : 0.9} />
      ))}

      {/* chão em grade violeta em perspectiva */}
      <g>
        <rect x="0" y="172" width="320" height="28" fill="#0a0b14" />
        {Array.from({ length: 13 }, (_, i) => (
          <line key={`v-${i}`} x1={160 + (i - 6) * 14} y1="172" x2={160 + (i - 6) * 44} y2="200" stroke="#8b5cf6" strokeWidth="1.5" opacity="0.55" />
        ))}
        {[176, 182, 190, 200].map((y, i) => (
          <line key={`h-${i}`} x1="0" y1={y} x2="320" y2={y} stroke="#8b5cf6" strokeWidth="1.5" opacity={0.2 + i * 0.15} />
        ))}
        <line x1="0" y1="172" x2="320" y2="172" stroke="#00e5ff" strokeWidth="1.5" opacity="0.5" />
      </g>

      {/* reflexo do sol no chão */}
      <rect x="146" y="172" width="28" height="28" fill="#ff2fd6" opacity="0.08" />
    </svg>
  );
}
