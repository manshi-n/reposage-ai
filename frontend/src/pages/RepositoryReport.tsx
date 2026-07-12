import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import {
  AlertTriangle,
  Boxes,
  Bug,
  CheckCircle2,
  Code2,
  Download,
  FileText,
  Gauge,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  Loader2,
  MessageSquareCode,
  PackageSearch,
  Send,
  TestTube2,
  ShieldCheck,
} from "lucide-react";

import {
  chatWithRepository,
  createPullRequest,
  downloadReport,
  generateDocs,
  generateTests,
  getAnalysis,
  getIssues,
} from "../services/api";

import ScoreRing from "../components/ScoreRing";
import IssueList from "../components/IssueList";

const TABS = [
  {
    label: "Overview",
    icon: LayoutDashboard,
  },
  {
    label: "Issues",
    icon: Bug,
  },
  {
    label: "Security",
    icon: ShieldCheck,
  },
  {
    label: "Architecture",
    icon: Boxes,
  },
  {
    label: "Performance",
    icon: Gauge,
  },
  {
    label: "Code Quality",
    icon: Code2,
  },
  {
    label: "Tests",
    icon: TestTube2,
  },
  {
    label: "Documentation",
    icon: FileText,
  },
  {
    label: "Dependencies",
    icon: PackageSearch,
  },
  {
    label: "Repository Chat",
    icon: MessageSquareCode,
  },
] as const;

type Tab = (typeof TABS)[number]["label"];

type SeverityCount = {
  critical: number;
  high: number;
  medium: number;
  low: number;
};

export default function RepositoryReport() {
  const { analysisId } = useParams<{
    analysisId: string;
  }>();

  const [tab, setTab] =
    useState<Tab>("Overview");

  const [downloadOpen, setDownloadOpen] =
    useState(false);

  const [downloading, setDownloading] =
    useState(false);

  const [downloadError, setDownloadError] =
    useState<string | null>(null);

  const {
    data: analysis,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [
      "analysis",
      analysisId,
    ],

    queryFn: () =>
      getAnalysis(
        analysisId!
      ).then(
        (response) =>
          response.data
      ),

    enabled: Boolean(
      analysisId
    ),
  });

  const {
    data: issues = [],
  } = useQuery({
    queryKey: [
      "issues",
      analysisId,
    ],

    queryFn: () =>
      getIssues(
        analysisId!
      ).then(
        (response) =>
          response.data
      ),

    enabled: Boolean(
      analysisId
    ),
  });

  const prMutation =
    useMutation({
      mutationFn: () =>
        createPullRequest(
          analysisId!
        ),
    });

  const handleDownload = async (
    format:
      | "pdf"
      | "md"
      | "json"
      | "csv"
  ) => {
    if (!analysisId) {
      return;
    }

    setDownloadError(null);
    setDownloading(true);

    try {
      await downloadReport(
        analysisId,
        format
      );

      setDownloadOpen(false);
    } catch (error: any) {
      setDownloadError(
        error?.response?.data
          ?.detail ||
          "Could not download report."
      );
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <div className="text-center">
          <Loader2 className="mx-auto animate-spin text-signal-teal" />

          <p className="mt-3 text-sm text-mist-400">
            Loading repository report…
          </p>
        </div>
      </div>
    );
  }

  if (
    isError ||
    !analysis
  ) {
    return (
      <div className="mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto text-signal-rose" />

        <h1 className="mt-4 font-display text-xl text-mist-100">
          Report unavailable
        </h1>

        <p className="mt-2 text-sm text-mist-400">
          The analysis report could
          not be loaded.
        </p>

        <Link
          to="/dashboard"
          className="mt-5 inline-block text-sm text-signal-teal"
        >
          Return to dashboard
        </Link>
      </div>
    );
  }

  const severityCount: SeverityCount = {
    critical: issues.filter(
      (issue) =>
        issue.severity ===
        "critical"
    ).length,

    high: issues.filter(
      (issue) =>
        issue.severity === "high"
    ).length,

    medium: issues.filter(
      (issue) =>
        issue.severity ===
        "medium"
    ).length,

    low: issues.filter(
      (issue) =>
        issue.severity === "low"
    ).length,
  };

  return (
    <main className="mx-auto max-w-[1500px] p-4 md:p-8">
      <header className="mb-6 rounded-3xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-800 p-6">
        <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-center">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-signal-teal/10 px-3 py-1 text-xs text-signal-teal">
                <CheckCircle2
                  size={13}
                />
                Analysis complete
              </span>

              <span className="inline-flex items-center gap-1.5 rounded-full bg-ink-950/50 px-3 py-1 text-xs text-mist-400">
                <GitBranch
                  size={13}
                />
                {analysis.branch}
              </span>
            </div>

            <h1 className="font-display text-2xl font-semibold text-mist-100 md:text-3xl">
              Repository health report
            </h1>

            <p className="mt-2 text-sm text-mist-400">
              Review findings,
              generate improvements,
              and explore your codebase.
            </p>
          </div>

          <div className="relative flex flex-wrap gap-2">
            <div className="relative">
              <button
                type="button"
                onClick={() =>
                  setDownloadOpen(
                    (value) =>
                      !value
                  )
                }
                className="inline-flex items-center gap-2 rounded-xl border border-ink-600 bg-ink-900 px-4 py-2.5 text-sm text-mist-200 transition hover:border-ink-500"
              >
                {downloading ? (
                  <Loader2
                    size={15}
                    className="animate-spin"
                  />
                ) : (
                  <Download
                    size={15}
                  />
                )}

                Download report
              </button>

              {downloadOpen && (
                <div className="absolute right-0 z-30 mt-2 w-44 rounded-xl border border-ink-700 bg-ink-900 p-2 shadow-2xl">
                  {[
                    "pdf",
                    "md",
                    "json",
                    "csv",
                  ].map((format) => (
                    <button
                      type="button"
                      key={format}
                      onClick={() =>
                        handleDownload(
                          format as
                            | "pdf"
                            | "md"
                            | "json"
                            | "csv"
                        )
                      }
                      className="w-full rounded-lg px-3 py-2 text-left text-sm uppercase text-mist-300 hover:bg-ink-800"
                    >
                      {format}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() =>
                prMutation.mutate()
              }
              disabled={
                prMutation.isPending
              }
              className="inline-flex items-center gap-2 rounded-xl bg-signal-amber px-4 py-2.5 text-sm font-medium text-ink-950 disabled:opacity-50"
            >
              {prMutation.isPending ? (
                <Loader2
                  size={15}
                  className="animate-spin"
                />
              ) : (
                <GitPullRequest
                  size={15}
                />
              )}

              Create pull request
            </button>
          </div>
        </div>

        {downloadError && (
          <p className="mt-4 text-sm text-signal-rose">
            {downloadError}
          </p>
        )}

        {prMutation.isSuccess && (
          <p className="mt-4 text-sm text-signal-teal">
            Pull request opened:{" "}
            <a
              href={
                prMutation.data.data
                  .pr_url
              }
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              #
              {
                prMutation.data.data
                  .pr_number
              }
            </a>
          </p>
        )}

        {prMutation.isError && (
          <p className="mt-4 text-sm text-signal-rose">
            {(prMutation.error as any)
              ?.response?.data
              ?.detail ||
              "Could not create pull request."}
          </p>
        )}
      </header>

      <div className="grid gap-6 xl:grid-cols-[230px_minmax(0,1fr)]">
        <aside className="h-fit rounded-2xl border border-ink-700 bg-ink-900 p-3 xl:sticky xl:top-6">
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-mist-500">
            Report sections
          </p>

          <nav className="space-y-1">
            {TABS.map(
              ({
                label,
                icon: Icon,
              }) => (
                <button
                  type="button"
                  key={label}
                  onClick={() =>
                    setTab(label)
                  }
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                    tab === label
                      ? "bg-signal-teal/10 text-signal-teal"
                      : "text-mist-400 hover:bg-ink-800 hover:text-mist-100"
                  }`}
                >
                  <Icon
                    size={16}
                  />
                  {label}
                </button>
              )
            )}
          </nav>
        </aside>

        <section className="min-w-0">
          {tab === "Overview" && (
            <OverviewTab
              analysis={analysis}
              issueCount={
                issues.length
              }
              severityCount={
                severityCount
              }
            />
          )}

          {tab === "Issues" && (
            <IssueList
              analysisId={
                analysis.id
              }
              issues={issues}
              repositoryUrl={
                analysis.repository_clone_url
              }
              branch={
                analysis.branch
              }
            />
          )}

          {tab === "Security" && (
            <IssueList
              analysisId={
                analysis.id
              }
              issues={issues}
              category="security"
              repositoryUrl={
                analysis.repository_clone_url
              }
              branch={
                analysis.branch
              }
            />
          )}

          {tab ===
            "Architecture" && (
            <ArchitectureTab
              summary={
                analysis.architecture_summary
              }
            />
          )}

          {tab ===
            "Performance" && (
            <IssueList
              analysisId={
                analysis.id
              }
              issues={issues}
              category="performance"
              repositoryUrl={
                analysis.repository_clone_url
              }
              branch={
                analysis.branch
              }
            />
          )}

          {tab ===
            "Code Quality" && (
            <IssueList
              analysisId={
                analysis.id
              }
              issues={issues}
              category="code_quality"
              repositoryUrl={
                analysis.repository_clone_url
              }
              branch={
                analysis.branch
              }
            />
          )}

          {tab === "Tests" && (
            <TestsTab
              analysisId={
                analysis.id
              }
            />
          )}

          {tab ===
            "Documentation" && (
            <DocumentationTab
              analysisId={
                analysis.id
              }
            />
          )}

          {tab ===
            "Dependencies" && (
            <IssueList
              analysisId={
                analysis.id
              }
              issues={issues.filter(
                (issue) =>
                  issue.source_tool ===
                    "npm-audit" ||
                  issue.title
                    .toLowerCase()
                    .includes(
                      "dependency"
                    )
              )}
              repositoryUrl={
                analysis.repository_clone_url
              }
              branch={
                analysis.branch
              }
            />
          )}

          {tab ===
            "Repository Chat" && (
            <ChatTab
              repositoryId={
                analysis.repository_id
              }
            />
          )}
        </section>
      </div>
    </main>
  );
}

function OverviewTab({
  analysis,
  issueCount,
  severityCount,
}: {
  analysis: any;
  issueCount: number;
  severityCount: SeverityCount;
}) {
  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <ScoreRing
          label="Overall score"
          value={analysis.overall_score}
          size={88}
          description="Combined repository health score"
        />

        <ScoreRing
          label="Security"
          value={analysis.security_score}
          size={88}
        />

        <ScoreRing
          label="Maintainability"
          value={
            analysis.maintainability_score
          }
          size={88}
        />

        <ScoreRing
          label="Performance"
          value={analysis.performance_score}
          size={88}
        />

        <ScoreRing
          label="Documentation"
          value={
            analysis.documentation_score
          }
          size={88}
        />

        <ScoreRing
          label="Testing"
          value={analysis.testing_score}
          size={88}
        />

        <ScoreRing
          label="Architecture"
          value={analysis.architecture_score}
          size={88}
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Files scanned"
          value={analysis.file_count}
        />

        <Stat
          label="Lines of code"
          value={analysis.lines_of_code}
        />

        <Stat
          label="Languages"
          value={
            analysis.languages
          }
        />

        <Stat
          label="Total findings"
          value={issueCount}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-ink-700 bg-ink-900 p-5">
          <h3 className="font-display text-lg font-semibold text-mist-100">
            Finding distribution
          </h3>

          <p className="mt-1 text-sm text-mist-400">
            Findings grouped by severity.
          </p>

          <div className="mt-5 grid grid-cols-2 gap-3">
            <SeverityStat
              label="Critical"
              value={
                severityCount.critical
              }
              className="text-red-400"
            />

            <SeverityStat
              label="High"
              value={
                severityCount.high
              }
              className="text-orange-400"
            />

            <SeverityStat
              label="Medium"
              value={
                severityCount.medium
              }
              className="text-amber-400"
            />

            <SeverityStat
              label="Low"
              value={
                severityCount.low
              }
              className="text-sky-400"
            />
          </div>
        </div>

        <div className="rounded-2xl border border-ink-700 bg-ink-900 p-5">
          <h3 className="font-display text-lg font-semibold text-mist-100">
            Recommended next steps
          </h3>

          <div className="mt-4 space-y-3">
            <Recommendation
              title="Improve test coverage"
              text="Generate tests for critical modules and API routes."
            />

            <Recommendation
              title="Review documentation"
              text="Generate a README and environment-variable guide."
            />

            <Recommendation
              title="Resolve highest-risk findings"
              text="Prioritize critical and high-severity issues."
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function LanguageStat({
  languages,
}: {
  languages?: string;
}) {
  const items = languages
    ? languages
        .split(",")
        .map((language) => language.trim())
        .filter(Boolean)
    : [];

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-900 p-5">
      <p className="text-xs uppercase tracking-wide text-mist-500">
        Languages
      </p>

      {items.length === 0 ? (
        <p className="mt-2 text-sm text-mist-400">
          No languages detected
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {items.map((language) => (
            <span
              key={language}
              className="rounded-full border border-ink-700 bg-ink-950 px-3 py-1.5 text-xs text-mist-200"
            >
              {language}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: any;
}) {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-900 p-5">
      <p className="text-xs uppercase tracking-wide text-mist-500">
        {label}
      </p>

      <p className="mt-2 truncate font-mono text-lg font-medium text-mist-100">
        {value ?? "—"}
      </p>
    </div>
  );
}

function SeverityStat({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className: string;
}) {
  return (
    <div className="rounded-xl bg-ink-950 p-4">
      <p
        className={`font-mono text-2xl font-semibold ${className}`}
      >
        {value}
      </p>

      <p className="mt-1 text-xs text-mist-400">
        {label}
      </p>
    </div>
  );
}

function Recommendation({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-950 p-4">
      <p className="text-sm font-medium text-mist-100">
        {title}
      </p>

      <p className="mt-1 text-xs leading-relaxed text-mist-400">
        {text}
      </p>
    </div>
  );
}

function ArchitectureTab({
  summary,
}: {
  summary?: string;
}) {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-900 p-6">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-signal-teal/10 text-signal-teal">
          <Boxes size={19} />
        </div>

        <div>
          <h3 className="font-display text-lg font-semibold text-mist-100">
            Architecture summary
          </h3>

          <p className="text-xs text-mist-400">
            AI-generated overview of the repository structure.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-ink-700 bg-ink-950 p-5">
        <p className="whitespace-pre-wrap text-sm leading-7 text-mist-300">
          {summary ||
            "Architecture summary has not been generated yet."}
        </p>
      </div>
    </div>
  );
}

function TestsTab({
  analysisId,
}: {
  analysisId: string;
}) {
  const mutation = useMutation({
    mutationFn: () =>
      generateTests(
        analysisId
      ).then(
        (response) =>
          response.data
      ),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-ink-700 bg-ink-900 p-5 sm:flex-row sm:items-center">
        <div>
          <h3 className="font-display text-lg font-semibold text-mist-100">
            Test generation
          </h3>

          <p className="mt-1 text-sm text-mist-400">
            Generate framework-specific tests for important repository files.
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            mutation.mutate()
          }
          disabled={
            mutation.isPending
          }
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-signal-amber px-4 py-2.5 text-sm font-medium text-ink-950 disabled:opacity-50"
        >
          {mutation.isPending ? (
            <Loader2
              size={15}
              className="animate-spin"
            />
          ) : (
            <TestTube2
              size={15}
            />
          )}

          {mutation.isPending
            ? "Generating tests…"
            : "Generate tests"}
        </button>
      </div>

      {mutation.isError && (
        <div className="rounded-xl border border-signal-rose/20 bg-signal-rose/5 p-4 text-sm text-signal-rose">
          {(mutation.error as any)
            ?.response?.data
            ?.detail ||
            "Could not generate tests."}
        </div>
      )}

      {!mutation.data &&
        !mutation.isPending && (
          <div className="rounded-2xl border border-dashed border-ink-700 bg-ink-900/40 px-6 py-12 text-center">
            <TestTube2 className="mx-auto text-mist-500" />

            <h4 className="mt-4 font-display text-lg text-mist-100">
              No generated tests yet
            </h4>

            <p className="mt-2 text-sm text-mist-400">
              Generate tests to preview framework-specific test files here.
            </p>
          </div>
        )}

      <div className="space-y-4">
        {mutation.data?.map(
          (test) => (
            <article
              key={test.id}
              className="rounded-2xl border border-ink-700 bg-ink-900 p-5"
            >
              <div className="mb-3 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                <span className="font-mono text-sm text-mist-100">
                  {test.file_name}
                </span>

                <span className="text-xs text-mist-400">
                  {test.framework} ·{" "}
                  {test.target_file}
                </span>
              </div>

              <pre className="max-h-[500px] overflow-auto rounded-xl border border-ink-700 bg-ink-950 p-4 font-mono text-xs leading-6 text-mist-200">
                {test.content}
              </pre>
            </article>
          )
        )}
      </div>
    </div>
  );
}

function DocumentationTab({
  analysisId,
}: {
  analysisId: string;
}) {
  const mutation = useMutation({
    mutationFn: () =>
      generateDocs(
        analysisId
      ).then(
        (response) =>
          response.data
      ),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-ink-700 bg-ink-900 p-5 sm:flex-row sm:items-center">
        <div>
          <h3 className="font-display text-lg font-semibold text-mist-100">
            Documentation generation
          </h3>

          <p className="mt-1 text-sm text-mist-400">
            Generate setup guides, architecture notes, and project documentation.
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            mutation.mutate()
          }
          disabled={
            mutation.isPending
          }
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-signal-amber px-4 py-2.5 text-sm font-medium text-ink-950 disabled:opacity-50"
        >
          {mutation.isPending ? (
            <Loader2
              size={15}
              className="animate-spin"
            />
          ) : (
            <FileText
              size={15}
            />
          )}

          {mutation.isPending
            ? "Generating documentation…"
            : "Generate documentation"}
        </button>
      </div>

      {mutation.isError && (
        <div className="rounded-xl border border-signal-rose/20 bg-signal-rose/5 p-4 text-sm text-signal-rose">
          {(mutation.error as any)
            ?.response?.data
            ?.detail ||
            "Could not generate documentation."}
        </div>
      )}

      {!mutation.data &&
        !mutation.isPending && (
          <div className="rounded-2xl border border-dashed border-ink-700 bg-ink-900/40 px-6 py-12 text-center">
            <FileText className="mx-auto text-mist-500" />

            <h4 className="mt-4 font-display text-lg text-mist-100">
              No generated documentation yet
            </h4>

            <p className="mt-2 text-sm text-mist-400">
              Generate documentation to preview it here.
            </p>
          </div>
        )}

      <div className="space-y-4">
        {mutation.data?.map(
          (doc) => (
            <article
              key={doc.id}
              className="rounded-2xl border border-ink-700 bg-ink-900 p-5"
            >
              <h4 className="font-display text-lg font-semibold text-mist-100">
                {doc.title}
              </h4>

              <div className="mt-4 rounded-xl border border-ink-700 bg-ink-950 p-5">
                <p className="whitespace-pre-wrap text-sm leading-7 text-mist-300">
                  {doc.content}
                </p>
              </div>
            </article>
          )
        )}
      </div>
    </div>
  );
}

function ChatTab({
  repositoryId,
}: {
  repositoryId: string;
}) {
  const [
    message,
    setMessage,
  ] = useState("");

  const [
    sessionId,
    setSessionId,
  ] = useState<
    string | undefined
  >();

  const [
    chatHistory,
    setChatHistory,
  ] = useState<
    {
      role:
        | "user"
        | "assistant";
      content: string;
      refs?: string[];
    }[]
  >([]);

  const mutation = useMutation({
    mutationFn: (
      currentMessage: string
    ) =>
      chatWithRepository(
        repositoryId,
        currentMessage,
        sessionId
      ),

    onSuccess: (
      response
    ) => {
      setSessionId(
        response.data.session_id
      );

      setChatHistory(
        (currentHistory) => [
          ...currentHistory,
          {
            role: "assistant",
            content:
              response.data.answer,
            refs:
              response.data
                .referenced_files,
          },
        ]
      );
    },

    onError: (
      error: any
    ) => {
      setChatHistory(
        (currentHistory) => [
          ...currentHistory,
          {
            role: "assistant",
            content:
              error?.response?.data
                ?.detail ||
              "I could not answer that question.",
          },
        ]
      );
    },
  });

  const send = () => {
    const trimmed =
      message.trim();

    if (
      !trimmed ||
      mutation.isPending
    ) {
      return;
    }

    setChatHistory(
      (currentHistory) => [
        ...currentHistory,
        {
          role: "user",
          content: trimmed,
        },
      ]
    );

    mutation.mutate(
      trimmed
    );

    setMessage("");
  };

  const suggestions = [
    "Explain the project architecture.",
    "Where is authentication handled?",
    "What are the main security risks?",
    "Which files should have tests?",
  ];

  return (
    <div className="flex h-[70vh] flex-col overflow-hidden rounded-2xl border border-ink-700 bg-ink-900">
      <div className="border-b border-ink-700 p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-signal-teal/10 text-signal-teal">
            <MessageSquareCode
              size={19}
            />
          </div>

          <div>
            <h3 className="font-display text-lg font-semibold text-mist-100">
              Repository assistant
            </h3>

            <p className="text-xs text-mist-400">
              Ask questions using indexed repository context.
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {chatHistory.length ===
          0 && (
          <div>
            <p className="mb-3 text-sm text-mist-400">
              Try one of these questions:
            </p>

            <div className="flex flex-wrap gap-2">
              {suggestions.map(
                (suggestion) => (
                  <button
                    type="button"
                    key={suggestion}
                    onClick={() =>
                      setMessage(
                        suggestion
                      )
                    }
                    className="rounded-full border border-ink-700 px-3 py-2 text-xs text-mist-400 transition hover:border-signal-teal hover:text-signal-teal"
                  >
                    {suggestion}
                  </button>
                )
              )}
            </div>
          </div>
        )}

        {chatHistory.map(
          (
            historyItem,
            index
          ) => (
            <div
              key={`${historyItem.role}-${index}`}
              className={
                historyItem.role ===
                "user"
                  ? "text-right"
                  : "text-left"
              }
            >
              <div
                className={`inline-block max-w-[85%] rounded-2xl px-4 py-3 text-left text-sm leading-6 ${
                  historyItem.role ===
                  "user"
                    ? "bg-signal-amber text-ink-950"
                    : "border border-ink-700 bg-ink-800 text-mist-100"
                }`}
              >
                <p className="whitespace-pre-wrap">
                  {
                    historyItem.content
                  }
                </p>

                {historyItem.refs &&
                  historyItem.refs
                    .length >
                    0 && (
                    <div className="mt-3 border-t border-ink-600 pt-2">
                      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-mist-500">
                        Sources
                      </p>

                      <p className="font-mono text-xs text-mist-400">
                        {historyItem.refs.join(
                          ", "
                        )}
                      </p>
                    </div>
                  )}
              </div>
            </div>
          )
        )}

        {mutation.isPending && (
          <div className="flex items-center gap-2 text-sm text-mist-400">
            <Loader2
              size={15}
              className="animate-spin"
            />
            Analyzing repository context…
          </div>
        )}
      </div>

      <div className="border-t border-ink-700 p-4">
        <div className="flex gap-2">
          <input
            value={message}
            onChange={(
              event
            ) =>
              setMessage(
                event.target.value
              )
            }
            onKeyDown={(
              event
            ) => {
              if (
                event.key ===
                  "Enter" &&
                !event.shiftKey
              ) {
                event.preventDefault();
                send();
              }
            }}
            placeholder="Ask about this repository…"
            className="flex-1 rounded-xl border border-ink-700 bg-ink-800 px-4 py-3 text-sm text-mist-100 outline-none transition placeholder:text-mist-500 focus:border-signal-teal"
          />

          <button
            type="button"
            onClick={send}
            disabled={
              mutation.isPending ||
              !message.trim()
            }
            className="inline-flex items-center justify-center rounded-xl bg-signal-amber px-4 text-ink-950 transition hover:brightness-110 disabled:opacity-50"
          >
            <Send size={17} />
          </button>
        </div>
      </div>
    </div>
  );
}