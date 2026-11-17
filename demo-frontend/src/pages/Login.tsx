import { useState, type FormEvent } from "react";
import { api, navigate } from "../api";
import { RetroWindow } from "../components/RetroWindow";

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
    setError("! Credenciais inválidas. Verifique ADMIN_USERNAME e ADMIN_PASSWORD no .env");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#05060f] p-4 font-mono text-parchment">
      <div className="w-full max-w-md">
        <RetroWindow
          title="AUTENTICAÇÃO // OPERADOR"
          icon="🔒"
          subtitle="SESSÃO CRIPTO"
          variant="cream"
          statusText="SISTEMA: PRONTO PARA LOGIN"
        >
          <div className="text-black space-y-4">
            <div>
              <h2 className="font-pixel text-xs font-bold uppercase tracking-wider text-black">
                ACESSO RESTRITO
              </h2>
              <p className="mt-1 text-[11px] opacity-75">
                * Somente operadores autorizados do laboratório de redes.
              </p>
            </div>

            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block">
                <span className="font-pixel text-[9px] text-black uppercase">
                  OPERADOR // USUÁRIO
                </span>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  placeholder="admin"
                  required
                  className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-xs text-black outline-none focus:bg-[#ffea75]/20 shadow-[inset_2px_2px_0_#999]"
                />
              </label>

              <label className="block">
                <span className="font-pixel text-[9px] text-black uppercase">
                  SENHA DE ACESSO
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-xs text-black outline-none focus:bg-[#ffea75]/20 shadow-[inset_2px_2px_0_#999]"
                />
              </label>

              {error && (
                <div className="border-2 border-red-600 bg-red-100 p-2.5 text-[11px] text-red-700 font-pixel">
                  {error}
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={busy}
                  className="w-full border border-black bg-black py-3 font-pixel text-xs tracking-wider text-[#ffea75] transition-colors hover:bg-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan disabled:opacity-50"
                >
                  {busy ? "VALIDANDO SESSÃO..." : "▶ ENTRAR NO PAINEL"}
                </button>
              </div>
            </form>

            <div className="border-t border-black/30 pt-3 flex items-center justify-between text-[10px]">
              <button
                type="button"
                onClick={() => navigate("/")}
                className="underline hover:opacity-100 opacity-70"
              >
                ← Voltar ao início
              </button>
              <span className="opacity-50">SESSÃO: HMAC-SHA256</span>
            </div>
          </div>
        </RetroWindow>
      </div>
    </main>
  );
}
