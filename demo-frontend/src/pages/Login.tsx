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
