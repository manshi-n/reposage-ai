import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  FolderGit2,
  GitBranch,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { listRepositories } from "../services/api";

export default function Dashboard() {
  const {
    data: repos,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["repositories"],
    queryFn: () =>
      listRepositories().then(
        (response) => response.data
      ),
  });

  const repositoryCount =
    repos?.length ?? 0;

  const privateCount =
    repos?.filter(
      (repository) => repository.is_private
    ).length ?? 0;

  return (
    <main className="mx-auto max-w-7xl p-5 md:p-8">
      <section className="mb-8 overflow-hidden rounded-3xl border border-ink-700 bg-gradient-to-br from-ink-900 via-ink-900 to-ink-800 p-6 md:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-signal-teal/30 bg-signal-teal/10 px-3 py-1 text-xs text-signal-teal">
              <Sparkles size={13} />
              AI-powered code intelligence
            </div>

            <h1 className="font-display text-3xl font-semibold text-mist-100 md:text-4xl">
              Repository dashboard
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mist-400 md:text-base">
              Connect a GitHub repository, inspect its
              architecture, identify code risks, generate
              tests and documentation, and ask questions
              about the codebase.
            </p>
          </div>

          <Link
            to="/analyses/new"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-signal-amber px-5 py-3 text-sm font-semibold text-ink-950 transition hover:brightness-110"
          >
            <Plus size={17} />
            Start new analysis
          </Link>
        </div>
      </section>

      <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryCard
          icon={<FolderGit2 size={19} />}
          label="Connected repositories"
          value={repositoryCount}
          description="Repositories available for analysis"
        />

        <SummaryCard
          icon={<Lock size={19} />}
          label="Private repositories"
          value={privateCount}
          description="Connected through GitHub OAuth"
        />

        <SummaryCard
          icon={<ShieldCheck size={19} />}
          label="Analysis engine"
          value="Online"
          description="Static analysis, RAG and Groq AI"
        />
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold text-mist-100">
              Your repositories
            </h2>

            <p className="mt-1 text-sm text-mist-400">
              Choose a repository and run a new code review.
            </p>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 rounded-lg border border-ink-700 px-3 py-2 text-xs text-mist-300 transition hover:border-ink-600 hover:text-mist-100"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-40 animate-pulse rounded-2xl border border-ink-700 bg-ink-900"
              />
            ))}
          </div>
        )}

        {isError && (
          <div className="rounded-2xl border border-signal-rose/30 bg-signal-rose/10 p-6 text-center">
            <p className="text-sm text-signal-rose">
              Could not load repositories.
            </p>

            <button
              onClick={() => refetch()}
              className="mt-3 text-sm text-mist-100 underline"
            >
              Try again
            </button>
          </div>
        )}

        {!isLoading &&
          !isError &&
          (!repos || repos.length === 0) && (
            <div className="rounded-3xl border border-dashed border-ink-700 bg-ink-900/50 px-6 py-14 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-ink-800 text-mist-300">
                <FolderGit2 size={25} />
              </div>

              <h3 className="font-display text-lg font-semibold text-mist-100">
                No repositories connected
              </h3>

              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-mist-400">
                Connect a public GitHub repository or sign
                in with GitHub to analyze private repositories.
              </p>

              <Link
                to="/analyses/new"
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-signal-amber px-4 py-2.5 text-sm font-medium text-ink-950"
              >
                Connect first repository
                <ArrowRight size={15} />
              </Link>
            </div>
          )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {repos?.map((repo) => (
            <article
              key={repo.id}
              className="group rounded-2xl border border-ink-700 bg-ink-900 p-5 transition hover:-translate-y-0.5 hover:border-ink-600 hover:shadow-xl hover:shadow-black/10"
            >
              <div className="mb-5 flex items-start justify-between gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-800 text-signal-teal">
                  <FolderGit2 size={19} />
                </div>

                <span
                  className={`rounded-full px-2.5 py-1 text-[11px] ${
                    repo.is_private
                      ? "bg-signal-amber/10 text-signal-amber"
                      : "bg-signal-teal/10 text-signal-teal"
                  }`}
                >
                  {repo.is_private
                    ? "Private"
                    : "Public"}
                </span>
              </div>

              <h3 className="truncate font-mono text-sm font-medium text-mist-100">
                {repo.full_name}
              </h3>

              <div className="mt-3 flex items-center gap-2 text-xs text-mist-400">
                <GitBranch size={14} />
                {repo.default_branch}
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-ink-700 pt-4">
                <span className="text-xs text-mist-500">
                  Ready to analyze
                </span>

                <Link
                  to="/analyses/new"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-signal-teal transition group-hover:gap-2"
                >
                  Analyze
                  <ArrowRight size={15} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  description,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-900 p-5">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-ink-800 text-signal-teal">
        {icon}
      </div>

      <p className="text-xs uppercase tracking-wide text-mist-500">
        {label}
      </p>

      <p className="mt-2 font-display text-2xl font-semibold text-mist-100">
        {value}
      </p>

      <p className="mt-1 text-xs text-mist-400">
        {description}
      </p>
    </div>
  );
}