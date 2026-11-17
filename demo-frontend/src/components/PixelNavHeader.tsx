import { navigate } from "../api";

export function PixelNavHeader() {
  return (
    <header className="border-b border-panel-edge bg-[#080912]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <a href="/" className="flex items-center gap-2 text-parchment" aria-label="WORKBYTE início">
          <span aria-hidden="true" className="size-2 bg-cyan" />
          <span className="font-pixel text-[10px] tracking-wider">
            WORKBYTE<span className="text-cyan">.EXE</span>
          </span>
        </a>
        <nav aria-label="Navegação principal" className="flex items-center gap-4 sm:gap-6">
          <a href="#recursos" className="hidden text-xs text-parchment/60 transition-colors hover:text-cyan sm:inline">
            Recursos
          </a>
          <button
            onClick={() => navigate("/login")}
            className="border border-cyan/60 px-4 py-2 text-xs font-semibold text-cyan transition-colors hover:bg-cyan hover:text-[#05060f] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan"
          >
            Entrar no painel
          </button>
        </nav>
      </div>
    </header>
  );
}
