import { useMemo, useState } from "react";
import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Copy,
  ExternalLink,
  FileCode2,
  Loader2,
  Search,
  ShieldAlert,
  Wand2,
  XCircle,
} from "lucide-react";

import {
  generateFix,
  updateIssue,
} from "../services/api";

import type {
  Issue,
  IssueCategory,
  Severity,
} from "../types";

const SEVERITY_STYLES: Record<
  Severity,
  {
    badge: string;
    border: string;
    icon: string;
  }
> = {
  critical: {
    badge:
      "border-red-500/30 bg-red-500/10 text-red-300",
    border: "border-l-red-500",
    icon: "text-red-400",
  },

  high: {
    badge:
      "border-orange-500/30 bg-orange-500/10 text-orange-300",
    border: "border-l-orange-500",
    icon: "text-orange-400",
  },

  medium: {
    badge:
      "border-amber-500/30 bg-amber-500/10 text-amber-300",
    border: "border-l-amber-500",
    icon: "text-amber-400",
  },

  low: {
    badge:
      "border-sky-500/30 bg-sky-500/10 text-sky-300",
    border: "border-l-sky-500",
    icon: "text-sky-400",
  },

  info: {
    badge:
      "border-slate-500/30 bg-slate-500/10 text-slate-300",
    border: "border-l-slate-500",
    icon: "text-slate-400",
  },
};

type IssueListProps = {
  analysisId: string;
  issues: Issue[];
  category?: IssueCategory;
  repositoryUrl?: string;
  branch?: string;
};

function buildGithubSourceUrl(
  repositoryUrl: string | undefined,
  branch: string,
  filePath: string,
  lineNumber?: number
): string | undefined {
  if (!repositoryUrl) {
    return undefined;
  }

  const cleanRepositoryUrl = repositoryUrl
    .trim()
    .replace(/\.git$/, "")
    .replace(/\/$/, "");

  const normalizedFilePath = filePath
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)
    .map((segment) =>
      encodeURIComponent(segment)
    )
    .join("/");

  if (!normalizedFilePath) {
    return undefined;
  }

  const encodedBranch =
    encodeURIComponent(branch || "main");

  const lineAnchor = lineNumber
    ? `#L${lineNumber}`
    : "";

  return (
    `${cleanRepositoryUrl}/blob/` +
    `${encodedBranch}/` +
    `${normalizedFilePath}` +
    `${lineAnchor}`
  );
}

export default function IssueList({
  analysisId,
  issues,
  category,
  repositoryUrl,
  branch = "main",
}: IssueListProps) {
  const [
    severityFilter,
    setSeverityFilter,
  ] = useState<string>("all");

  const [search, setSearch] =
    useState("");

  const [
    expandedIssue,
    setExpandedIssue,
  ] = useState<string | null>(
    null
  );

  const [
    copiedValue,
    setCopiedValue,
  ] = useState<string | null>(
    null
  );

  const [
    mutationError,
    setMutationError,
  ] = useState<string | null>(
    null
  );

  const queryClient =
    useQueryClient();

  const filtered = useMemo(
    () => {
      const normalizedSearch =
        search
          .trim()
          .toLowerCase();

      return issues.filter(
        (issue) => {
          if (
            category &&
            issue.category !== category
          ) {
            return false;
          }

          if (
            severityFilter !==
              "all" &&
            issue.severity !==
              severityFilter
          ) {
            return false;
          }

          if (!normalizedSearch) {
            return true;
          }

          const searchableValues = [
            issue.title,
            issue.description,
            issue.file_path,
            issue.category,
            issue.severity,
            issue.source_tool,
            issue.language,
            issue.status,
          ];

          return searchableValues
            .filter(Boolean)
            .some((value) =>
              String(value)
                .toLowerCase()
                .includes(
                  normalizedSearch
                )
            );
        }
      );
    },
    [
      issues,
      category,
      severityFilter,
      search,
    ]
  );

  const statusMutation =
    useMutation({
      mutationFn: ({
        issueId,
        status,
      }: {
        issueId: string;
        status: string;
      }) =>
        updateIssue(
          analysisId,
          issueId,
          status
        ),

      onMutate: () => {
        setMutationError(null);
      },

      onSuccess: async () => {
        await queryClient.invalidateQueries(
          {
            queryKey: [
              "issues",
              analysisId,
            ],
          }
        );
      },

      onError: (error: any) => {
        setMutationError(
          error?.response?.data
            ?.detail ||
            "Could not update the issue."
        );
      },
    });

  const fixMutation =
    useMutation({
      mutationFn: (
        issueId: string
      ) =>
        generateFix(
          analysisId,
          issueId
        ),

      onMutate: () => {
        setMutationError(null);
      },

      onSuccess: async () => {
        await queryClient.invalidateQueries(
          {
            queryKey: [
              "issues",
              analysisId,
            ],
          }
        );
      },

      onError: (error: any) => {
        setMutationError(
          error?.response?.data
            ?.detail ||
            "Could not generate a fix."
        );
      },
    });

  const copyText = async (
    key: string,
    text: string
  ) => {
    try {
      await navigator.clipboard.writeText(
        text
      );

      setCopiedValue(key);

      window.setTimeout(() => {
        setCopiedValue(null);
      }, 1600);
    } catch {
      setMutationError(
        "Could not copy text to the clipboard."
      );
    }
  };

  if (issues.length === 0) {
    return (
      <div className="rounded-2xl border border-signal-teal/20 bg-signal-teal/5 px-6 py-12 text-center">
        <CheckCircle2 className="mx-auto mb-3 text-signal-teal" />

        <h3 className="font-display text-lg font-semibold text-mist-100">
          No issues found
        </h3>

        <p className="mt-2 text-sm text-mist-400">
          No findings were detected
          in this category.
        </p>
      </div>
    );
  }

  return (
    <section>
      <div className="mb-5 flex flex-col gap-3 rounded-2xl border border-ink-700 bg-ink-900 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:max-w-sm">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-mist-500"
          />

          <input
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            placeholder="Search issues or files"
            className="w-full rounded-xl border border-ink-700 bg-ink-950 py-2.5 pl-9 pr-3 text-sm text-mist-100 outline-none transition placeholder:text-mist-500 focus:border-signal-teal"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            "all",
            "critical",
            "high",
            "medium",
            "low",
            "info",
          ].map((severity) => (
            <button
              type="button"
              key={severity}
              onClick={() =>
                setSeverityFilter(
                  severity
                )
              }
              className={`rounded-lg border px-3 py-2 text-xs capitalize transition ${
                severityFilter ===
                severity
                  ? "border-signal-teal bg-signal-teal/10 text-signal-teal"
                  : "border-ink-700 text-mist-400 hover:border-ink-600 hover:text-mist-200"
              }`}
            >
              {severity}
            </button>
          ))}
        </div>
      </div>

      {mutationError && (
        <div className="mb-4 rounded-xl border border-signal-rose/25 bg-signal-rose/5 px-4 py-3 text-sm text-signal-rose">
          {mutationError}
        </div>
      )}

      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-mist-400">
          {filtered.length} finding
          {filtered.length === 1
            ? ""
            : "s"}
        </p>
      </div>

      {filtered.length === 0 && (
        <div className="rounded-2xl border border-dashed border-ink-700 bg-ink-900/50 px-6 py-10 text-center">
          <Search className="mx-auto mb-3 text-mist-500" />

          <h3 className="font-display text-base font-semibold text-mist-100">
            No matching findings
          </h3>

          <p className="mt-2 text-sm text-mist-400">
            Change the severity filter
            or search query.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {filtered.map(
          (issue) => {
            const styles =
              SEVERITY_STYLES[
                issue.severity
              ];

            const expanded =
              expandedIssue ===
              issue.id;

            const githubSourceUrl =
              buildGithubSourceUrl(
                repositoryUrl,
                branch,
                issue.file_path,
                issue.line_number
              );

            const isGeneratingFix =
              fixMutation.isPending &&
              fixMutation.variables ===
                issue.id;

            const isUpdatingStatus =
              statusMutation.isPending &&
              statusMutation.variables
                ?.issueId === issue.id;

            return (
              <article
                key={issue.id}
                className={`rounded-2xl border border-l-4 border-ink-700 bg-ink-900 transition hover:border-ink-600 ${styles.border}`}
              >
                <button
                  type="button"
                  onClick={() =>
                    setExpandedIssue(
                      expanded
                        ? null
                        : issue.id
                    )
                  }
                  className="flex w-full items-start gap-4 p-5 text-left"
                >
                  <div
                    className={`mt-0.5 shrink-0 ${styles.icon}`}
                  >
                    {issue.category ===
                    "security" ? (
                      <ShieldAlert
                        size={19}
                      />
                    ) : (
                      <CircleAlert
                        size={19}
                      />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${styles.badge}`}
                      >
                        {
                          issue.severity
                        }
                      </span>

                      <span className="rounded-full bg-ink-800 px-2.5 py-1 text-[10px] capitalize text-mist-400">
                        {issue.category.replace(
                          "_",
                          " "
                        )}
                      </span>

                      {issue.language && (
                        <span className="rounded-full bg-ink-950 px-2.5 py-1 text-[10px] text-mist-400">
                          {
                            issue.language
                          }
                        </span>
                      )}

                      {issue.source_tool && (
                        <span className="text-[10px] text-mist-500">
                          {
                            issue.source_tool
                          }
                        </span>
                      )}
                    </div>

                    <h3 className="font-medium text-mist-100">
                      {issue.title}
                    </h3>

                    <div className="mt-2 flex items-center gap-2 font-mono text-xs text-mist-400">
                      <FileCode2
                        size={13}
                      />

                      <span className="truncate">
                        {
                          issue.file_path
                        }

                        {issue.line_number
                          ? `:${issue.line_number}`
                          : ""}
                      </span>
                    </div>
                  </div>

                  <div className="text-mist-500">
                    {expanded ? (
                      <ChevronUp
                        size={18}
                      />
                    ) : (
                      <ChevronDown
                        size={18}
                      />
                    )}
                  </div>
                </button>

                {expanded && (
                  <div className="border-t border-ink-700 px-5 pb-5 pt-4">
                    {issue.description && (
                      <div className="mb-4">
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-mist-500">
                          Explanation
                        </p>

                        <p className="text-sm leading-relaxed text-mist-300">
                          {
                            issue.description
                          }
                        </p>
                      </div>
                    )}

                    {issue.risk && (
                      <div className="mb-4 rounded-xl border border-signal-rose/20 bg-signal-rose/5 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-signal-rose">
                          Risk
                        </p>

                        <p className="mt-1 text-sm text-mist-300">
                          {
                            issue.risk
                          }
                        </p>
                      </div>
                    )}

                    {issue.suggested_fix && (
                      <div className="mb-4 rounded-xl border border-signal-teal/20 bg-signal-teal/5 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-xs font-semibold uppercase tracking-wide text-signal-teal">
                              Suggested fix
                            </p>

                            <p className="mt-1 whitespace-pre-wrap text-sm text-mist-300">
                              {
                                issue.suggested_fix
                              }
                            </p>
                          </div>

                          <button
                            type="button"
                            onClick={() =>
                              copyText(
                                `suggestion-${issue.id}`,
                                issue.suggested_fix ??
                                  ""
                              )
                            }
                            className="shrink-0 text-mist-500 transition hover:text-mist-100"
                            title="Copy suggestion"
                          >
                            {copiedValue ===
                            `suggestion-${issue.id}` ? (
                              <Check
                                size={15}
                              />
                            ) : (
                              <Copy
                                size={15}
                              />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {issue.generated_patch && (
                      <div className="mb-4">
                        <div className="mb-2 flex items-center justify-between">
                          <p className="text-xs font-semibold uppercase tracking-wide text-mist-500">
                            Generated patch
                          </p>

                          <button
                            type="button"
                            onClick={() =>
                              copyText(
                                `patch-${issue.id}`,
                                issue.generated_patch ??
                                  ""
                              )
                            }
                            className="text-mist-500 transition hover:text-mist-100"
                            title="Copy generated patch"
                          >
                            {copiedValue ===
                            `patch-${issue.id}` ? (
                              <Check
                                size={15}
                              />
                            ) : (
                              <Copy
                                size={15}
                              />
                            )}
                          </button>
                        </div>

                        <pre className="max-h-96 overflow-auto whitespace-pre rounded-xl border border-ink-700 bg-ink-950 p-4 font-mono text-xs leading-6 text-mist-200">
                          {
                            issue.generated_patch
                          }
                        </pre>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          fixMutation.mutate(
                            issue.id
                          )
                        }
                        disabled={
                          isGeneratingFix ||
                          isUpdatingStatus
                        }
                        className="inline-flex items-center gap-2 rounded-lg bg-signal-amber px-3 py-2 text-xs font-medium text-ink-950 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isGeneratingFix ? (
                          <Loader2
                            size={14}
                            className="animate-spin"
                          />
                        ) : (
                          <Wand2
                            size={14}
                          />
                        )}

                        {isGeneratingFix
                          ? "Generating…"
                          : issue.generated_patch
                          ? "Regenerate fix"
                          : "Generate fix"}
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          statusMutation.mutate(
                            {
                              issueId:
                                issue.id,
                              status:
                                "resolved",
                            }
                          )
                        }
                        disabled={
                          isUpdatingStatus ||
                          issue.status ===
                            "resolved"
                        }
                        className="inline-flex items-center gap-2 rounded-lg border border-ink-700 px-3 py-2 text-xs text-mist-300 transition hover:border-signal-teal hover:text-signal-teal disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isUpdatingStatus ? (
                          <Loader2
                            size={14}
                            className="animate-spin"
                          />
                        ) : (
                          <CheckCircle2
                            size={14}
                          />
                        )}

                        Resolve
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          statusMutation.mutate(
                            {
                              issueId:
                                issue.id,
                              status:
                                "false_positive",
                            }
                          )
                        }
                        disabled={
                          isUpdatingStatus ||
                          issue.status ===
                            "false_positive"
                        }
                        className="inline-flex items-center gap-2 rounded-lg border border-ink-700 px-3 py-2 text-xs text-mist-300 transition hover:border-signal-rose hover:text-signal-rose disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <XCircle
                          size={14}
                        />

                        False positive
                      </button>

                      {githubSourceUrl ? (
                        <a
                          href={
                            githubSourceUrl
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="ml-auto inline-flex items-center gap-2 text-xs text-mist-400 transition hover:text-mist-100"
                        >
                          <ExternalLink
                            size={14}
                          />
                          Open source
                        </a>
                      ) : (
                        <span
                          className="ml-auto inline-flex cursor-not-allowed items-center gap-2 text-xs text-mist-600"
                          title="Repository URL is unavailable"
                        >
                          <ExternalLink
                            size={14}
                          />
                          Open source
                        </span>
                      )}
                    </div>

                    {issue.status !==
                      "open" && (
                      <p className="mt-4 text-xs italic text-mist-500">
                        Marked as{" "}
                        {issue.status.replace(
                          "_",
                          " "
                        )}
                      </p>
                    )}
                  </div>
                )}
              </article>
            );
          }
        )}
      </div>
    </section>
  );
}