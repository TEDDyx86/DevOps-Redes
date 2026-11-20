import { useEffect, useRef } from "react";
import bg8Bit3d from "../assets/bg-8bit-3d.jpg";

export function Arcade3DBackground() {
  const stageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = stageRef.current;
    if (!el || typeof window === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const onMove = (event: PointerEvent) => {
      const nx = (event.clientX / window.innerWidth) * 2 - 1;
      const ny = (event.clientY / window.innerHeight) * 2 - 1;
      targetX = Math.max(-1, Math.min(1, nx));
      targetY = Math.max(-1, Math.min(1, ny));
      if (!raf) {
        raf = window.requestAnimationFrame(tick);
      }
    };

    const tick = () => {
      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;
      el.style.setProperty("--mx", currentX.toFixed(4));
      el.style.setProperty("--my", currentY.toFixed(4));
      if (Math.abs(targetX - currentX) > 0.002 || Math.abs(targetY - currentY) > 0.002) {
        raf = window.requestAnimationFrame(tick);
      } else {
        raf = 0;
      }
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div
      ref={stageRef}
      aria-hidden="true"
      className="arcade-3d-stage pointer-events-none fixed inset-0 z-0 overflow-hidden"
    >
      {/* Arte panorâmica 8-bit/voxel 3D com câmera viva + parallax 3D */}
      <div className="arcade-3d-backdrop-tilt">
        <div
          className="arcade-3d-artwork pixelated-art"
          style={{ backgroundImage: `url(${bg8Bit3d})` }}
        />
      </div>

      {/* Pulso de brilho synthwave no sol e horizonte */}
      <div className="arcade-3d-sun-aura" />

      {/* Estrelas 8-bit cintilantes em parallax */}
      <div className="arcade-3d-stars arcade-3d-stars-far" />
      <div className="arcade-3d-stars arcade-3d-stars-near" />

      {/* Trilhas de luz / naves pixeladas cruzando o céu */}
      <div className="arcade-3d-streaks">
        <span className="streak streak-1" />
        <span className="streak streak-2" />
        <span className="streak streak-3" />
      </div>

      {/* Overlay de grade 3D correndo sobre a rodovia neon */}
      <div className="arcade-3d-floor-wrap">
        <div className="arcade-3d-floor" />
      </div>

      {/* Voxels 3D neon flutuando em primeiro plano */}
      <div className="arcade-3d-voxels">
        <span className="voxel voxel-1" />
        <span className="voxel voxel-2" />
        <span className="voxel voxel-3" />
        <span className="voxel voxel-4" />
        <span className="voxel voxel-5" />
        <span className="voxel voxel-6" />
        <span className="voxel voxel-7" />
        <span className="voxel voxel-8" />
      </div>

      {/* Vinheta suave + scanlines CRT para manter leitura impecável */}
      <div className="arcade-3d-vignette" />
    </div>
  );
}
