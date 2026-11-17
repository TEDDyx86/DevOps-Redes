import {
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Terminal,
  X,
  type LucideIcon,
} from "lucide-react";
import type { Page } from "./types";

type NavItem = { id: Page; label: string; icon: LucideIcon };

export default function Sidebar({
  navigation,
  page,
  activeIncidents,
  collapsed,
  onToggle,
  mobileOpen,
  onCloseMobile,
}: {
  navigation: NavItem[];
  page: Page;
  activeIncidents: number;
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  return (
    <aside
      className={`sidebar ${collapsed ? "collapsed" : ""}`}
      data-mobile-open={mobileOpen || undefined}
    >
      <div className="sidebar-head">
        <a href="#overview" className="brand" aria-label="AulaRedes, início">
          <span className="brand-mark">
            <Network size={22} />
          </span>
          {!collapsed && (
            <span>
              Aula<span className="brand-light">Redes</span>
              <small>OBSERVABILIDADE</small>
            </span>
          )}
        </a>
        <button
          type="button"
          className="icon-button sidebar-toggle"
          onClick={onToggle}
          aria-expanded={!collapsed}
          aria-label={
            collapsed ? "Expandir menu lateral" : "Recolher menu lateral"
          }
          title={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
        <button
          type="button"
          className="icon-button sidebar-close mobile-only"
          onClick={onCloseMobile}
          aria-label="Fechar navegação"
        >
          <X size={18} />
        </button>
      </div>
      {!collapsed && (
        <div className="workspace">
          <span className="workspace-icon">
            <Terminal size={18} />
          </span>
          <div>
            <strong>Projeto de redes</strong>
            <small>Laboratório local</small>
          </div>
          <span className="workspace-dot" />
        </div>
      )}
      <div className="nav-caption">MONITORAMENTO</div>
      <nav aria-label="Navegação principal">
        {navigation.map(({ id, label, icon: Icon }) => (
          <a
            href={`#${id}`}
            key={id}
            className={`nav-item ${page === id ? "active" : ""}`}
            aria-label={label}
            aria-current={page === id ? "page" : undefined}
            title={collapsed ? label : undefined}
            onClick={onCloseMobile}
          >
            <Icon size={18} />
            <span>{label}</span>
            {id === "incidents" && activeIncidents > 0 && (
              <span className="nav-count">{activeIncidents}</span>
            )}
          </a>
        ))}
      </nav>
      {!collapsed && (
        <div className="sidebar-bottom">
          <div className="version-pill">
            ETAPA 06 <span>TRÁFEGO E ACESSO</span>
          </div>
          <p>
            Da requisição ao alerta.
            <br />
            Um sinal de cada vez.
          </p>
          <div className="sidebar-author">
            <span>AR</span>
            <div>
              <strong>Trabalho final</strong>
              <small>Redes de Computadores</small>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
