import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Github } from "lucide-react";
import { login, signup } from "../services/api";
import { useAuthStore } from "../stores/useAuthStore";

export default function Auth() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = mode === "login" ? await login(email, password) : await signup(email, password, fullName);
      setAuth(resp.data.access_token, resp.data.user);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGithubLogin = () => {
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
    window.location.assign(`${apiBase}/auth/github/start`);
  };

  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="w-6 h-6 rounded bg-signal-amber" />
          <span className="font-display font-semibold tracking-tight text-mist-100">RepoSage AI</span>
        </div>

        <div className="bg-ink-900 border border-ink-700 rounded-card p-6">
          <div className="flex mb-6 text-sm border border-ink-700 rounded-md overflow-hidden">
            <button
              className={`flex-1 py-2 transition-colors ${mode === "login" ? "bg-ink-800 text-mist-100" : "text-mist-400"}`}
              onClick={() => setMode("login")}
            >
              Sign in
            </button>
            <button
              className={`flex-1 py-2 transition-colors ${mode === "signup" ? "bg-ink-800 text-mist-100" : "text-mist-400"}`}
              onClick={() => setMode("signup")}
            >
              Create account
            </button>
          </div>

          <button
            onClick={handleGithubLogin}
            className="w-full flex items-center justify-center gap-2 bg-ink-800 hover:bg-ink-700 border border-ink-700 rounded-md py-2.5 text-sm mb-4 transition-colors"
          >
            <Github size={16} /> Continue with GitHub
          </button>

          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-ink-700" />
            <span className="text-xs text-mist-400">or with email</span>
            <div className="h-px flex-1 bg-ink-700" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            {mode === "signup" && (
              <input
                type="text"
                placeholder="Full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-ink-800 border border-ink-700 rounded-md px-3 py-2 text-sm outline-none focus:border-signal-teal transition-colors"
              />
            )}
            <input
              type="email"
              required
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-ink-800 border border-ink-700 rounded-md px-3 py-2 text-sm outline-none focus:border-signal-teal transition-colors"
            />
            <input
              type="password"
              required
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-ink-800 border border-ink-700 rounded-md px-3 py-2 text-sm outline-none focus:border-signal-teal transition-colors"
            />

            {error && <p className="text-signal-rose text-xs">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-signal-amber text-ink-950 font-medium rounded-md py-2.5 text-sm hover:brightness-110 transition disabled:opacity-60"
            >
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
