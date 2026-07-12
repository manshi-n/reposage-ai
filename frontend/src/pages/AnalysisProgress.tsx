import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { getAnalysisStatus } from "../services/api";
import type { AnalysisStatusValue } from "../types";

const STEPS: { key: AnalysisStatusValue; label: string }[] = [
  { key: "cloning", label: "Cloning repository" },
  { key: "detecting_languages", label: "Detecting languages" },
  { key: "running_static_analysis", label: "Running static analysis" },
  { key: "building_index", label: "Building repository index" },
  { key: "running_ai_review", label: "Running AI review" },
  { key: "generating_report", label: "Generating final report" },
];

function stepState(stepKey: string, currentStatus: string): "done" | "active" | "pending" {
  const order = ["pending", ...STEPS.map((s) => s.key), "complete"];
  const currentIdx = order.indexOf(currentStatus);
  const stepIdx = order.indexOf(stepKey);
  if (currentStatus === "complete" || stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "active";
  return "pending";
}

export default function AnalysisProgress() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>("pending");
  const [percent, setPercent] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!analysisId) return;

    const poll = async () => {
      try {
        const resp = await getAnalysisStatus(analysisId);
        setStatus(resp.data.status);
        setPercent(resp.data.progress_percent);
        if (resp.data.error_message) setErrorMessage(resp.data.error_message);

        if (resp.data.status === "complete") {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
          navigate(`/analyses/${analysisId}/report`);
        }
        if (resp.data.status === "failed" && intervalRef.current) {
          window.clearInterval(intervalRef.current);
        }
      } catch {
        // transient errors are fine, next poll will retry
      }
    };

    poll();
    intervalRef.current = window.setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, [analysisId, navigate]);

  return (
    <div className="p-8 max-w-xl mx-auto">
      <h1 className="font-display text-2xl font-semibold text-mist-100 mb-1">Analyzing repository</h1>
      <p className="text-mist-400 text-sm mb-8">This can take a minute or two depending on repo size.</p>

      <div className="bg-ink-900 border border-ink-700 rounded-card p-6">
        <div className="h-1.5 rounded-full bg-ink-700 overflow-hidden mb-6">
          <div
            className="h-full bg-signal-teal transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>

        <div className="space-y-3">
          {STEPS.map((step) => {
            const state = stepState(step.key, status);
            return (
              <div key={step.key} className="flex items-center gap-3 text-sm">
                {state === "done" && <CheckCircle2 size={18} className="text-signal-teal shrink-0" />}
                {state === "active" && <Loader2 size={18} className="text-signal-amber shrink-0 animate-spin" />}
                {state === "pending" && <Circle size={18} className="text-mist-400 shrink-0" />}
                <span className={state === "pending" ? "text-mist-400" : "text-mist-100"}>{step.label}</span>
              </div>
            );
          })}
        </div>

        {status === "failed" && (
          <p className="text-signal-rose text-sm mt-6">
            Analysis failed{errorMessage ? `: ${errorMessage}` : "."}
          </p>
        )}
      </div>
    </div>
  );
}
