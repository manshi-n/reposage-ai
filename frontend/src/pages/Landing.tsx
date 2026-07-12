import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, Gauge, FileCode2, MessagesSquare } from "lucide-react";

const CAPABILITIES = [
  { icon: <ShieldCheck size={18} />, title: "Security review", copy: "Hard-coded secrets, injection, unsafe auth — caught before merge.", tone: "gutter-critical" },
  { icon: <Gauge size={18} />, title: "Performance & architecture", copy: "N+1 queries, blocking calls, and layering problems, explained plainly.", tone: "gutter-high" },
  { icon: <FileCode2 size={18} />, title: "Tests & docs, generated", copy: "Framework-correct unit tests and a real README, not boilerplate.", tone: "gutter-medium" },
  { icon: <MessagesSquare size={18} />, title: "Chat with the repo", copy: "Ask where auth breaks or how payments flow — answers cite file and line.", tone: "gutter-low" },
];

const SAMPLE_SCORES = [
  { label: "Security", value: 72 },
  { label: "Architecture", value: 84 },
  { label: "Testing", value: 54 },
  { label: "Docs", value: 65 },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-ink-950 text-mist-100">
      <header className="max-w-6xl mx-auto flex items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-signal-amber" />
          <span className="font-display font-semibold tracking-tight">RepoSage AI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/auth" className="text-sm text-mist-300 hover:text-mist-100 transition-colors">
            Sign in
          </Link>
          <Link
            to="/auth"
            className="text-sm bg-signal-amber text-ink-950 font-medium px-4 py-2 rounded-md hover:brightness-110 transition"
          >
            Connect GitHub
          </Link>
        </div>
      </header>

      {/* Hero: the thesis is a live-looking diff, since that's the actual mental model of the product */}
      <section className="max-w-6xl mx-auto px-6 pt-14 pb-20 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <p className="font-mono text-xs text-signal-teal mb-4 tracking-wide">
            git diff --stat  ·  before you ship
          </p>
          <h1 className="font-display text-4xl md:text-5xl font-semibold leading-[1.1] tracking-tight mb-6">
            Know your codebase
            <br />
            before it knows your bugs.
          </h1>
          <p className="text-mist-300 text-lg mb-8 max-w-md">
            Point RepoSage AI at any repository. It clones it, runs real static
            analysis alongside specialized AI agents, and hands you a scored
            report — plus generated tests, docs, and a repo-aware chat.
          </p>
          <div className="flex items-center gap-4">
            <Link
              to="/auth"
              className="inline-flex items-center gap-2 bg-signal-amber text-ink-950 font-medium px-5 py-3 rounded-md hover:brightness-110 transition"
            >
              Analyze a repository <ArrowRight size={16} />
            </Link>
            <span className="text-mist-400 text-sm">Python · JS/TS · Java · Go · Ruby · more</span>
          </div>
        </div>

        {/* Signature element: a diff-style mock report card */}
        <div className="bg-ink-900 border border-ink-700 rounded-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-ink-700 bg-ink-800/60">
            <span className="font-mono text-xs text-mist-300">AdvoCouncil / main</span>
            <span className="font-mono text-xs text-signal-teal">Overall 78/100</span>
          </div>
          <div className="p-5 space-y-3">
            {SAMPLE_SCORES.map((s) => (
              <div key={s.label} className="diff-gutter gutter-medium">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-mist-200">{s.label}</span>
                  <span className="font-mono text-mist-300">{s.value}/100</span>
                </div>
                <div className="h-1.5 rounded-full bg-ink-700 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-signal-teal"
                    style={{ width: `${s.value}%` }}
                  />
                </div>
              </div>
            ))}
            <div className="diff-gutter gutter-critical pt-2 text-sm">
              <div className="text-mist-100">Hard-coded JWT secret</div>
              <div className="font-mono text-xs text-mist-400">backend/config/auth.js:14</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-2 gap-4">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className={`diff-gutter ${c.tone} bg-ink-900 border border-ink-700 rounded-card p-5`}>
              <div className="flex items-center gap-2 text-signal-teal mb-2">{c.icon}</div>
              <h3 className="font-display font-medium mb-1">{c.title}</h3>
              <p className="text-mist-300 text-sm">{c.copy}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
