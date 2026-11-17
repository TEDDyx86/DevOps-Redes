interface PixelHeroSceneProps {
  onStartClick: () => void;
}

export function PixelHeroScene({ onStartClick }: PixelHeroSceneProps) {
  // Stars in the night sky
  const stars: Array<[number, number, number, string]> = [
    [15, 20, 3, "#ffffff"],
    [45, 12, 4, "#00e5ff"],
    [85, 30, 2, "#ffffff"],
    [120, 15, 4, "#ffb400"],
    [160, 35, 3, "#ffffff"],
    [210, 18, 4, "#00e5ff"],
    [255, 28, 3, "#ffffff"],
    [290, 14, 4, "#ff2fd6"],
    [330, 32, 2, "#ffffff"],
    [370, 22, 3, "#00e5ff"],
    [70, 50, 3, "#ffffff"],
    [190, 55, 2, "#ffffff"],
    [310, 48, 3, "#ffb400"],
    [380, 60, 2, "#ffffff"],
  ];

  return (
    <div className="relative w-full overflow-hidden border border-panel-edge bg-[#0a0f24] shadow-[0_16px_48px_rgba(0,0,0,0.28)]">
      {/* 16-Bit / Pixel Art Canvas Scene */}
      <svg
        viewBox="0 0 400 240"
        className="block w-full h-auto select-none"
        shapeRendering="crispEdges"
        role="img"
        aria-label="Cena pixel art de floresta noturna com lua sorridente, pinheiros 16-bit e servidor de redes"
      >
        <defs>
          {/* Night sky gradient */}
          <linearGradient id="nightSky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#080c1f" />
            <stop offset="60%" stopColor="#142147" />
            <stop offset="100%" stopColor="#1e3a6a" />
          </linearGradient>

          {/* Forest mist gradient */}
          <linearGradient id="forestMist" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#19335c" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#0a1931" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {/* 1. Sky Background */}
        <rect width="400" height="240" fill="url(#nightSky)" />

        {/* 2. Stars */}
        {stars.map(([x, y, s, col], i) => (
          <rect
            key={`star-${i}`}
            x={x}
            y={y}
            width={s}
            height={s}
            fill={col}
            opacity={i % 2 === 0 ? 0.9 : 0.6}
          />
        ))}

        {/* 3. Smiling Pixel Moon (Directly inspired by Image 1) */}
        <g transform="translate(100, 20)">
          {/* Moon Glow */}
          <rect x="-12" y="-12" width="56" height="56" fill="#ffea75" opacity="0.15" />
          <rect x="-6" y="-6" width="44" height="44" fill="#ffea75" opacity="0.25" />

          {/* Yellow Moon Body */}
          <rect x="0" y="4" width="32" height="24" fill="#ffea75" />
          <rect x="4" y="0" width="24" height="32" fill="#ffea75" />

          {/* Moon shading */}
          <rect x="2" y="2" width="4" height="4" fill="#fff7b0" />
          <rect x="20" y="24" width="10" height="6" fill="#f0be30" />

          {/* Smiling Face Pixels */}
          {/* Left Eye */}
          <rect x="8" y="12" width="4" height="6" fill="#1b120c" />
          {/* Right Eye */}
          <rect x="20" y="12" width="4" height="6" fill="#1b120c" />
          {/* Smile mouth */}
          <rect x="12" y="22" width="8" height="2" fill="#1b120c" />
          <rect x="10" y="20" width="2" height="2" fill="#1b120c" />
          <rect x="20" y="20" width="2" height="2" fill="#1b120c" />
        </g>

        {/* 4. Golden Star Friend (from Image 1) */}
        <g transform="translate(290, 18)">
          <rect x="4" y="0" width="4" height="12" fill="#ffb400" />
          <rect x="0" y="4" width="12" height="4" fill="#ffb400" />
          <rect x="2" y="2" width="8" height="8" fill="#ffe066" />
        </g>

        {/* 5. Pixel Art Clouds Layer */}
        <g opacity="0.45" fill="#2d497c">
          <rect x="20" y="60" width="80" height="10" />
          <rect x="35" y="52" width="50" height="8" />
          <rect x="210" y="70" width="120" height="12" />
          <rect x="235" y="62" width="70" height="8" />
        </g>

        {/* 6. Distant Forest Skyline (Layer 1 - deep blue) */}
        <g fill="#102544">
          {Array.from({ length: 28 }).map((_, i) => {
            const tx = i * 15;
            const h = 30 + ((i * 7) % 25);
            return (
              <polygon
                key={`p1-${i}`}
                points={`${tx},180 ${tx + 8},${180 - h} ${tx + 16},180`}
              />
            );
          })}
        </g>

        {/* 7. Midground Pine Trees (Layer 2 - teal/green) */}
        <g fill="#144246">
          {Array.from({ length: 18 }).map((_, i) => {
            const tx = i * 24 - 10;
            const h = 45 + ((i * 11) % 35);
            return (
              <polygon
                key={`p2-${i}`}
                points={`${tx},195 ${tx + 12},${195 - h} ${tx + 24},195`}
              />
            );
          })}
        </g>

        {/* 8. Foreground Lush 16-Bit Pine Trees (Layer 3 - Emerald/Spring Green as Image 1) */}
        {/* Left giant tree */}
        <g transform="translate(0, 70)">
          {/* Foliage */}
          <polygon points="10,80 40,30 70,80" fill="#1f7a52" />
          <polygon points="15,75 40,32 65,75" fill="#2eb872" />
          <polygon points="12,110 40,60 68,110" fill="#1f7a52" />
          <polygon points="18,105 40,62 62,105" fill="#2eb872" />
          {/* Trunk */}
          <rect x="34" y="105" width="12" height="40" fill="#5c3826" />
          <rect x="38" y="105" width="4" height="40" fill="#7a4b33" />
        </g>

        {/* Right giant tree with hollow (as Image 1) */}
        <g transform="translate(330, 65)">
          <polygon points="10,80 35,25 60,80" fill="#1f7a52" />
          <polygon points="14,75 35,28 56,75" fill="#2eb872" />
          <polygon points="8,115 35,55 62,115" fill="#1f7a52" />
          <polygon points="12,110 35,58 58,110" fill="#2eb872" />
          {/* Tree trunk with owl hole */}
          <rect x="28" y="110" width="16" height="45" fill="#5c3826" />
          <rect x="32" y="110" width="6" height="45" fill="#7a4b33" />
          {/* Hollow */}
          <ellipse cx="36" cy="130" rx="3" ry="5" fill="#1c0f08" />
        </g>

        {/* 9. Ground Path & Grass (Pixel steps and flowers) */}
        <g>
          {/* Dirt bank */}
          <rect x="0" y="185" width="400" height="55" fill="#1b2420" />
          {/* Lush Grass top edge with pixel fringe */}
          <rect x="0" y="180" width="400" height="12" fill="#2eb872" />
          {Array.from({ length: 40 }).map((_, i) => (
            <rect
              key={`grass-${i}`}
              x={i * 10}
              y={178 + (i % 3) * 2}
              width="6"
              height="4"
              fill="#52de97"
            />
          ))}

          {/* Dirt walking path through the center */}
          <polygon
            points="120,240 280,240 260,192 140,192"
            fill="#d2a679"
            opacity="0.85"
          />
          <polygon
            points="135,240 265,240 250,192 150,192"
            fill="#e6c299"
          />

          {/* Tiny Yellow pixel flowers */}
          <rect x="80" y="174" width="4" height="4" fill="#ffea75" />
          <rect x="82" y="178" width="2" height="4" fill="#2eb872" />
          <rect x="110" y="176" width="4" height="4" fill="#ffea75" />
          <rect x="290" y="175" width="4" height="4" fill="#ffea75" />
          <rect x="315" y="173" width="4" height="4" fill="#ff2fd6" />
        </g>
      </svg>

      {/* Foreground Hero Overlay with 3D Pixel Typography & START Button */}
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-between p-4 text-center pointer-events-none sm:p-6">
        {/* Top Tag */}
        <div className="font-pixel text-[9px] tracking-widest text-[#E8E8C6] bg-black/75 px-3 py-1 border border-[#E8E8C6]/40 uppercase pointer-events-auto">
          REDES DE COMPUTADORES &amp; INTERNET • 2026
        </div>

        {/* Center Giant 3D Title (Styled identically to "PORTFOLIO GRAPHIC DESIGNER 2025" in Image 1) */}
        <div className="my-auto drop-shadow-[0_4px_10px_rgba(0,0,0,0.7)]">
          <h1 className="font-pixel text-2xl tracking-wide text-[#ffea75] sm:text-4xl md:text-5xl">
            WORKBYTE
          </h1>
          <p className="mt-2 font-pixel text-[11px] tracking-wider text-[#ff9900] sm:text-sm">
            OBSERVABILIDADE // MICROSSERVIÇOS
          </p>
          <p className="mt-2 text-xs sm:text-sm text-[#E8E8C6] max-w-lg mx-auto font-mono bg-black/60 px-3 py-1 border border-black/40">
            Cada requisição real • Cada falha medida • 0 rotas falsas
          </p>
        </div>

        {/* Pill START Button (Directly inspired by Image 1: Yellow with orange base and rounded border) */}
        <div className="pointer-events-auto pb-2">
          <button
            type="button"
            onClick={onStartClick}
            className="group relative inline-flex cursor-pointer select-none items-center justify-center border border-[#b45309] bg-[#ffea75] px-6 py-3 font-pixel text-[10px] tracking-wider text-black shadow-[0_4px_0_#b45309] transition-colors hover:bg-[#fff099] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#ffea75] active:translate-y-1 active:shadow-none sm:px-9 sm:text-xs"
          >
            <span className="flex items-center gap-2">
              <span className="text-[#b45309] group-hover:translate-x-1 transition-transform">▶</span>
              <span>START / ENTRAR</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
