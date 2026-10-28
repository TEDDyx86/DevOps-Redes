import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, LockKeyhole, Network, RefreshCw } from "lucide-react";
import App from "./App";
import { APIError, request, setCSRFToken } from "./api";

interface Session {
  username: string;
  csrf_token: string;
  expires_at: number;
}

export default function Auth() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const mutating = useRef(false);

  function accept(value: Session | null) {
    setCSRFToken(value?.csrf_token ?? null);
    setSession(value);
  }

  useEffect(() => {
    let active = true;
    async function check() {
      if (mutating.current) return;
      const expected = generation.current;
      try {
        const value = await request<Session>("/api/auth/session");
        if (active && expected === generation.current) {
          accept(value);
          setError(null);
        }
      } catch (reason) {
        if (active && expected === generation.current) {
          accept(null);
          if (!(reason instanceof APIError && reason.status === 401))
            setError(
              reason instanceof Error
                ? reason.message
                : "Não foi possível verificar a sessão.",
            );
        }
      } finally {
        if (active) setChecking(false);
      }
    }
    void check();
    const expired = () => {
      generation.current++;
      accept(null);
      setError("Sua sessão terminou. Entre novamente para continuar.");
    };
    window.addEventListener("session-expired", expired);
    // Also checks expiry while the security page or an idle tab is open.
    const timer = window.setInterval(() => {
      void check();
    }, 15000);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("session-expired", expired);
    };
  }, []);

  async function login(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    mutating.current = true;
    generation.current++;
    try {
      accept(
        await request<Session>("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        }),
      );
      setPassword("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Não foi possível entrar.",
      );
      setPassword("");
    } finally {
      generation.current++;
      mutating.current = false;
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    mutating.current = true;
    generation.current++;
    try {
      await request("/api/auth/logout", { method: "POST" });
      accept(null);
      setError(null);
    } catch (reason) {
      if (reason instanceof APIError && reason.status === 401) accept(null);
      else
        setError(
          reason instanceof Error
            ? reason.message
            : "Não foi possível sair. Tente novamente.",
        );
    } finally {
      generation.current++;
      mutating.current = false;
      setBusy(false);
    }
  }

  if (session)
    return (
      <App
        username={session.username}
        onLogout={() => {
          void logout();
        }}
        logoutBusy={busy}
        authError={error}
      />
    );
  return (
    <main className="login-shell">
      <section className="login-context" aria-label="AulaRedes">
        <a className="brand" href="#overview">
          <span className="brand-mark">
            <Network size={24} />
          </span>
          <span>
            Aula<span className="brand-light">Redes</span>
            <small>OBSERVABILIDADE</small>
          </span>
        </a>
        <div className="login-story">
          <span className="eyebrow">LABORATÓRIO DE REDES</span>
          <h1>
            Quatro serviços.
            <br />
            Um ponto de observação.
          </h1>
          <p>
            Acompanhe o caminho de uma falha: da primeira sonda ao alerta e à
            recuperação.
          </p>
          <div className="protocol-list">
            <span>HTTP</span>
            <span>PostgreSQL</span>
            <span>DNS</span>
            <span>SMTP</span>
          </div>
        </div>
        <p className="login-footnote">Projeto final · Redes de Computadores</p>
      </section>
      <section className="login-form-area">
        <div className="login-form-wrap">
          <span className="login-lock">
            <LockKeyhole size={24} />
          </span>
          <span className="eyebrow">ACESSO AO LABORATÓRIO</span>
          <h2>Entre para acompanhar.</h2>
          <p>Use a conta de administrador deste ambiente.</p>
          {checking ? (
            <p className="login-loading" role="status">
              <RefreshCw size={17} className="spinning" /> Verificando sua
              sessão…
            </p>
          ) : (
            <form onSubmit={login} className="login-form">
              <label htmlFor="username">Usuário</label>
              <input
                id="username"
                name="username"
                autoComplete="username"
                required
                maxLength={64}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={busy}
              />
              <label htmlFor="password">Senha</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={256}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={busy}
              />
              {error && (
                <p className="login-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="button primary" disabled={busy}>
                {busy ? "Entrando…" : "Entrar"}
                <ArrowRight size={17} />
              </button>
            </form>
          )}
          <div className="login-help">
            <strong>Primeiro acesso?</strong>
            <p>
              O arquivo local <code>.env</code> contém{" "}
              <code>ADMIN_USERNAME</code> e <code>ADMIN_PASSWORD</code>, gerados
              na configuração do projeto.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
