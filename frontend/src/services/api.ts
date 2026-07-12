import axios from "axios";
import { useAuthStore } from "../stores/useAuthStore";

import type {
  Analysis,
  GeneratedDocument,
  GeneratedTest,
  Issue,
  Repository,
  User,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();

      if (
        window.location.pathname !== "/auth" &&
        window.location.pathname !== "/auth/github/callback"
      ) {
        window.location.href = "/auth";
      }
    }

    return Promise.reject(error);
  }
);

// ---------- Auth ----------

export const signup = (
  email: string,
  password: string,
  full_name?: string
) =>
  api.post<{
    access_token: string;
    user: User;
  }>("/auth/signup", {
    email,
    password,
    full_name,
  });

export const login = (
  email: string,
  password: string
) =>
  api.post<{
    access_token: string;
    user: User;
  }>("/auth/login", {
    email,
    password,
  });

export const getMe = () =>
  api.get<User>("/auth/me");

export const exchangeGithubTicket = (
  ticket: string
) =>
  api.post<{
    access_token: string;
    user: User;
  }>("/auth/github/exchange", {
    ticket,
  });

// ---------- Repositories ----------

export const connectRepository = (
  clone_url: string,
  is_private = false,
  default_branch = "main"
) =>
  api.post<Repository>("/repositories/connect", {
    clone_url,
    is_private,
    default_branch,
  });

export const listRepositories = () =>
  api.get<Repository[]>("/repositories");

export const getRepository = (id: string) =>
  api.get<Repository>(`/repositories/${id}`);

// ---------- Analyses ----------

export const createAnalysis = (payload: {
  repository_id: string;
  branch: string;
  modules: string[];
}) =>
  api.post<{
    id: string;
    status: string;
    progress_percent: number;
  }>("/analyses", payload);

export const getAnalysisStatus = (
  id: string
) =>
  api.get<{
    id: string;
    status: string;
    progress_percent: number;
    error_message?: string | null;
  }>(`/analyses/${id}/status`);

export const getAnalysis = (id: string) =>
  api.get<Analysis>(`/analyses/${id}`);

export const getIssues = (
  id: string,
  filters?: Record<string, string>
) =>
  api.get<Issue[]>(`/analyses/${id}/issues`, {
    params: filters,
  });

export const updateIssue = (
  analysisId: string,
  issueId: string,
  status: string
) =>
  api.patch<Issue>(
    `/analyses/${analysisId}/issues/${issueId}`,
    { status }
  );

export const generateFix = (
  analysisId: string,
  issueId: string
) =>
  api.post(
    `/analyses/${analysisId}/generate-fix`,
    { issue_id: issueId }
  );

export const generateTests = (
  analysisId: string
) =>
  api.post<GeneratedTest[]>(
    `/analyses/${analysisId}/generate-tests`
  );

export const generateDocs = (
  analysisId: string
) =>
  api.post<GeneratedDocument[]>(
    `/analyses/${analysisId}/generate-docs`
  );

export const createPullRequest = (
  analysisId: string
) =>
  api.post<{
    pr_url: string;
    pr_number: number;
  }>(`/analyses/${analysisId}/create-pr`);

// ---------- Chat ----------

export const chatWithRepository = (
  repositoryId: string,
  message: string,
  sessionId?: string
) =>
  api.post<{
    session_id: string;
    answer: string;
    referenced_files: string[];
  }>(
    `/chat/${repositoryId}`,
    {
      message,
      session_id: sessionId,
    }
  );

// ---------- Reports ----------

export const downloadReport = async (
  analysisId: string,
  format: "pdf" | "md" | "json" | "csv" = "pdf"
) => {
  const response = await api.get(
    `/reports/${analysisId}`,
    {
      params: { format },
      responseType: "blob",
    }
  );

  const contentDisposition =
    response.headers["content-disposition"];

  let fileName =
    `reposage-report-${analysisId}.${format}`;

  const match = contentDisposition?.match(
    /filename="?([^"]+)"?/
  );

  if (match?.[1]) {
    fileName = match[1];
  }

  const blobUrl = window.URL.createObjectURL(
    response.data
  );

  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = fileName;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.URL.revokeObjectURL(blobUrl);
};

export default api;