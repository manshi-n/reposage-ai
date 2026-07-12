import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { connectRepository, createAnalysis } from "../services/api";

const MODULES = [
  { key: "bugs", label: "Bugs" },
  { key: "security", label: "Security" },
  { key: "performance", label: "Performance" },
  { key: "architecture", label: "Architecture" },
  { key: "quality", label: "Code quality" },
  { key: "docs", label: "Documentation" },
  { key: "tests", label: "Test coverage" },
];

export default function NewAnalysis() {
  const [cloneUrl, setCloneUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [modules, setModules] = useState<string[]>(MODULES.map((m) => m.key));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const toggleModule = (key: string) => {
    setModules((prev) => (prev.includes(key) ? prev.filter((m) => m !== key) : [...prev, key]));
  };

  const handleStart = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const repoResp = await connectRepository(cloneUrl, false, branch);
      const analysisResp = await createAnalysis({
        repository_id: repoResp.data.id,
        branch,
        modules,
      });
      navigate(`/analyses/${analysisResp.data.id}/progress`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not start analysis.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="font-display text-2xl font-semibold text-mist-100 mb-1">New analysis</h1>
      <p className="text-mist-400 text-sm mb-8">
        Paste a public repository URL to get started. Private repos need GitHub connected first.
      </p>

      <div className="bg-ink-900 border border-ink-700 rounded-card p-6 space-y-5">
        <div>
          <label className="block text-sm text-mist-300 mb-1.5">Repository URL</label>
          <input
            value={cloneUrl}
            onChange={(e) => setCloneUrl(e.target.value)}
            placeholder="https://github.com/owner/repo.git"
            className="w-full bg-ink-800 border border-ink-700 rounded-md px-3 py-2 text-sm font-mono outline-none focus:border-signal-teal transition-colors"
          />
        </div>

        <div>
          <label className="block text-sm text-mist-300 mb-1.5">Branch</label>
          <input
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="w-full bg-ink-800 border border-ink-700 rounded-md px-3 py-2 text-sm font-mono outline-none focus:border-signal-teal transition-colors"
          />
        </div>

        <div>
          <label className="block text-sm text-mist-300 mb-2">Analysis modules</label>
          <div className="grid grid-cols-2 gap-2">
            {MODULES.map((m) => (
              <label
                key={m.key}
                className="flex items-center gap-2 text-sm text-mist-200 bg-ink-800 border border-ink-700 rounded-md px-3 py-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={modules.includes(m.key)}
                  onChange={() => toggleModule(m.key)}
                  className="accent-signal-teal"
                />
                {m.label}
              </label>
            ))}
          </div>
        </div>

        {error && <p className="text-signal-rose text-sm">{error}</p>}

        <button
          onClick={handleStart}
          disabled={!cloneUrl || submitting}
          className="w-full bg-signal-amber text-ink-950 font-medium rounded-md py-2.5 text-sm hover:brightness-110 transition disabled:opacity-50"
        >
          {submitting ? "Starting…" : "Start analysis"}
        </button>
      </div>
    </div>
  );
}
