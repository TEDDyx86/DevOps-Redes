# Experiência Workbyte no dashboard principal — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Em `:8000`, entregar landing pública Workbyte → login existente → dashboard completo com tema escuro/neon e menu lateral retrátil, preservando autenticação, APIs e as nove áreas.

**Architecture:** Reestilizar o frontend principal (`frontend/`): tokens de design trocados em `styles.css`, novo componente `Sidebar.tsx` extraído de `App.tsx` com colapso persistido, novo `Landing.tsx` integrado ao `Auth.tsx` antes do login. Nenhuma mudança de backend, endpoints ou autenticação.

**Tech Stack:** React 19, TypeScript, Vite, CSS puro (variáveis), lucide-react, Vitest (`renderToStaticMarkup`, ambiente node).

**Spec:** `docs/superpowers/specs/2026-11-13-workbyte-dashboard-experience-design.md`

## Global Constraints

- Não alterar endpoints, contratos de API, autenticação (`Auth.tsx`/`api.ts` lógica), credenciais ou fontes de dados.
- Nenhum indicador simulado: todos os dados vêm das APIs existentes.
- A demo `:8011` (`demo-frontend/`, `demo/`, `web-demo`) não é tocada por este plano.
- Paleta Workbyte (da demo): `#05060f` bg, `#0a0b14` panel, `#1b1f3a` edge, `#00e5ff` cyan, `#8b5cf6` violet, `#ff2fd6` magenta, `#ffb400` amber, `#e8e6f0` texto; fonte de display `"Press Start 2P"`, corpo `"IBM Plex Mono"`.
- Menu: expandido (ícone+rótulo), recolhido (ícone + `title` + `aria-label`), `aria-expanded` no controle, drawer em ≤850px, preferência em `localStorage`.
- Comandos de teste do frontend rodam em `frontend/`: `npm test` (Vitest, node) e `npm run build` (`tsc -b && vite build`).
- Testes do frontend não usam DOM real (sem jsdom instalado): componentizar para renderizar com `renderToStaticMarkup` e isolar lógica sem `window`.

---

### Task 1: Tokens de design e fontes Workbyte

**Files:**
- Modify: `frontend/src/styles.css:1-15` (bloco `:root`)
- Modify: `frontend/src/main.tsx:4-9` (imports de fontes)
- Modify: `frontend/package.json` (dependência `@fontsource/press-start-2p`)

**Interfaces:**
- Consumes: nada (ponto de partida).
- Produces: variáveis CSS `--bg`, `--panel`, `--panel-raised`, `--surface`, `--surface-raised`, `--line`, `--muted`, `--text`, `--text-soft`, `--accent`, `--accent-violet`, `--accent-magenta`, `--green`, `--red`, `--yellow`, `--pixel` — usadas por Tasks 2, 3 e 4.

- [ ] **Step 1: Instalar a fonte de display**

Em `frontend/`, rode:

```
npm install @fontsource/press-start-2p
```

Isso adiciona `"@fontsource/press-start-2p": "^5.3.0"` a `frontend/package.json` e atualiza `package-lock.json`.

- [ ] **Step 2: Trocar os imports de fonte em `main.tsx`**

Substitua em `frontend/src/main.tsx` as linhas:

```tsx
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import "@fontsource/dm-sans/latin-700.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "./styles.css";
```

por:

```tsx
import "@fontsource/press-start-2p";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-700.css";
import "./styles.css";
```

- [ ] **Step 3: Substituir o bloco `:root` de `styles.css`**

Substitua em `frontend/src/styles.css` (linhas 1-15) o bloco inteiro:

```css
:root {
  font-family: "DM Sans", "Segoe UI", sans-serif;
  color: oklch(28% 0.021 285);
  background: oklch(97.2% 0.004 285);
  font-synthesis: none;
  font-weight: 400;
  font-size: 14px;
  --surface: oklch(99.5% 0.002 285);
  --line: oklch(91.7% 0.008 285);
  --muted: oklch(54% 0.019 285);
  --accent: oklch(51% 0.18 295);
  --green: oklch(43% 0.09 164);
  --red: oklch(48% 0.16 25);
  --yellow: oklch(45% 0.1 75);
}
```

por:

```css
:root {
  font-family: "IBM Plex Mono", "Segoe UI", monospace;
  color: #e8e6f0;
  background: #05060f;
  font-synthesis: none;
  font-weight: 400;
  font-size: 14px;
  --bg: #05060f;
  --panel: #0a0b14;
  --panel-raised: #101326;
  --surface: #0a0b14;
  --surface-raised: #101326;
  --line: #1b1f3a;
  --muted: #9aa3c0;
  --text: #e8e6f0;
  --text-soft: #c9cfe4;
  --accent: #00e5ff;
  --accent-violet: #8b5cf6;
  --accent-magenta: #ff2fd6;
  --green: #00e5a8;
  --red: #ff5470;
  --yellow: #ffb400;
  --pixel: "Press Start 2P", "IBM Plex Mono", monospace;
}
```

Os nomes `--surface`, `--line`, `--muted`, `--accent`, `--green`, `--red`, `--yellow` são preservados de propósito: o restante do arquivo que usa essas variáveis muda de tema automaticamente.

- [ ] **Step 4: Verificar que o build e os testes passam**

Em `frontend/`, rode:

```
npm test
npm run build
```

Esperado: testes existentes passam (3 arquivos: `resourceState.test.tsx`, `incidents.test.tsx` e nenhum outro — 2 arquivos de teste na pasta `src/`); build conclui sem erros de TypeScript.

- [ ] **Step 5: Commit**

```
git add frontend/src/styles.css frontend/src/main.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(dashboard): tokens de design Workbyte e fontes Press Start 2P + IBM Plex Mono"
```

---

### Task 2: Menu lateral retrátil com persistência e drawer

**Files:**
- Create: `frontend/src/sidebarPreference.ts`
- Test: `frontend/src/sidebarPreference.test.ts`
- Create: `frontend/src/Sidebar.tsx`
- Test: `frontend/src/sidebar.test.tsx`
- Modify: `frontend/src/App.tsx` (estado, JSX do aside → `<Sidebar/>`, botão hamburger no topbar)
- Modify: `frontend/src/styles.css` (regras de colapso + drawer nas media queries 850px e 580px)

**Interfaces:**
- Consumes: variáveis CSS da Task 1; `navigation`, `page`, `activeIncidents` existentes em `App.tsx`; `type { Page }` de `./types`.
- Produces: `Sidebar({ navigation, page, activeIncidents, collapsed, onToggle, mobileOpen, onCloseMobile })` (default export); `readSidebarPreference(): boolean` e `saveSidebarPreference(collapsed: boolean)`; chave `localStorage` `workbyte-sidebar-collapsed`.

- [ ] **Step 1: Escrever o teste da preferência (falha primeiro)**

Crie `frontend/src/sidebarPreference.test.ts`:

```ts
import { afterEach, describe, expect, it } from "vitest";
import {
  readSidebarPreference,
  saveSidebarPreference,
} from "./sidebarPreference";

type Store = Record<string, string>;

function fakeWindow(store: Store) {
  return {
    localStorage: {
      getItem: (key: string) => (key in store ? store[key] : null),
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
    },
  };
}

const originalWindow = (globalThis as { window?: unknown }).window;

afterEach(() => {
  (globalThis as { window?: unknown }).window = originalWindow;
});

describe("preferência do menu lateral", () => {
  it("sem window, assume expandido e não falha ao salvar", () => {
    expect(readSidebarPreference()).toBe(false);
    expect(() => saveSidebarPreference(true)).not.toThrow();
  });

  it("persiste recolhido e volta ao expandido usando o armazenamento", () => {
    const store: Store = {};
    (globalThis as { window?: unknown }).window = fakeWindow(store);
    expect(readSidebarPreference()).toBe(false);
    saveSidebarPreference(true);
    expect(readSidebarPreference()).toBe(true);
    saveSidebarPreference(false);
    expect(readSidebarPreference()).toBe(false);
  });

  it("armazenamento indisponível é ignorado", () => {
    (globalThis as { window?: unknown }).window = { localStorage: null };
    expect(readSidebarPreference()).toBe(false);
    expect(() => saveSidebarPreference(true)).not.toThrow();
  });
});
```

- [ ] **Step 2: Rodar o teste e confirmar a falha**

Em `frontend/`, rode:

```
npx vitest run src/sidebarPreference.test.ts
```

Esperado: FAIL — "Failed to resolve import ./sidebarPreference".

- [ ] **Step 3: Implementar `sidebarPreference.ts`**

Crie `frontend/src/sidebarPreference.ts`:

```ts
const KEY = "workbyte-sidebar-collapsed";

function storage(): Pick<Storage, "getItem" | "setItem" | "removeItem"> | null {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readSidebarPreference(): boolean {
  return storage()?.getItem(KEY) === "1";
}

export function saveSidebarPreference(collapsed: boolean) {
  const store = storage();
  if (!store) return;
  if (collapsed) store.setItem(KEY, "1");
  else store.removeItem(KEY);
}
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

```
npx vitest run src/sidebarPreference.test.ts
```

Esperado: PASS (3 testes).

- [ ] **Step 5: Escrever o teste do Sidebar (falha primeiro)**

Crie `frontend/src/sidebar.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Bell, LayoutDashboard, Server } from "lucide-react";
import Sidebar from "./Sidebar";
import type { Page } from "./types";

const navigation = [
  { id: "overview" as Page, label: "Visão geral", icon: LayoutDashboard },
  { id: "service" as Page, label: "Serviço HTTP", icon: Server },
  { id: "incidents" as Page, label: "Incidentes", icon: Bell },
];

const base = {
  navigation,
  page: "overview" as Page,
  activeIncidents: 2,
  onToggle: () => {},
  onCloseMobile: () => {},
};

describe("menu lateral", () => {
  it("expandido mostra rótulos, área ativa e contador de incidentes", () => {
    const html = renderToStaticMarkup(
      <Sidebar {...base} collapsed={false} mobileOpen={false} />,
    );
    expect(html).toContain("Visão geral");
    expect(html).toContain("OBSERVABILIDADE");
    expect(html).toContain('aria-current="page"');
    expect(html).toContain(">2</span>");
    expect(html).toContain('aria-expanded="true"');
  });

  it("recolhido preserva ícones, área ativa e nome acessível", () => {
    const html = renderToStaticMarkup(
      <Sidebar {...base} collapsed={true} mobileOpen={false} />,
    );
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain("OBSERVABILIDADE");
    expect(html).toContain('title="Serviço HTTP"');
    expect(html).toContain('aria-label="Incidentes"');
    expect(html).toContain(">2</span>");
  });
});
```

- [ ] **Step 6: Rodar o teste e confirmar a falha**

```
npx vitest run src/sidebar.test.tsx
```

Esperado: FAIL — "Failed to resolve import ./Sidebar".

- [ ] **Step 7: Implementar `Sidebar.tsx`**

Crie `frontend/src/Sidebar.tsx`:

```tsx
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
          aria-label={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
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
```

- [ ] **Step 8: Rodar o teste e confirmar que passa**

```
npx vitest run src/sidebar.test.tsx
```

Esperado: PASS (2 testes).

- [ ] **Step 9: Integrar em `App.tsx`**

Em `frontend/src/App.tsx`:

1. Adicione `Menu` aos imports de `lucide-react` e os novos imports abaixo do bloco de componentes:

```tsx
import Sidebar from "./Sidebar";
import {
  readSidebarPreference,
  saveSidebarPreference,
} from "./sidebarPreference";
```

2. Após a linha `const [now, setNow] = useState(() => Date.now() / 1000);` (linha ~141), adicione:

```tsx
const [collapsed, setCollapsed] = useState(readSidebarPreference);
const [mobileOpen, setMobileOpen] = useState(false);
```

3. Dentro do componente, antes do `return`, adicione:

```tsx
function toggleSidebar() {
  setCollapsed((previous) => {
    const value = !previous;
    saveSidebarPreference(value);
    return value;
  });
}
```

4. Substitua o `<div className="app-shell">` (linha ~369) por:

```tsx
<div
  className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${
    mobileOpen ? "sidebar-open" : ""
  }`}
>
  {mobileOpen && (
    <div
      className="sidebar-overlay"
      aria-hidden="true"
      onClick={() => setMobileOpen(false)}
    />
  )}
```

5. Substitua o bloco `<aside className="sidebar">…</aside>` inteiro (linhas ~370-425, do `<a href="#overview" className="brand"` até o `</aside>`) por:

```tsx
<Sidebar
  navigation={navigation}
  page={page}
  activeIncidents={activeIncidents}
  collapsed={collapsed}
  onToggle={toggleSidebar}
  mobileOpen={mobileOpen}
  onCloseMobile={() => setMobileOpen(false)}
/>
```

6. No `<header className="topbar">`, adicione o hamburger antes do `<div className="topbar-right">`:

```tsx
<button
  type="button"
  className="icon-button menu-button mobile-only"
  onClick={() => setMobileOpen(true)}
  aria-label="Abrir navegação"
>
  <Menu size={18} />
</button>
```

- [ ] **Step 10: Adicionar CSS de colapso e drawer em `styles.css`**

1. Logo após a regra `.sidebar` existente (linha ~118), adicione:

```css
.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.sidebar-head .brand {
  padding: 0;
}
.sidebar-toggle {
  color: var(--muted);
}
.sidebar-toggle:hover {
  color: var(--accent);
}
.sidebar-close {
  color: var(--muted);
  display: none;
}
.app-shell.sidebar-collapsed .sidebar {
  width: 64px;
  padding-inline: 9px;
}
.app-shell.sidebar-collapsed .main-shell {
  width: calc(100% - 64px);
  margin-left: 64px;
}
.app-shell.sidebar-collapsed .sidebar .brand {
  justify-content: center;
  padding-bottom: 30px;
}
.app-shell.sidebar-collapsed .nav-item {
  justify-content: center;
  padding-inline: 0;
}
.app-shell.sidebar-collapsed .sidebar-head {
  flex-direction: column;
  padding-bottom: 30px;
}
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 4, 12, 0.66);
  z-index: 9;
}
.menu-button {
  display: none;
}
```

2. Em `@media (max-width: 850px)` (a partir da linha ~1166), substitua o grupo de regras da sidebar (`.sidebar { width: 74px … }`, `.brand { … }`, `.brand > span:last-child, .workspace, … { display: none; }`, `.nav-item { … }`, `.sidebar nav { width: 45px; }`, `.main-shell { width: calc(100% - 74px); margin-left: 74px; }`) por:

```css
.sidebar {
  width: min(280px, 84vw);
  padding: 22px 14px 0;
  transform: translateX(-102%);
  transition: transform 0.2s ease;
  align-items: stretch;
}
.app-shell.sidebar-open .sidebar {
  transform: translateX(0);
}
.menu-button,
.sidebar-close {
  display: inline-flex;
}
.sidebar-toggle {
  display: none;
}
.main-shell {
  width: 100%;
  margin-left: 0;
}
```

Mantenha as demais regras do bloco 850px (topbar, métricas, grids) como estão.

3. Em `@media (max-width: 580px)` (a partir da linha ~1241), remova/reponha as regras da sidebar e do main-shell (`.sidebar { position: sticky … width: 56px … }`, `.brand-mark { width: 32px … }`, `.brand { padding-bottom: 18px; }`, `.nav-item { width: 40px … }`, `.sidebar nav { width: 40px; }`, `.main-shell { margin-left: 0; width: calc(100% - 56px); }`) por:

```css
.main-shell {
  width: 100%;
  margin-left: 0;
}
```

No drawer, os rótulos permanecem visíveis; não há mais versão de 56px.

- [ ] **Step 11: Rodar todos os testes e o build**

Em `frontend/`, rode:

```
npm test
npm run build
```

Esperado: todos os testes passam (incluindo `sidebarPreference` e `sidebar`); build sem erros.

- [ ] **Step 12: Commit**

```
git add frontend/src/Sidebar.tsx frontend/src/sidebarPreference.ts frontend/src/sidebar.test.tsx frontend/src/sidebarPreference.test.ts frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat(dashboard): menu lateral retrátil com persistência e drawer móvel"
```

---

### Task 3: Landing pública e fluxo de entrada no Auth

**Files:**
- Create: `frontend/src/Landing.tsx`
- Test: `frontend/src/landing.test.tsx`
- Modify: `frontend/src/Auth.tsx` (estado `view`, render condicional)
- Modify: `frontend/src/styles.css` (estilos da landing)

**Interfaces:**
- Consumes: variáveis e fonte `--pixel` da Task 1; `Auth.tsx` existente (sessão, login, logout).
- Produces: `Landing({ onEnter: () => void })` (default export) — renderiza a landing pública; não consome APIs.

- [ ] **Step 1: Escrever o teste da landing (falha primeiro)**

Crie `frontend/src/landing.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Landing from "./Landing";

describe("landing pública", () => {
  it("apresenta a plataforma e o acesso ao painel sem dados operacionais", () => {
    const html = renderToStaticMarkup(<Landing onEnter={() => {}} />);
    expect(html).toContain("WORK");
    expect(html).toContain("Um ponto de observação.");
    expect(html).toContain("Acessar o painel");
    expect(html).not.toContain("Incidentes");
    expect(html).not.toContain('aria-current="page"');
  });
});
```

- [ ] **Step 2: Rodar o teste e confirmar a falha**

```
npx vitest run src/landing.test.tsx
```

Esperado: FAIL — "Failed to resolve import ./Landing".

- [ ] **Step 3: Implementar `Landing.tsx`**

Crie `frontend/src/Landing.tsx`:

```tsx
import { ArrowRight, Globe2, Mail, Server, ShieldCheck } from "lucide-react";

const pillars = [
  { icon: Server, title: "HTTP", text: "Disponibilidade e tráfego do serviço." },
  { icon: Globe2, title: "DNS", text: "Resolução de nomes do laboratório." },
  { icon: Mail, title: "SMTP", text: "Fila e entrega do correio local." },
  { icon: ShieldCheck, title: "Segurança", text: "Alertas, integridade e acesso." },
];

export default function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <main className="landing-shell">
      <header className="landing-top">
        <span className="landing-brand">
          WORK<span>BYTE</span>
        </span>
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
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

```
npx vitest run src/landing.test.tsx
```

Esperado: PASS (1 teste).

- [ ] **Step 5: Integrar a landing em `Auth.tsx`**

Em `frontend/src/Auth.tsx`:

1. Após `import App from "./App";`, adicione:

```tsx
import Landing from "./Landing";
```

2. Após `const [busy, setBusy] = useState(false);`, adicione:

```tsx
const [view, setView] = useState<"landing" | "login">("landing");
```

3. Substitua a linha `return (` que abre o JSX do login (imediatamente após o bloco `if (session) return <App … />;`) por:

```tsx
if (view === "landing") return <Landing onEnter={() => setView("login")} />;
return (
```

O restante do JSX do login permanece intacto. Enquanto `checking` é `true`, a landing é exibida; ao concluir a verificação, sessão válida abre o `App` diretamente e sem sessão permanece na landing até o CTA. Após `logout()`, a sessão fica `null` e a `view` permanece `"login"` (o usuário saiu de dentro do dashboard), então volta ao formulário de login.

- [ ] **Step 6: Adicionar o CSS da landing em `styles.css`**

Adicione ao final de `frontend/src/styles.css`:

```css
.landing-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 26px clamp(18px, 6vw, 64px) 40px;
  background:
    radial-gradient(ellipse 60% 40% at 70% -10%, rgba(139, 92, 246, 0.18), transparent 60%),
    radial-gradient(ellipse 50% 35% at 10% 110%, rgba(0, 229, 255, 0.12), transparent 60%),
    var(--bg);
}
.landing-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: clamp(48px, 10vh, 110px);
}
.landing-brand {
  font-family: var(--pixel);
  font-size: 15px;
  letter-spacing: 1px;
  color: var(--text);
  text-shadow: 2px 2px 0 #0284c7, 4px 4px 0 #0369a1, 6px 6px 0 #000;
}
.landing-brand > span {
  color: var(--accent);
}
.landing-hero {
  max-width: 640px;
}
.landing-hero h1 {
  font-size: clamp(30px, 5vw, 46px);
  line-height: 1.25;
  letter-spacing: -0.5px;
  margin: 14px 0 18px;
}
.landing-glow {
  color: var(--accent);
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.8), 0 0 24px rgba(0, 229, 255, 0.35);
}
.landing-hero > p {
  color: var(--muted);
  max-width: 460px;
  line-height: 1.7;
  margin-bottom: 26px;
}
.landing-cta {
  font-size: 15px;
  padding: 14px 22px;
}
.landing-pillars {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: clamp(40px, 8vh, 80px);
}
.landing-pillar {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 10px;
  padding: 16px 14px;
}
.landing-pillar svg {
  color: var(--accent);
}
.landing-pillar h2 {
  font-size: 13px;
  margin: 10px 0 6px;
  color: var(--text);
}
.landing-pillar p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}
.landing-foot {
  margin-top: auto;
  padding-top: 40px;
  color: var(--muted);
  font-size: 11px;
}
@media (max-width: 850px) {
  .landing-pillars {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 580px) {
  .landing-pillars {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 7: Rodar todos os testes e o build**

Em `frontend/`, rode:

```
npm test
npm run build
```

Esperado: todos os testes passam; build sem erros.

- [ ] **Step 8: Commit**

```
git add frontend/src/Landing.tsx frontend/src/landing.test.tsx frontend/src/Auth.tsx frontend/src/styles.css
git commit -m "feat(dashboard): landing pública Workbyte antes do login"
```

---

### Task 4: Varredura de tema — cores restantes do tema claro

**Files:**
- Modify: `frontend/src/styles.css` (todas as ocorrências restantes de `oklch(...)` e hex herdados do tema claro)

**Interfaces:**
- Consumes: paleta definida na Task 1.
- Produces: folha de estilo 100% no tema escuro — verificação determinística: zero ocorrências de `oklch(` no arquivo.

**Contexto:** após a Task 1, ~90 valores `oklch()` do tema claro permanecem espalhados pelo arquivo (sidebar, cards, tabelas, badges, login, gráficos). Esta tarefa aplica a tabela de mapeamento abaixo por substituição literal. Categorias: cinzas claros (hue 285, L≥94%) → superfícies escuras; cinzas de texto (L 25-39%) → texto claro; cinzas médios (L 54-79%) → texto secundário; violetas saturados (295) → ciano; lavandas claras (295, L≥89%) → tint translúcido de violeta; verdes → verde neon; vermelhos → vermelho neon; âmbar → âmbar; tint claro de qualquer cor → rgba translúcido da cor neon correspondente.

- [ ] **Step 1: Aplicar o script de substituição**

Rode no PowerShell a partir da raiz do repositório:

```powershell
$css = 'frontend/src/styles.css'
$map = [ordered]@{
  # Cinzas de texto (era texto escuro → vira texto claro)
  'oklch(28% 0.021 285)' = '#e8e6f0'
  'oklch(25% 0.018 285)' = '#e8e6f0'
  'oklch(30% 0.02 285)'  = '#c9cfe4'
  'oklch(32% 0.02 285)'  = '#c9cfe4'
  'oklch(34% 0.022 285)' = '#c9cfe4'
  'oklch(34% 0.02 285)'  = '#c9cfe4'
  'oklch(36% 0.018 285)' = '#c9cfe4'
  'oklch(36% 0.019 285)' = '#c9cfe4'
  'oklch(38% 0.018 285)' = '#c9cfe4'
  'oklch(39% 0.02 285)'  = '#c9cfe4'
  # Cinzas médios (secundário)
  'oklch(54% 0.019 285)' = '#9aa3c0'
  'oklch(64% 0.01 285)'  = '#9aa3c0'
  'oklch(64% 0.016 285)' = '#9aa3c0'
  'oklch(64% 0.018 285)' = '#9aa3c0'
  'oklch(65% 0.018 285)' = '#9aa3c0'
  'oklch(66% 0.014 285)' = '#9aa3c0'
  'oklch(67% 0.012 285)' = '#9aa3c0'
  'oklch(67% 0.018 285)' = '#9aa3c0'
  'oklch(69% 0.02 285)'  = '#c9cfe4'
  'oklch(72% 0.012 285)' = '#c9cfe4'
  'oklch(79% 0.012 285)' = '#6b7290'
  # Bordas e superfícies cinza-claras → escuras
  'oklch(86% 0.015 285)'  = '#2a3050'
  'oklch(91.7% 0.008 285)' = '#1b1f3a'
  'oklch(94% 0.006 285)'  = '#141830'
  'oklch(94% 0.009 285)'  = '#141830'
  'oklch(94% 0.012 285)'  = '#141830'
  'oklch(96% 0.008 285)'  = '#0d1020'
  'oklch(96% 0.009 285)'  = '#0d1020'
  'oklch(96% 0.018 285)'  = '#0d1020'
  'oklch(96% 0.004 285)'  = '#0d1020'
  'oklch(97.2% 0.004 285)' = '#05060f'
  'oklch(98% 0.004 285)'  = '#0a0b14'
  'oklch(98% 0.005 285)'  = '#0a0b14'
  'oklch(99.5% 0.002 285)' = '#0a0b14'
  # Violetas saturados → ciano
  'oklch(35% 0.035 295)' = '#b39cff'
  'oklch(36% 0.06 295)'  = '#b39cff'
  'oklch(45% 0.17 295)'  = '#00e5ff'
  'oklch(51% 0.18 295)'  = '#00e5ff'
  'oklch(59% 0.19 295)'  = '#00e5ff'
  'oklch(66% 0.15 295)'  = '#00e5ff'
  'oklch(80% 0.07 295)'  = '#8b5cf6'
  'oklch(79% 0.11 295)'  = '#8b5cf6'
  # Lavandas claras → tints de violeta
  'oklch(89% 0.033 295)' = 'rgba(139, 92, 246, 0.16)'
  'oklch(91% 0.042 295)' = 'rgba(139, 92, 246, 0.2)'
  'oklch(91% 0.055 295)' = 'rgba(139, 92, 246, 0.2)'
  'oklch(91% 0.03 295)'  = 'rgba(139, 92, 246, 0.14)'
  'oklch(93% 0.02 295)'  = 'rgba(139, 92, 246, 0.12)'
  'oklch(94% 0.025 295)' = 'rgba(139, 92, 246, 0.12)'
  'oklch(94% 0.03 295)'  = 'rgba(139, 92, 246, 0.12)'
  'oklch(95% 0.015 295)' = 'rgba(139, 92, 246, 0.1)'
  'oklch(95% 0.02 295)'  = 'rgba(139, 92, 246, 0.1)'
  'oklch(95% 0.023 295)' = 'rgba(139, 92, 246, 0.1)'
  'oklch(98% 0.005 295)' = 'rgba(139, 92, 246, 0.08)'
  # Vermelhos
  'oklch(48% 0.16 25)'   = '#ff5470'
  'oklch(47% 0.12 25)'   = '#ff5470'
  'oklch(87% 0.04 25)'   = 'rgba(255, 84, 112, 0.16)'
  'oklch(88% 0.04 25)'   = 'rgba(255, 84, 112, 0.16)'
  'oklch(95% 0.025 25)'  = 'rgba(255, 84, 112, 0.12)'
  'oklch(96% 0.018 25)'  = 'rgba(255, 84, 112, 0.12)'
  'oklch(96% 0.02 25)'   = 'rgba(255, 84, 112, 0.12)'
  'oklch(97% 0.015 25)'  = 'rgba(255, 84, 112, 0.1)'
  # Verdes
  'oklch(43% 0.09 164)'  = '#00e5a8'
  'oklch(52% 0.11 164)'  = '#00e5a8'
  'oklch(58% 0.09 164)'  = '#00e5a8'
  'oklch(59% 0.06 165)'  = '#00c9a0'
  'oklch(73% 0.12 165)'  = '#7ff0d0'
  'oklch(88% 0.034 165)' = 'rgba(0, 229, 168, 0.16)'
  'oklch(89% 0.025 164)' = 'rgba(0, 229, 168, 0.14)'
  'oklch(95% 0.025 164)' = 'rgba(0, 229, 168, 0.12)'
  'oklch(95% 0.025 165)' = 'rgba(0, 229, 168, 0.12)'
  'oklch(96% 0.018 165)' = 'rgba(0, 229, 168, 0.12)'
  'oklch(97.4% 0.012 165)' = 'rgba(0, 229, 168, 0.1)'
  # Âmbar
  'oklch(45% 0.1 75)'    = '#ffb400'
  'oklch(88% 0.06 80)'   = '#ffb400'
  'oklch(95% 0.05 80)'   = 'rgba(255, 180, 0, 0.16)'
  'oklch(97% 0.025 80)'  = 'rgba(255, 180, 0, 0.12)'
  'oklch(95% 0.03 80)'   = 'rgba(255, 180, 0, 0.12)'
  # Hex herdados
  '#328c94' = '#00e5a8'
  '#24232d' = '#101326'
  '#f5f4fa' = '#0a0b14'
  '#b5a3ec' = '#8b5cf6'
  '#bbb8c9' = '#9aa3c0'
  '#504b62' = '#6b7290'
  '#d8d1ed' = '#c9cfe4'
  '#aaa5bc' = '#9aa3c0'
  '#ece6fa' = 'rgba(139, 92, 246, 0.12)'
  '#454050' = '#2a3050'
}
$content = Get-Content $css -Raw
foreach ($key in $map.Keys) { $content = $content.Replace($key, $map[$key]) }
Set-Content -Path $css -Value $content -NoNewline -Encoding utf8
```

- [ ] **Step 2: Verificar que nenhuma cor antiga sobrou**

```powershell
(Select-String -Path frontend/src/styles.css -Pattern 'oklch\(' | Measure-Object).Count
```

Esperado: `0`.

- [ ] **Step 3: Ajustes pontuais de contraste pós-sweep (esperados)**

As substituições acima devem deixar o tema coerente; confira e corrija, se necessário, estes pontos — cada um com a correção exata quando aplicável:

1. `box-shadow` claros herdados (ex.: `rgba(...,0.1)` cinza em cards/topbar) ficam invisíveis em fundo escuro — substitua por `box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.06), 0 12px 32px rgba(0, 0, 0, 0.5)` nos cartões que usavam sombra clara.
2. Texto sobre badges sólidos (`color` branco/escuro dentro de `.status-badge`/`.pill`) deve permanecer legível: se um badge com fundo `#00e5a8`/`#ff5470`/`#ffb400` tiver `color` que era escuro (`#e8e6f0` após o sweep), troque para `#05060f` naquele seletor para contraste.
3. O `outline` de foco global (`outline: 3px solid ...`) já vira `#00e5ff` pelo mapeamento — confirme.

Não introduza novas cores fora da paleta Workbyte.

- [ ] **Step 4: Rodar testes e build**

Em `frontend/`, rode:

```
npm test
npm run build
```

Esperado: testes passam; build sem erros.

- [ ] **Step 5: Commit**

```
git add frontend/src/styles.css
git commit -m "feat(dashboard): varredura de tema escuro Workbyte em todas as seções"
```

---

### Task 5: Verificação final — build, testes, deploy e walkthrough

**Files:**
- Modify: `README.md` (uma linha de acesso, se necessário)
- Nenhum código novo — tarefa de verificação.

**Interfaces:**
- Consumes: tudo construído nas Tasks 1-4.
- Produces: evidência dos critérios de aceitação da especificação.

- [ ] **Step 1: Suíte completa do frontend**

Em `frontend/`, rode:

```
npm test
npm run build
```

Esperado: todos os testes passam (5 arquivos de teste: `resourceState`, `incidents`, `sidebarPreference`, `sidebar`, `landing`); build conclui.

- [ ] **Step 2: Suíte do backend (regressão)**

Na raiz, rode:

```
.venv\Scripts\python.exe -m pytest backend/tests -q
```

Esperado: `213 passed, 1 skipped` (nenhum teste de backend deve quebrar — nada de backend mudou).

- [ ] **Step 3: Deploy do frontend no serviço `api`**

```
docker compose up -d --build --no-deps api
```

Esperado: imagem `aularedes-platform:local` reconstruída com o `frontend/dist` novo; container `api` recriado e saudável.

- [ ] **Step 4: Smoke HTTP do fluxo público**

```powershell
$html = (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ -TimeoutSec 10).Content
$html.Contains('WORKBYTE') -or $html.Contains('WORK')
$resp = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/auth/session -TimeoutSec 10
$resp.StatusCode
```

Esperado: HTML do bundle novo servido (contém o título da landing ou referência a `assets/index-*.js`); `/api/auth/session` responde `401` (sem sessão) — status esperado para visitante público.

- [ ] **Step 5: Walkthrough dos critérios de aceitação**

Verifique manualmente em `http://localhost:8000` (com credenciais `ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env`) e registre o resultado de cada item:

1. `:8000` abre a landing Workbyte com CTA "Acessar o painel". ✔ esperado
2. O CTA abre o formulário de login da plataforma (`/api/auth/login`), não o login da demo. ✔ esperado
3. Login com credenciais válidas abre o dashboard; recarregar a página com sessão ativa abre o dashboard direto (sem passar pela landing). ✔ esperado
4. Logout encerra e volta ao login; expiração de sessão mostra a mensagem e volta ao login. ✔ esperado
5. As nove áreas estão presentes no menu: Visão geral, Serviço HTTP, PostgreSQL, DNS, SMTP, Recursos, Segurança, Incidentes, Laboratório — com dados reais carregando (APIs `/api/*`).
6. O botão do menu recolhe/expande; no recolhido, `title`/`aria-label` mostram os nomes; após recarregar a página, a preferência persiste; navegação por teclado (Tab) alcança todos os itens com foco visível.
7. Em janela ≤850px, a navegação vira drawer (hamburger abre, X e overlay fecham); tabelas/gráficos sem overflow horizontal da página.
8. Nenhum valor de demonstração: os números do dashboard batem com as APIs `/api/overview`, `/api/incidents` etc.
9. `:8011` continua servindo a demo independentemente (landing → login → painel do serviço HTTP).

- [ ] **Step 6: Atualizar README (seção de acesso)**

Em `README.md`, localize a linha que descreve o dashboard em `http://localhost:8000` e garanta que o texto mencione o fluxo. Substitua a linha existente (procure por `localhost:8000` na seção de URLs/uso) por:

```
- Dashboard Workbyte (landing pública → login → painel): http://localhost:8000
```

- [ ] **Step 7: Commit final**

```
git add README.md
git commit -m "docs: acesso ao dashboard principal com landing Workbyte"
```

---

## Critérios de pronto (checklist final)

- [ ] Landing pública em `:8000` com CTA para o login da plataforma.
- [ ] Login/sessão/CSRF/logout inalterados e funcionando.
- [ ] Dashboard com as nove áreas e dados reais.
- [ ] Menu lateral retrátil com persistência, `aria-expanded`, tooltips, drawer ≤850px.
- [ ] Zero `oklch(` em `frontend/src/styles.css` (tema 100% Workbyte).
- [ ] `npm test` e `npm run build` passam; backend `213 passed, 1 skipped`.
- [ ] Demo `:8011` intocada e funcionando.
