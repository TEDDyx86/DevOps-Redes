import React, { useState, useEffect, useCallback } from "react";
import useEmblaCarousel from "embla-carousel-react";

export interface CarouselSlide {
  id: string;
  tag: string;
  title: string;
  badge: string;
  description: string;
  endpoint: string;
  details: string[];
  actionLabel?: string;
  onAction?: () => void;
  accentColor: "cyan" | "magenta" | "amber" | "violet";
  icon: string;
}

interface RetroCarouselProps {
  slides: CarouselSlide[];
  onSelectSlide?: (slide: CarouselSlide) => void;
}

export function RetroCarousel({ slides, onSelectSlide }: RetroCarouselProps) {
  const [emblaRef, emblaApi] = useEmblaCarousel({
    loop: true,
    align: "start",
    skipSnaps: false,
  });

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [scrollSnaps, setScrollSnaps] = useState<number[]>([]);

  const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);
  const scrollTo = useCallback((index: number) => emblaApi && emblaApi.scrollTo(index), [emblaApi]);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    onSelect();
    setScrollSnaps(emblaApi.scrollSnapList());
    emblaApi.on("select", onSelect);
    emblaApi.on("reInit", onSelect);
    return () => {
      emblaApi.off("select", onSelect);
      emblaApi.off("reInit", onSelect);
    };
  }, [emblaApi, onSelect]);

  const toneMap = {
    cyan: {
      border: "border-cyan/70 hover:border-cyan",
      badge: "bg-cyan/15 text-cyan border-cyan/40",
      glow: "glow-cyan",
      btn: "border-cyan text-cyan hover:bg-cyan/15",
      accent: "#00e5ff",
    },
    magenta: {
      border: "border-magenta/70 hover:border-magenta",
      badge: "bg-magenta/15 text-magenta border-magenta/40",
      glow: "glow-magenta",
      btn: "border-magenta text-magenta hover:bg-magenta/15",
      accent: "#ff2fd6",
    },
    amber: {
      border: "border-amber/70 hover:border-amber",
      badge: "bg-amber/15 text-amber border-amber/40",
      glow: "glow-amber",
      btn: "border-amber text-amber hover:bg-amber/15",
      accent: "#ffb400",
    },
    violet: {
      border: "border-violet/70 hover:border-violet",
      badge: "bg-violet/15 text-violet border-violet/40",
      glow: "",
      btn: "border-violet text-violet hover:bg-violet/15",
      accent: "#8b5cf6",
    },
  };

  return (
    <div className="relative w-full">
      {/* Header controls bar */}
      <div className="flex items-center justify-between pb-4 border-b border-panel-edge mb-6">
        <div className="flex items-center gap-3">
          <span className="font-pixel text-[10px] text-parchment/60 uppercase tracking-widest">
            SLIDES // 0{selectedIndex + 1} DE 0{slides.length}
          </span>
          <span className="hidden sm:inline-block text-[10px] text-cyan">
            [EMBLA INTERACTIVE]
          </span>
        </div>

        {/* Nostalgia / 8-bit Bevel Navigation Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={scrollPrev}
            aria-label="Slide anterior"
            className="retro-bevel-btn bg-[#252525] text-parchment px-3 py-2 text-xs flex items-center justify-center font-pixel cursor-pointer select-none"
          >
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none" className="rotate-180">
              <path d="M2 1 L6 4 L2 7 Z" fill="currentColor" />
            </svg>
          </button>
          <button
            type="button"
            onClick={scrollNext}
            aria-label="Próximo slide"
            className="retro-bevel-btn bg-[#252525] text-parchment px-3 py-2 text-xs flex items-center justify-center font-pixel cursor-pointer select-none"
          >
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
              <path d="M2 1 L6 4 L2 7 Z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </div>

      {/* Embla Viewport */}
      <div className="overflow-hidden cursor-grab active:cursor-grabbing" ref={emblaRef}>
        <div className="flex -ml-4">
          {slides.map((slide, idx) => {
            const tone = toneMap[slide.accentColor];
            const isActive = idx === selectedIndex;
            return (
              <div
                key={slide.id}
                className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] pl-4 min-w-0"
              >
                <div
                  onClick={() => onSelectSlide?.(slide)}
                  className={`h-full flex flex-col justify-between border-2 bg-[#0a0b14]/90 p-6 transition-all duration-200 ${
                    tone.border
                  } ${isActive ? "shadow-[0_0_24px_rgba(0,229,255,0.2)]" : "opacity-85"}`}
                >
                  <div>
                    {/* Top Meta */}
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-pixel text-[9px] px-2 py-1 border ${tone.badge}`}>
                        {slide.badge}
                      </span>
                      <span className="font-pixel text-sm">{slide.icon}</span>
                    </div>

                    {/* Title */}
                    <h3 className={`mt-4 font-pixel text-xs leading-relaxed text-parchment ${tone.glow}`}>
                      {slide.title}
                    </h3>

                    {/* Endpoint tag */}
                    <p className="mt-2 text-[10px] text-cyan font-mono bg-black/60 px-2 py-1 border border-panel-edge w-fit">
                      {slide.endpoint}
                    </p>

                    {/* Description */}
                    <p className="mt-4 text-xs leading-relaxed opacity-75">
                      {slide.description}
                    </p>

                    {/* Details list */}
                    <ul className="mt-4 space-y-1.5 text-[11px] opacity-70 border-t border-panel-edge pt-3">
                      {slide.details.map((item, dIdx) => (
                        <li key={dIdx} className="flex items-start gap-1.5">
                          <span className="text-cyan">✦</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Bottom Action */}
                  {slide.actionLabel && (
                    <div className="mt-6 pt-4 border-t border-panel-edge/80">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          slide.onAction?.();
                        }}
                        className={`w-full font-pixel border-2 px-3 py-2.5 text-[9px] transition-colors ${tone.btn}`}
                      >
                        {slide.actionLabel}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pagination dots (Nostalgia / Apple inspired) */}
      <div className="mt-6 flex items-center justify-center gap-2 select-none">
        {scrollSnaps.map((_, index) => (
          <button
            key={index}
            onClick={() => scrollTo(index)}
            aria-label={`Ir para slide ${index + 1}`}
            className={`transition-all duration-200 border border-current ${
              index === selectedIndex
                ? "w-8 h-2.5 bg-cyan text-cyan glow-cyan"
                : "w-2.5 h-2.5 bg-transparent text-panel-edge hover:text-parchment"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
