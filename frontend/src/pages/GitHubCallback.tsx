import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { exchangeGithubTicket } from "../services/api";
import { useAuthStore } from "../stores/useAuthStore";

export default function GitHubCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const ticket = params.get("ticket");
    if (!ticket) {
      setError("GitHub did not return a valid login ticket.");
      return;
    }

    exchangeGithubTicket(ticket)
      .then((response) => {
        setAuth(response.data.access_token, response.data.user);
        navigate("/dashboard", { replace: true });
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || "GitHub login failed. Please try again.");
      });
  }, [navigate, params, setAuth]);

  return (
    <main className="min-h-screen bg-ink-950 text-mist-100 grid place-items-center px-6">
      <section className="w-full max-w-md rounded-card border border-ink-700 bg-ink-900 p-8 text-center">
        {!error ? (
          <>
            <div className="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-2 border-ink-600 border-t-signal-amber" />
            <h1 className="font-display text-xl font-semibold">Connecting GitHub</h1>
            <p className="mt-2 text-sm text-mist-400">Completing secure authentication…</p>
          </>
        ) : (
          <>
            <h1 className="font-display text-xl font-semibold">GitHub login failed</h1>
            <p className="mt-3 text-sm text-signal-rose">{error}</p>
            <Link className="mt-6 inline-block rounded-md bg-signal-amber px-4 py-2 text-sm font-medium text-ink-950" to="/auth">
              Return to sign in
            </Link>
          </>
        )}
      </section>
    </main>
  );
}
