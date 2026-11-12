# Frontend do web-demo (WORKBYTE) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao web-demo (porta 8001) um frontend React 8-bit futurista (landing → login → painel) servido pelo próprio FastAPI, preservando byte a byte os contratos `/health`, `/work`, `/metrics`, `GET/POST /mode`.

**Architecture:** Pasta nova `demo-frontend/` (React 19 + Vite + TS + Tailwind v4 + shadcn), buildada no Dockerfile (estágio node) e copiada para `demo/static/`, servida por `demo/main.py` (mount `/assets` + fallback SPA). Login real via `POST /login` novo no demo, reutilizando `ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env`, com cookie de sessão assinado (HMAC-SHA256 com `LAB_TOKEN`).

**Tech Stack:** React 19, Vite 7, TypeScript, Tailwind CSS v4, shadcn CLI + registries do shoogle (MCP), vitest, FastAPI + TestClient, Docker multi-stage.

**Spec:** `docs/superpowers/specs/2026-11-12-demo-frontend-design.md`

## Global Constraints

- Contratos existentes NÃO mudam: `GET /health`, `GET /work`, `GET /metrics`, `GET /mode`, `POST /mode` — middleware de instrumentação (só `/work` e `/health`) intocado.
- Suíte backend atual (200 passed, 1 skipped) precisa continuar verde.
- Testes backend: `.venv\Scripts\python.exe -m pytest` (NUNCA o python do sistema).
- Testes frontend: `npm run test` (vitest) dentro de `demo-frontend/`.
- PowerShell 5.1 corrompe Python inline com f-strings/aspas → validar endpoints via scripts em `tmp/*.py` rodando `.venv\Scripts\python.exe tmp\script.py`.
- Nunca métrica sintética ou valor falsificado: contadores ausentes → "AGUARDANDO DADOS".
- Visual: fundo `#05060f`/`#0a0b14`; neon magenta `#ff2fd6`, ciano `#00e5ff`, violeta `#8b5cf6`, âmbar `#ffb400`; `Press Start 2P` para títulos, `IBM Plex Mono` para corpo; scanlines CRT; diálogos RPG (borda dupla branca).
- Produto fictício chama **WORKBYTE** (processamento de tarefas em tempo real).
- Docker: rebuild com `docker compose up -d --build --wait` ao final.

---

### Task 1: Scaffold do `demo-frontend` com tema CRT synthwave

**Files:**
- Create: `demo-frontend/package.json`
- Create: `demo-frontend/vite.config.ts`
- Create: `demo-frontend/tsconfig.json`
- Create: `demo-frontend/index.html`
- Create: `demo-frontend/src/main.tsx`
- Create: `demo-frontend/src/App.tsx` (shell mínimo; páginas vêm nas Tasks 6–8)
- Create: `demo-frontend/src/styles.css`

**Interfaces:**
- Consumes: nada (primeira task).
- Produces: projeto Vite que builda (`npm run build`) e testa (`npm run test`); `styles.css` exporta os tokens (`--color-*`, `--font-*`) e utilitários CSS (`crt-scanlines`, `crt-flicker`, `glow-magenta`, `glow-cyan`, `dialog-rpg`, `synth-grid`, `marquee-track`) usados por TODAS as páginas seguintes.

- [ ] **Step 1: Criar `demo-frontend/package.json`**

```json
{
  "name": "aularedes-demo-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@fontsource/ibm-plex-mono": "^5.0.0",
    "@fontsource/press-start-2p": "^5.0.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.468.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "tailwind-merge": "^3.0.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@types/node": "^24.0.0",
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "@vitejs/plugin-react": "^5.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "~5.9.3",
    "vite": "^7.1.0",
    "vitest": "^3.2.0"
  }
}
```

- [ ] **Step 2: Criar `demo-frontend/vite.config.ts`** (proxy dos endpoints do demo para :8001, alias `@`, Tailwind v4)

```typescript
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const demoApi = "http://127.0.0.1:8001";
const demoProxy = Object.fromEntries(
  ["/health", "/work", "/metrics", "/mode", "/login", "/logout"].map((p) => [p, demoApi]),
);

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: { proxy: demoProxy },
});
```

- [ ] **Step 3: Criar `demo-frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src", "vite.config.ts"]
}
```

- [ ] **Step 4: Criar `demo-frontend/index.html`**

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>WORKBYTE — processamento em tempo real</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Criar `demo-frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 6: Criar `demo-frontend/src/App.tsx`** (shell mínimo — rotas reais chegam nas Tasks 6–8; aqui só precisa buildar)

```tsx
export default function App() {
  return (
    <div className="crt-scanlines min-h-screen bg-bg font-mono text-parchment">
      <span className="font-pixel text-cyan glow-cyan">WORKBYTE</span>
    </div>
  );
}
```

- [ ] **Step 7: Criar `demo-frontend/src/styles.css`** (tokens do tema + efeitos CRT — todo o visual vem daqui)

```css
@import "tailwindcss";
@import "@fontsource/press-start-2p";
@import "@fontsource/ibm-plex-mono/400.css";
@import "@fontsource/ibm-plex-mono/700.css";

@theme {
  --color-bg: #05060f;
  --color-panel: #0a0b14;
  --color-panel-edge: #1b1f3a;
  --color-magenta: #ff2fd6;
  --color-cyan: #00e5ff;
  --color-violet: #8b5cf6;
  --color-amber: #ffb400;
  --color-parchment: #e8e6f0;
  --font-pixel: "Press Start 2P", "IBM Plex Mono", monospace;
  --font-mono: "IBM Plex Mono", monospace;
}

html,
body {
  background: var(--color-bg);
}

body {
  color: var(--color-parchment);
  font-family: var(--font-mono);
}

.crt-scanlines {
  position: relative;
}

.crt-scanlines::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 50;
  pointer-events: none;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0 2px,
    rgba(2, 3, 10, 0.35) 2px 4px
  );
}

.crt-flicker {
  animation: crt-flicker 6s infinite steps(1);
}

@keyframes crt-flicker {
  0%, 91%, 94%, 96%, 100% { opacity: 1; }
  93% { opacity: 0.86; }
  97% { opacity: 0.92; }
}

.glow-magenta {
  text-shadow: 0 0 6px rgba(255, 47, 214, 0.8), 0 0 24px rgba(255, 47, 214, 0.4);
}

.glow-cyan {
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.8), 0 0 24px rgba(0, 229, 255, 0.35);
}

.dialog-rpg {
  border: 4px double #ffffff;
  background: rgba(5, 6, 15, 0.94);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.8), 0 0 18px rgba(139, 92, 246, 0.35);
}

.synth-grid {
  background-image:
    linear-gradient(rgba(139, 92, 246, 0.22) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139, 92, 246, 0.22) 1px, transparent 1px);
  background-size: 40px 40px;
}

.marquee-track {
  animation: marquee 18s linear infinite;
}

@keyframes marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
```

- [ ] **Step 8: Instalar e buildar**

```bash
cd demo-frontend
npm install --no-audit --no-fund
npm run build
```

Expected: `tsc -b` sem erros, `vite build` gera `demo-frontend/dist/`. `node_modules/` e `dist/` já estão no `.gitignore` global.

- [ ] **Step 9: Commit**

```bash
git add demo-frontend/package.json demo-frontend/package-lock.json demo-frontend/vite.config.ts demo-frontend/tsconfig.json demo-frontend/index.html demo-frontend/src
git commit -m "feat(demo-frontend): scaffold vite+react com tema CRT synthwave"
```

---

### Task 2: Sessão assinada no backend — `demo/session.py` (TDD)

**Files:**
- Create: `demo/session.py`
- Test: `backend/tests/test_demo_session.py`

**Interfaces:**
- Consumes: nada.
- Produces: `make_session(username: str, secret: str, ttl_seconds: int = 43200) -> str` (retorna `"<body_b64url>.<hmac_hex>"`) e `read_session(token: str, secret: str) -> str | None` (retorna o username ou `None` se assinatura/expiração/formato inválidos). A Task 3 usa exatamente essas duas funções.

- [ ] **Step 1: Escrever os testes que falham**

```python
from demo.session import make_session, read_session


def test_session_roundtrip():
    token = make_session("admin", "demo-secret")
    assert read_session(token, "demo-secret") == "admin"


def test_session_rejects_bad_signature():
    token = make_session("admin", "demo-secret")
    assert read_session(token + "x", "demo-secret") is None
    assert read_session(token, "outra-chave") is None


def test_session_rejects_expired():
    token = make_session("admin", "demo-secret", ttl_seconds=-1)
    assert read_session(token, "demo-secret") is None


def test_session_rejects_garbage():
    assert read_session("", "demo-secret") is None
    assert read_session("sem-ponto", "demo-secret") is None
    assert read_session("###.fedcba", "demo-secret") is None
```

- [ ] **Step 2: Rodar e confirmar falha**

```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_demo_session.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'demo.session'`

- [ ] **Step 3: Implementar `demo/session.py`**

```python
"""Cookie de sessão assinado (HMAC-SHA256) para o login do web-demo."""
import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

SESSION_COOKIE = "demo_session"
SESSION_TTL_SECONDS = 43200  # 12h


def make_session(username: str, secret: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    payload = {"u": username, "exp": int(time.time()) + ttl_seconds}
    body = urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def read_session(token: str, secret: str) -> str | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    padding = "=" * (-len(body) % 4)
    try:
        payload = json.loads(urlsafe_b64decode(body + padding))
    except ValueError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("exp"), (int, float)):
        return None
    if payload["exp"] < time.time():
        return None
    user = payload.get("u")
    return user if isinstance(user, str) else None
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_demo_session.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add demo/session.py backend/tests/test_demo_session.py
git commit -m "feat(demo): sessao assinada por HMAC para o login do web-demo"
```

---

### Task 3: Endpoints de login no `demo/main.py` + estáticos (TDD)

**Files:**
- Modify: `demo/main.py` (importações, assinatura de `create_demo`, endpoints novos, servimento de estáticos no fim de `create_demo`)
- Test: `backend/tests/test_demo_login.py`

**Interfaces:**
- Consumes: `make_session`/`read_session` da Task 2.
- Produces: `POST /login` (`{"username","password"}` → 200 `{"authenticated": true}` + cookie `demo_session`; 401 credencial errada; 503 se senha não configurada), `GET /login` → `{"authenticated": bool}`, `POST /logout` (limpa cookie). Counter `demo_auth_attempts_total{path="/login",result="failed"|"accepted"}`. `create_demo(token=None, runtime_config=None, admin_username=None, admin_password=None, static_path=None)` — defaults lidos de `ADMIN_USERNAME`/`ADMIN_PASSWORD` do ambiente. Estáticos: `GET /{full_path:path}` → `index.html` quando `demo/static/` existir (o Dockerfile da Task 9 o cria); rotas de API têm precedência por ordem de registro.

- [ ] **Step 1: Escrever os testes que falham**

```python
from fastapi.testclient import TestClient

from demo.session import make_session


def demo_client():
    from demo.main import create_demo
    return create_demo("demo-secret", admin_username="admin", admin_password="monitor-pass")


def test_login_accepts_authorized_credentials():
    with TestClient(demo_client()) as client:
        data = client.post("/login", json={"username": "admin", "password": "monitor-pass"})
        assert data.status_code == 200
        assert data.json() == {"authenticated": True}
        assert "demo_session" in data.cookies


def test_login_rejects_wrong_password_and_counts():
    with TestClient(demo_client()) as client:
        assert client.post("/login", json={"username": "admin", "password": "errada"}).status_code == 401
        metrics = client.get("/metrics").text
        assert 'demo_auth_attempts_total{path="/login",result="failed"} 1.0' in metrics


def test_login_status_and_logout_flow():
    with TestClient(demo_client()) as client:
        assert client.get("/login").json() == {"authenticated": False}
        client.post("/login", json={"username": "admin", "password": "monitor-pass"})
        assert client.get("/login").json() == {"authenticated": True}
        client.post("/logout")
        assert client.get("/login").json() == {"authenticated": False}


def test_tampered_session_cookie_is_rejected():
    with TestClient(demo_client()) as client:
        client.cookies.set("demo_session", "abc.def")
        assert client.get("/login").json() == {"authenticated": False}
        client.cookies.set("demo_session", make_session("admin", "outra-chave"))
        assert client.get("/login").json() == {"authenticated": False}


def test_login_without_configured_password_returns_503():
    from demo.main import create_demo

    with TestClient(create_demo("demo-secret", admin_username="admin", admin_password="")) as client:
        assert client.post("/login", json={"username": "admin", "password": "qualquer"}).status_code == 503


def test_existing_contracts_survive_login_endpoints():
    with TestClient(demo_client()) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/mode", json={"mode": "offline"}).status_code == 401
        assert client.post("/mode", headers={"X-Lab-Token": "demo-secret"}, json={"mode": "offline"}).status_code == 200
        assert client.get("/health").status_code == 503
        assert client.get("/work").status_code == 503
        assert client.get("/metrics").status_code == 200


def test_static_fallback_serves_index_html(tmp_path):
    from demo.main import create_demo

    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html><body>WORKBYTE</body></html>", encoding="utf-8")
    with TestClient(create_demo("demo-secret", static_path=static)) as client:
        page = client.get("/rota-qualquer-da-spa")
        assert page.status_code == 200
        assert "WORKBYTE" in page.text
        # contratos de API continuam acima do fallback
        assert client.get("/health").status_code == 200
```

- [ ] **Step 2: Rodar e confirmar falha**

```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_demo_login.py -v
```

Expected: FAIL — `TypeError: create_demo() got an unexpected keyword argument 'admin_username'`

- [ ] **Step 3: Modificar `demo/main.py`**

Substituir a assinatura e o topo de `create_demo` (linhas 18–22 atuais):

```python
import asyncio
import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from pydantic import BaseModel
from .config import load_http_config
from .session import SESSION_COOKIE, SESSION_TTL_SECONDS, make_session, read_session


class Mode(BaseModel):
    mode: Literal["normal", "slow", "offline"]


class LoginRequest(BaseModel):
    username: str
    password: str


def create_demo(token=None, runtime_config=None, admin_username=None, admin_password=None, static_path=None):
    app = FastAPI(title="HTTP de demonstração")
    app.state.mode = "normal"
    config = runtime_config or load_http_config()
    token = token if token is not None else os.getenv("LAB_TOKEN", "")
    username = admin_username if admin_username is not None else os.getenv("ADMIN_USERNAME", "admin")
    password = admin_password if admin_password is not None else os.getenv("ADMIN_PASSWORD", "")
    static_dir = static_path if static_path is not None else Path(__file__).resolve().parent / "static"
    registry = CollectorRegistry()
    # ... (Counter/Histogram/auth EXISTENTES sem mudança — copiar do arquivo atual)
```

Depois dos endpoints existentes (`/health`, `/work`, `/metrics`, `GET/POST /mode`), ADICIONAR antes do `return app`:

```python
    @app.post("/login")
    def login(body: LoginRequest, response: Response):
        if not password:
            raise HTTPException(503, "Login indisponível no serviço de demonstração")
        user_ok = hmac.compare_digest(body.username.encode(), username.encode())
        pass_ok = hmac.compare_digest(hashlib.sha256(body.password.encode()).hexdigest(), hashlib.sha256(password.encode()).hexdigest())
        if not (user_ok and pass_ok):
            auth.labels("/login", "failed").inc()
            raise HTTPException(401, "Credenciais inválidas")
        auth.labels("/login", "accepted").inc()
        response.set_cookie(SESSION_COOKIE, make_session(body.username, token), max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax")
        return {"authenticated": True}

    @app.get("/login")
    def login_status(request: Request):
        session = read_session(request.cookies.get(SESSION_COOKIE, ""), token)
        return {"authenticated": session is not None}

    @app.post("/logout")
    def logout(response: Response):
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"authenticated": False}
```

E no FIM de `create_demo`, logo antes do `return app`:

```python
    if static_dir.exists() and (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="demo-assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            return FileResponse(static_dir / "index.html")

    return app
```

Atenção: o middleware de instrumentação, `/health`, `/work`, `/metrics`, `GET/POST /mode` existentes NÃO são alterados — os endpoints novos entram depois deles, e o fallback SPA é o último route registrado.

- [ ] **Step 4: Rodar os testes novos e a suíte completa**

```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_demo_login.py -v
.venv\Scripts\python.exe -m pytest backend/tests -x -q
```

Expected: Task nova 7 passed; suíte completa ~208 passed, 1 skipped (as 200 antigas continuam verdes).

- [ ] **Step 5: Commit**

```bash
git add demo/main.py backend/tests/test_demo_login.py
git commit -m "feat(demo): POST/GET/DELETE /login com sessao assinada e fallback SPA"
```

---

### Task 4: Cliente de API + parser de métricas no frontend (TDD vitest)

**Files:**
- Create: `demo-frontend/src/api.ts`
- Create: `demo-frontend/src/metrics.ts`
- Test: `demo-frontend/src/api.test.ts`
- Test: `demo-frontend/src/metrics.test.ts`

**Interfaces:**
- Consumes: endpoints da Task 3.
- Produces: `api` (métodos `health(): Promise<boolean>` — false se caiu; `mode(): Promise<{mode: Mode}>`; `work(): Promise<WorkResult>`; `metrics(): Promise<string>`; `authenticated(): Promise<boolean>` — false se erro; `login(username, password): Promise<boolean>`; `logout(): Promise<void>`) e `navigate(path: string): void`; `parseDemoCounters(text: string): RequestCounters` com `{total: number, byStatus: Record<string, number>, work: number}`. Tasks 6–8 usam exatamente essas APIs.

- [ ] **Step 1: Escrever os testes que falham** — `demo-frontend/src/metrics.test.ts`

```typescript
import { describe, expect, it } from "vitest";
import { parseDemoCounters } from "./metrics";

const exposition = [
  "# HELP demo_http_requests_total Completed HTTP requests",
  "# TYPE demo_http_requests_total counter",
  'demo_http_requests_total{path="/work",status="200"} 12.0',
  'demo_http_requests_total{path="/work",status="503"} 3.0',
  'demo_http_requests_total{path="/mode",status="200"} 2.0',
  'demo_other_metric_total{path="/work",status="200"} 99.0',
].join("\n");

describe("parseDemoCounters", () => {
  it("sums totals and groups by status", () => {
    const data = parseDemoCounters(exposition);
    expect(data.total).toBe(17);
    expect(data.byStatus).toEqual({ "200": 14, "503": 3 });
  });

  it("counts work requests separately", () => {
    expect(parseDemoCounters(exposition).work).toBe(15);
  });

  it("returns zeros for exposition without demo counters", () => {
    const data = parseDemoCounters("# HELP demo_http_duration_seconds nothing\n");
    expect(data).toEqual({ total: 0, byStatus: {}, work: 0 });
  });
});
```

- [ ] **Step 2: Escrever os testes que falham** — `demo-frontend/src/api.test.ts`

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api", () => {
  it("health returns true when status is ok", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ status: "ok" }), { status: 200 })));
    expect(await api.health()).toBe(true);
  });

  it("health returns false when the service is offline", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 503 })));
    expect(await api.health()).toBe(false);
  });

  it("login posts credentials and reports success", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ authenticated: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await api.login("admin", "monitor-pass")).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("/login", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ username: "admin", password: "monitor-pass" }),
    }));
  });

  it("login reports failure on 401", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response('{"detail":"Credenciais inválidas"}', { status: 401 })));
    expect(await api.login("admin", "errada")).toBe(false);
  });

  it("authenticated falls back to false on network error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    expect(await api.authenticated()).toBe(false);
  });

  it("mode parses the current phase", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ mode: "slow" }), { status: 200 })));
    expect(await api.mode()).toEqual({ mode: "slow" });
  });
});
```

- [ ] **Step 3: Rodar e confirmar falha**

```bash
cd demo-frontend && npm run test
```

Expected: FAIL — arquivos `./api` e `./metrics` não existem.

- [ ] **Step 4: Implementar `demo-frontend/src/metrics.ts`**

```typescript
export interface RequestCounters {
  total: number;
  byStatus: Record<string, number>;
  work: number;
}

export function parseDemoCounters(text: string): RequestCounters {
  const byStatus: Record<string, number> = {};
  let total = 0;
  let work = 0;
  for (const line of text.split("\n")) {
    if (!line.startsWith("demo_http_requests_total{")) continue;
    const value = Number(line.slice(line.lastIndexOf("}") + 1).trim());
    if (!Number.isFinite(value)) continue;
    total += value;
    const path = /path="([^"]*)"/.exec(line)?.[1] ?? "";
    const status = /status="([^"]*)"/.exec(line)?.[1] ?? "";
    if (path === "/work") work += value;
    byStatus[status] = (byStatus[status] ?? 0) + value;
  }
  return { total, byStatus, work };
}
```

- [ ] **Step 5: Implementar `demo-frontend/src/api.ts`**

```typescript
export type Mode = "normal" | "slow" | "offline";

export interface WorkResult {
  message: string;
  timestamp: number;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  async health(): Promise<boolean> {
    try {
      const data = await requestJson<{ status: string }>("/health");
      return data.status === "ok";
    } catch {
      return false;
    }
  },
  mode(): Promise<{ mode: Mode }> {
    return requestJson<{ mode: Mode }>("/mode");
  },
  work(): Promise<WorkResult> {
    return requestJson<WorkResult>("/work");
  },
  async metrics(): Promise<string> {
    const response = await fetch("/metrics");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.text();
  },
  async authenticated(): Promise<boolean> {
    try {
      const data = await requestJson<{ authenticated: boolean }>("/login");
      return data.authenticated;
    } catch {
      return false;
    }
  },
  async login(username: string, password: string): Promise<boolean> {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return response.ok;
  },
  async logout(): Promise<void> {
    const response = await fetch("/logout", { method: "POST" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  },
};

export function navigate(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
```

- [ ] **Step 6: Rodar e confirmar que passa**

```bash
cd demo-frontend && npm run test
```

Expected: 9 passed (6 de api.test.ts + 3 de metrics.test.ts).

- [ ] **Step 7: Commit**

```bash
git add demo-frontend/src/api.ts demo-frontend/src/metrics.ts demo-frontend/src/api.test.ts demo-frontend/src/metrics.test.ts
git commit -m "feat(demo-frontend): cliente de api e parser de contadores com testes"
```

---

### Task 5: shadcn init + componentes base + componente do shoogle

**Files:**
- Create: `demo-frontend/components.json`
- Create: `demo-frontend/src/lib/utils.ts`
- Create: `demo-frontend/src/components/ui/*` (gerados pela CLI)
- Modify: `demo-frontend/tsconfig.json`, `demo-frontend/vite.config.ts` (já estão prontos da Task 1 — alias e paths já configurados)

**Interfaces:**
- Consumes: scaffold da Task 1.
- Produces: componentes `@/components/ui/button|input|label|card` (shadcn padrão, com `cn()` de `@/lib/utils`) e o componente do shoogle `feature-carousel` disponíveis para as páginas das Tasks 6–8.

- [ ] **Step 1: Criar `demo-frontend/components.json`** (evita o prompt interativo do init)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/styles.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 2: Criar `demo-frontend/src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 3: Adicionar componentes base shadcn**

```bash
cd demo-frontend
npx shadcn@latest add button input label card --yes
```

Expected: arquivos criados em `src/components/ui/`.

- [ ] **Step 4: Adicionar componente do shoogle** (busca feita no planejamento: `@cult-ui/feature-carousel` — "Feature carousel with smooth transitions"; registro em https://www.cult-ui.com)

```bash
npx shadcn@latest add @cult-ui/feature-carousel --yes
```

Expected: componente adicionado (a CLI resolve dependências do item, ex. embla-carousel). Se o registro estiver indisponível, usar o fallback do Step 5 e registrar isso no commit.

- [ ] **Step 5 (apenas se o Step 4 falhar): fallback — grid de features próprio** — Create `demo-frontend/src/components/FeatureGrid.tsx`

```tsx
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
        <div key={f.title} className="dialog-rbg border-2 border-panel-edge bg-panel p-6" data-dialog>
          <span className="font-pixel text-sm text-magenta glow-magenta">{f.icon}</span>
          <h3 className="mt-3 font-pixel text-xs text-cyan">{f.title}</h3>
          <p className="mt-2 text-sm opacity-75">{f.description}</p>
        </div>
      ))}
    </div>
  );
}
```

(Obs.: a classe correta é `dialog-rpg` em vez de `dialog-rbg`/`data-dialog` — usar `className="dialog-rpg border-2 border-panel-edge bg-panel p-6"`.)

- [ ] **Step 6: Buildar e commitar**

```bash
npm run build
git add demo-frontend/components.json demo-frontend/src
git commit -m "feat(demo-frontend): shadcn base e feature-carousel do shoogle"
```

---

### Task 6: Tela de login

**Files:**
- Create: `demo-frontend/src/pages/Login.tsx`
- Modify: `demo-frontend/src/App.tsx` (rotas por pathname)

**Interfaces:**
- Consumes: `api.login`, `navigate` (Task 4).
- Produces: página `/login` renderizada em `App.tsx`; sucesso → `window.location.assign("/painel")` (recarrega para o cookie valer); erro → diálogo RPG com mensagem.

- [ ] **Step 1: Criar `demo-frontend/src/pages/Login.tsx`**

```tsx
import { useState, type FormEvent } from "react";
import { api, navigate } from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const ok = await api.login(username, password);
    setBusy(false);
    if (ok) {
      window.location.assign("/painel");
      return;
    }
    setError("! Credenciais inválidas. Verifique usuário e senha.");
  }

  return (
    <main className="crt-scanlines flex min-h-screen items-center justify-center bg-bg px-4 font-mono text-parchment">
      <div className="crt-flicker dialog-rpg w-full max-w-md p-8">
        <h1 className="font-pixel text-base text-cyan glow-cyan">ACESSO RESTRITO</h1>
        <p className="mt-4 text-sm opacity-75">* Somente operadores autorizados do laboratório.</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-5">
          <label className="block">
            <span className="font-pixel text-[10px] text-magenta glow-magenta">OPERADOR</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="mt-2 w-full border-2 border-panel-edge bg-black/60 px-3 py-2 font-mono text-parchment outline-none focus:border-cyan"
            />
          </label>
          <label className="block">
            <span className="font-pixel text-[10px] text-magenta glow-magenta">SENHA</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="mt-2 w-full border-2 border-panel-edge bg-black/60 px-3 py-2 font-mono text-parchment outline-none focus:border-cyan"
            />
          </label>
          {error && (
            <div className="dialog-rpg px-4 py-3 text-sm text-magenta">{error}</div>
          )}
          <button
            type="submit"
            disabled={busy}
            className="font-pixel w-full border-2 border-cyan px-4 py-3 text-xs text-cyan transition-colors hover:bg-cyan/10 disabled:opacity-50"
          >
            {busy ? "VALIDANDO..." : "ENTRAR"}
          </button>
        </form>
        <button onClick={() => navigate("/")} className="mt-5 text-xs opacity-60 underline hover:opacity-100">
          voltar ao início
        </button>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Rotas em `demo-frontend/src/App.tsx`** (substituir o shell da Task 1)

```tsx
import { useEffect, useState } from "react";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Panel from "./pages/Panel";

const routes: Record<string, () => React.ReactElement> = {
  "/": Landing,
  "/login": Login,
  "/painel": Panel,
};

export default function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const Page = routes[path] ?? Landing;
  return <Page />;
}
```

Nota: `Landing` e `Panel` ainda não existem — criar nesta task arquivos provisórios `src/pages/Landing.tsx` e `src/pages/Panel.tsx` apenas com `export default function Nome() { return null; }` (substituídos nas Tasks 7 e 8), para o build passar.

- [ ] **Step 3: Buildar, testar e commitar**

```bash
cd demo-frontend && npm run build && npm run test
```

Expected: build limpo, 9 passed.

```bash
git add demo-frontend/src
git commit -m "feat(demo-frontend): tela de login estilo terminal CRT e roteamento por path"
```

---

### Task 7: Landing 8-bit futurista (WORKBYTE)

**Files:**
- Create: `demo-frontend/src/assets/hero.png` (gerada por IA nesta task)
- Modify: `demo-frontend/src/pages/Landing.tsx` (substitui o placeholder da Task 6)

**Interfaces:**
- Consumes: tokens/utilitários CSS (Task 1); `navigate` (Task 4); `FeatureGrid` ou `feature-carousel` (Task 5).
- Produces: página `/` completa. Nenhuma página depende dela.

- [ ] **Step 1: Gerar a arte do hero** (ferramenta de geração de imagem; guardar como `demo-frontend/src/assets/hero.png`)

Prompt: "Pixel art 8-bit scene, dark navy background (#05060f), a glowing magenta neon sun setting behind a retro computer server rack with glowing cyan windows, violet grid floor in perspective, few pixel stars, chunky limited palette magenta/cyan/violet/amber, no text, wide 16:9 composition" — editar/gerrar até ficar coerente com o tema; se preferir reusar a imagem 3 de referência (vaporwave) como base de estilo, passar as referências do usuário junto.

- [ ] **Step 2: Escrever `demo-frontend/src/pages/Landing.tsx`**

```tsx
import hero from "../assets/hero.png";
import { navigate } from "../api";

const marqueeItems = [
  "WORKBYTE",
  "SINAL DE VERDADE",
  "PROCESSAMENTO EM TEMPO REAL",
  "8-BIT // FUTURISTA",
  "PROMETHEUS INSIDE",
  "WORKBYTE",
  "SINAL DE VERDADE",
  "PROCESSAMENTO EM TEMPO REAL",
  "8-BIT // FUTURISTA",
  "PROMETHEUS INSIDE",
];

export default function Landing() {
  return (
    <main className="font-mono text-parchment">
      <section className="crt-scanlines synth-grid relative min-h-screen overflow-hidden">
        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
          <span className="font-pixel text-xs text-magenta glow-magenta">WORKBYTE</span>
          <button
            onClick={() => navigate("/login")}
            className="font-pixel border-2 border-cyan px-4 py-2 text-[10px] text-cyan transition-colors hover:bg-cyan/10"
          >
            ENTRAR
          </button>
        </header>
        <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-10 px-6 pt-10 pb-24 md:grid-cols-2">
          <div className="crt-flicker">
            <h1 className="font-pixel text-3xl leading-relaxed md:text-4xl">
              <span className="text-parchment">TRABALHO</span>{" "}
              <span className="text-cyan glow-cyan">REAL</span>
              <br />
              <span className="text-magenta glow-magenta">EM PIXELS</span>
            </h1>
            <p className="mt-6 max-w-md text-sm leading-relaxed opacity-75">
              * O processador de tarefas do laboratório: cada requisição medida,
              cada falha observada, cada alerta entregue. Sem routes falsas.
            </p>
            <button
              onClick={() => navigate("/login")}
              className="font-pixel mt-8 border-4 border-magenta bg-magenta/10 px-8 py-4 text-xs text-magenta glow-magenta transition-transform hover:translate-y-[-2px]"
            >
              ▶ ABRIR PAINEL
            </button>
          </div>
          <img src={hero} alt="Cena pixel art do WORKBYTE" className="w-full border-2 border-panel-edge shadow-[0_0_40px_rgba(139,92,246,0.25)]" />
        </div>
      </section>

      <section className="overflow-hidden border-y-2 border-panel-edge bg-panel py-3">
        <div className="marquee-track flex w-max gap-12 font-pixel text-[10px] text-violet">
          {marqueeItems.map((item, index) => (
            <span key={`${item}-${index}`}>{item} ✦</span>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="font-pixel text-sm text-cyan glow-cyan">SISTEMA EM CAMADAS</h2>
        <p className="mt-3 text-sm opacity-70">* Tudo que o WORKBYTE expõe, o Prometheus coleta.</p>
        <div className="mt-10">
          {/* usar <FeatureCarousel /> do shoogle (Task 5) ou <FeatureGrid /> no fallback */}
          <FeatureCarousel />
        </div>
      </section>

      <footer className="border-t-2 border-panel-edge bg-panel px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 text-center">
          <div className="flex gap-8 font-pixel text-[10px] text-parchment opacity-70">
            <span>♥</span><span>▶</span><span>◆</span><span>✉</span>
          </div>
          <p className="text-xs opacity-60">WORKBYTE — laboratório de redes · serviços medidos de verdade</p>
          <p className="text-[10px] opacity-40">/health · /work · /metrics · /mode</p>
        </div>
      </footer>
    </main>
  );
}
```

Ajustar o import do carousel conforme o caminho real criado pela CLI do shoogle (ex.: `import { FeatureCarousel } from "@/components/ui/feature-carousel";` — conferir o nome do export no arquivo gerado).

- [ ] **Step 3: Buildar, testar e commitar**

```bash
cd demo-frontend && npm run build && npm run test
```

```bash
git add demo-frontend/src
git commit -m "feat(demo-frontend): landing WORKBYTE 8-bit com hero, marquee e features"
```

---

### Task 8: Painel protegido (status ao vivo)

**Files:**
- Modify: `demo-frontend/src/pages/Panel.tsx` (substitui o placeholder da Task 6)

**Interfaces:**
- Consumes: `api` (health/mode/work/metrics/authenticated/logout), `parseDemoCounters` (Task 4); CSS do tema (Task 1).
- Produces: página `/painel` — checa sessão (redirect `/login` se inválida) e exibe 4 regiões: SINAL (`● ONLINE`/`✖ SIGNAL LOST`), MODO, CONTADORES, CONSOLE DE TRABALHO.

- [ ] **Step 1: Escrever `demo-frontend/src/pages/Panel.tsx`**

```tsx
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { parseDemoCounters, type RequestCounters } from "../metrics";

interface WorkLogEntry {
  at: string;
  latencyMs: number;
  message: string;
  failure?: string;
}

function StatCard({ label, value, tone, glitch }: { label: string; value: string; tone: "cyan" | "violet" | "amber" | "magenta"; glitch?: boolean }) {
  const toneClass = { cyan: "text-cyan glow-cyan", violet: "text-violet", amber: "text-amber", magenta: "text-magenta glow-magenta" }[tone];
  return (
    <div className="dialog-rpg p-6">
      <p className="font-pixel text-[10px] opacity-60">{label}</p>
      <p className={`font-pixel mt-4 text-sm ${toneClass} ${glitch ? "crt-flicker" : ""}`}>{value}</p>
    </div>
  );
}

export default function Panel() {
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [counters, setCounters] = useState<RequestCounters | null>(null);
  const [log, setLog] = useState<WorkLogEntry[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    api.authenticated().then((ok) => {
      if (!alive) return;
      if (!ok) {
        window.location.assign("/login");
        return;
      }
      setReady(true);
    });
    return () => { alive = false; };
  }, []);

  const refreshHealth = useCallback(async () => setOnline(await api.health()), []);
  const refreshMode = useCallback(async () => {
    try {
      setMode((await api.mode()).mode);
    } catch {
      setMode(null);
    }
  }, []);
  const refreshMetrics = useCallback(async () => {
    try {
      setCounters(parseDemoCounters(await api.metrics()));
    } catch {
      setCounters(null);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    void refreshHealth();
    void refreshMode();
    void refreshMetrics();
    const fast = window.setInterval(() => { void refreshHealth(); void refreshMode(); }, 3000);
    const slow = window.setInterval(() => { void refreshMetrics(); }, 10000);
    return () => { window.clearInterval(fast); window.clearInterval(slow); };
  }, [ready, refreshHealth, refreshMode, refreshMetrics]);

  async function runWork() {
    setBusy(true);
    const started = performance.now();
    try {
      const data = await api.work();
      const latencyMs = Math.round(performance.now() - started);
      setLog((entries) => [{ at: new Date().toLocaleTimeString(), latencyMs, message: data.message }, ...entries].slice(0, 8));
    } catch {
      const latencyMs = Math.round(performance.now() - started);
      setLog((entries) => [{ at: new Date().toLocaleTimeString(), latencyMs, message: "", failure: "FALHA — serviço não respondeu" }, ...entries].slice(0, 8));
    } finally {
      setBusy(false);
    }
  }

  const statusLines = counters
    ? Object.entries(counters.byStatus).sort(([a], [b]) => a.localeCompare(b))
    : [];

  return (
    <main className="crt-scanlines min-h-screen bg-bg px-6 py-8 font-mono text-parchment">
      <header className="mx-auto flex max-w-5xl items-center justify-between">
        <h1 className="font-pixel text-xs text-cyan glow-cyan">WORKBYTE // PAINEL</h1>
        <button
          onClick={() => { void api.logout().then(() => window.location.assign("/")); }}
          className="font-pixel border-2 border-magenta px-3 py-2 text-[10px] text-magenta transition-colors hover:bg-magenta/10"
        >
          SAIR
        </button>
      </header>

      <section className="mx-auto mt-8 grid max-w-5xl gap-6 md:grid-cols-3">
        <StatCard label="SINAL" value={online === null ? "..." : online ? "● ONLINE" : "✖ SIGNAL LOST"} tone={online ? "cyan" : "magenta"} glitch={online === false} />
        <StatCard label="MODO" value={mode === null ? "..." : mode.toUpperCase()} tone="violet" />
        <StatCard label="REQUISIÇÕES" value={counters ? String(Math.round(counters.total)) : "AGUARDANDO DADOS"} tone="amber" />
      </section>

      <section className="mx-auto mt-6 grid max-w-5xl gap-6 md:grid-cols-2">
        <div className="dialog-rbg dialog-rpg p-6">
          <p className="font-pixel text-[10px] opacity-60">CONSOLE DE TRABALHO</p>
          <button
            onClick={() => { void runWork(); }}
            disabled={busy}
            className="font-pixel mt-4 border-2 border-cyan px-4 py-3 text-[10px] text-cyan transition-colors hover:bg-cyan/10 disabled:opacity-50"
          >
            {busy ? "PROCESSANDO..." : "▶ EXECUTAR /WORK"}
          </button>
          <div className="mt-4 max-h-56 space-y-2 overflow-y-auto font-mono text-xs">
            {log.length === 0 && <p className="opacity-50">* Sem execuções nesta sessão.</p>}
            {log.map((entry, index) => (
              <p key={`${entry.at}-${index}`} className={entry.failure ? "text-magenta" : "opacity-80"}>
                [{entry.at}] {entry.failure ?? `${entry.message} — ${entry.latencyMs} ms`}
              </p>
            ))}
          </div>
        </div>
        <div className="dialog-rpg p-6">
          <p className="font-pixel text-[10px] opacity-60">CONTADORES POR STATUS</p>
          <div className="mt-4 space-y-2 font-mono text-xs">
            {statusLines.length === 0 && <p className="opacity-50">AGUARDANDO DADOS</p>}
            {statusLines.map(([status, value]) => (
              <p key={status} className="flex justify-between opacity-80">
                <span>HTTP {status}</span>
                <span className="text-cyan">{Math.round(value)}</span>
              </p>
            ))}
            {counters && counters.work > 0 && (
              <p className="flex justify-between border-t border-panel-edge pt-2 opacity-80">
                <span>/work</span>
                <span className="text-violet">{Math.round(counters.work)}</span>
              </p>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Buildar, testar e commitar**

```bash
cd demo-frontend && npm run build && npm run test
```

Expected: build limpo, 9 passed.

```bash
git add demo-frontend/src
git commit -m "feat(demo-frontend): painel protegido com sinal, modo, console /work e contadores"
```

---

### Task 9: Docker multi-stage + validação ponta a ponta + docs

**Files:**
- Modify: `Dockerfile` (estágio novo `demo-frontend` + COPY para `demo/static/`)
- Modify: `demo-frontend/package.json` (nada — só conferir que `build` gera `dist/`)
- Modify: `docs/roadmap.md` (marcar sub-projeto 2 como concluído)
- Create: `tmp/validate_demo_frontend.py` (script de validação — `tmp/` é ignorado pelo Git)

**Interfaces:**
- Consumes: tudo das Tasks 1–8.
- Produces: imagem `aularedes-platform:local` com `demo/static/` embutido; site servido em `http://127.0.0.1:8001`.

- [ ] **Step 1: Ajustar o `Dockerfile`** — adicionar o estágio após o estágio `frontend` existente e o COPY no estágio final:

```dockerfile
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM node:24-alpine AS demo-frontend
WORKDIR /demo-frontend
COPY demo-frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY demo-frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app:app /data
COPY backend/ backend/
COPY demo/ demo/
COPY --from=frontend /frontend/dist frontend/dist/
COPY --from=demo-frontend /demo-frontend/dist demo/static/
USER app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
```

- [ ] **Step 2: Adicionar as envs de credenciais ao serviço `web-demo` no `compose.yaml`** (o `.env` do configure.py já as tem):

```yaml
  web-demo:
    <<: *platform
    command: ["uvicorn", "demo.main:app", "--host", "0.0.0.0", "--port", "8001"]
    environment:
      LAB_TOKEN: ${LAB_TOKEN:?Execute python scripts/configure.py}
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?Execute python scripts/configure.py}
      HTTP_CONFIG_FILE: /etc/aularedes/runtime/http.json
    volumes: ["./infra:/etc/aularedes/runtime:ro"]
    ports: ["127.0.0.1:8001:8001"]
```

- [ ] **Step 3: Subir a stack com o build novo**

```bash
docker compose up -d --build --wait
```

Expected: todos os serviços healthy; `web-demo` expõe 8001.

- [ ] **Step 4: Validar com script Python** — Create `tmp/validate_demo_frontend.py`:

```python
"""Validação ponta a ponta do frontend do web-demo (rodar da raiz do repo)."""
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001"


def request(path, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers or {})
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode("utf-8", "replace")


status, _, page = request("/")
assert status == 200 and 'id="root"' in page, f"landing nao servida: {status}"

status, _, health = request("/health")
assert status == 200 and json.loads(health) == {"status": "ok"}, "contrato /health quebrado"

status, _, data = request("/login", method="POST", body={"username": "admin", "password": "senha-errada"})
assert status == 401, f"login deveria rejeitar: {status}"

env = {}
for line in open(".env", encoding="utf-8"):
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
status, headers, data = request("/login", method="POST", body={"username": env.get("ADMIN_USERNAME", "admin"), "password": env["ADMIN_PASSWORD"]})
assert status == 200 and json.loads(data) == {"authenticated": True}, f"login falhou: {status} {data}"
cookie = next(v.split(";")[0] for k, v in headers.items() if k.lower() == "set-cookie" and v.startswith("demo_session="))

status, headers, data = request("/login", headers={"Cookie": cookie})
assert status == 200 and json.loads(data) == {"authenticated": True}, "sessao nao reconhecida"

status, headers, data = request("/login", headers={"Cookie": "demo_session=abc.def"})
assert json.loads(data) == {"authenticated": False}, "cookie adulterado aceito"

status, _, metrics = request("/metrics")
assert status == 200 and "demo_http_requests_total" in metrics, "contrato /metrics quebrado"

print("VALIDACAO OK: landing, contratos, login e sessao funcionando")
```

Rodar:

```bash
.venv\Scripts\python.exe tmp\validate_demo_frontend.py
```

Expected: `VALIDACAO OK: landing, contratos, login e sessao funcionando`

- [ ] **Step 5: Validação manual de apresentação** — abrir `http://localhost:8001` no browser: landing com scanlines e arte; `Entrar` → login com as credenciais do `.env` → painel mostra `● ONLINE`; na sequência, disparar o **ataque 4 (modo offline)** pelo painel de ataques (porta 8002) e confirmar que o card vira `✖ SIGNAL LOST` em até ~3 s; voltar ao modo normal.

- [ ] **Step 6: Atualizar docs e commitar**

Marcar o sub-projeto 2 como concluído em `docs/roadmap.md` (mesma seção usada pelo painel de ataques).

```bash
git add Dockerfile compose.yaml docs/roadmap.md
git commit -m "build(demo): estaticos do demo-frontend na imagem e credenciais de login no compose"
```

---

## Self-Review do plano

1. **Cobertura da spec**: estáticos+Dockerfile (Tasks 1, 9) · `POST/GET /login`+`POST /logout` com cookie HMAC e credenciais do `.env` (Tasks 2, 3) · SPA `/`→`/login`→`/painel` (Tasks 6, 7, 8) · painel com 4 cards e polls 3s/10s (Task 8) · estados SIGNAL LOST/AGUARDANDO DADOS (Task 8) · visual CRT synthwave (Tasks 1, 6, 7, 8) · shoogle (Task 5) · testes backend+frontend+build (Tasks 2–4, 6–8) · validação Docker e ataque 4 (Task 9). Nenhum item da spec ficou sem task.
2. **Placeholders**: nenhum "TBD/TODO"; único ponto deliberadamente dinâmico é o export do `feature-carousel` do shoogle (o nome real é confirmado no arquivo gerado) e há fallback completo de código (Task 5, Step 5).
3. **Consistência de tipos**: `make_session/read_session` (Task 2) são os usados na Task 3; `SESSION_COOKIE`/`SESSION_TTL_SECONDS` importados corretamente; `parseDemoCounters`/`RequestCounters` (Task 4) batem com o uso na Task 8; `api.*` e `navigate` (Task 4) batem com Tasks 6–8; `create_demo(..., static_path=...)` da Task 3 é o usado no teste de fallback e no default da Task 9.
