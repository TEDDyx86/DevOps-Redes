import React, { useState } from "react";

interface RetroWindowProps {
  title: string;
  icon?: string;
  subtitle?: string;
  variant?: "dark" | "cream" | "cyan";
  className?: string;
  children: React.ReactNode;
  initialCollapsed?: boolean;
  onClose?: () => void;
  statusText?: string;
}

export function RetroWindow({
  title,
  icon,
  subtitle,
  variant = "dark",
  className = "",
  children,
  initialCollapsed = false,
  onClose,
  statusText,
}: RetroWindowProps) {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [closed, setClosed] = useState(false);

  if (closed) return null;

  const isCream = variant === "cream";
  const isCyan = variant === "cyan";

  const outerBorder = isCream
    ? "border border-[#b8b89e] bg-[#e8e8c6] text-black shadow-[0_8px_24px_rgba(0,0,0,0.12)]"
    : isCyan
    ? "border border-cyan/45 bg-[#080a14] text-cyan"
    : "border border-panel-edge bg-[#090b16] text-white";

  const headerBg = isCream
    ? "bg-black text-[#E8E8C6]"
    : isCyan
    ? "bg-cyan/5 text-cyan border-b border-cyan/20"
    : "bg-[#1b1f3a] text-parchment border-b border-panel-edge";

  return (
    <div className={`flex flex-col overflow-hidden font-mono ${outerBorder} ${className}`}>
      {/* Title Bar */}
      <div className={`flex items-center justify-between px-4 py-3 select-none ${headerBg}`}>
        <div className="flex items-center gap-2 truncate">
          {icon && <span className="font-pixel text-[11px]">{icon}</span>}
          <span className="font-pixel text-[10px] tracking-wider truncate uppercase">
            {title}
          </span>
          {subtitle && (
            <span className="hidden sm:inline text-[9px] opacity-60">[{subtitle}]</span>
          )}
        </div>

        {/* Striped decoration */}
        <div className="mx-2 hidden h-px flex-1 bg-current opacity-10 md:flex" />

        {/* Window controls */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Minimizar janela"
            className="flex size-5 items-center justify-center border border-current/30 text-[10px] transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan active:translate-y-[1px]"
          >
            {collapsed ? "+" : "—"}
          </button>
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar janela"
              className="flex size-5 items-center justify-center border border-current/30 text-[10px] transition-colors hover:bg-magenta hover:text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan active:translate-y-[1px]"
            >
              ✕
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setClosed(true)}
              aria-label="Fechar janela"
              className="flex size-5 items-center justify-center border border-current/30 text-[10px] transition-colors hover:bg-magenta hover:text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan active:translate-y-[1px]"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Content Area */}
      {!collapsed && (
        <div className="flex-1 overflow-auto p-4 sm:p-5">
          {children}
        </div>
      )}

      {/* Bottom Placard / Status Strip (Mac OS 9 Style) */}
      {!collapsed && statusText && (
        <div className={`px-3 py-1 text-[9px] border-t flex items-center justify-between select-none ${
          isCream
            ? "border-black/30 bg-[#dedea8] text-black/70"
            : "border-panel-edge bg-black/40 text-parchment/60"
        }`}>
          <span>{statusText}</span>
          <span className="font-pixel text-[8px]">● OK</span>
        </div>
      )}
    </div>
  );
}
