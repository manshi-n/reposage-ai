export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
}

export interface Repository {
  id: string;
  name: string;
  full_name: string;
  clone_url: string;
  is_private: boolean;
  default_branch: string;
  created_at: string;
}

export type AnalysisStatusValue =
  | "pending"
  | "cloning"
  | "detecting_languages"
  | "running_static_analysis"
  | "building_index"
  | "running_ai_review"
  | "generating_report"
  | "complete"
  | "failed";

export interface Analysis {
  id: string;
  repository_id: string;

  repository_full_name?: string;
  repository_clone_url?: string;

  branch: string;
  status: AnalysisStatusValue;
  progress_percent: number;

  file_count?: number;
  lines_of_code?: number;
  languages?: string;
  architecture_summary?: string;

  overall_score?: number;
  security_score?: number;
  maintainability_score?: number;
  performance_score?: number;
  documentation_score?: number;
  testing_score?: number;
  architecture_score?: number;

  created_at: string;
  completed_at?: string;
}

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type IssueCategory =
  | "bug"
  | "security"
  | "performance"
  | "architecture"
  | "code_quality"
  | "documentation"
  | "testing";
export type IssueStatus = "open" | "resolved" | "false_positive";

export interface Issue {
  id: string;
  title: string;
  severity: Severity;
  category: IssueCategory;
  file_path: string;
  line_number?: number;
  language?: string;
  description?: string;
  risk?: string;
  suggested_fix?: string;
  generated_patch?: string;
  source_tool: string;
  status: IssueStatus;
}

export interface GeneratedTest {
  id: string;
  target_file: string;
  framework: string;
  file_name: string;
  content: string;
}

export interface GeneratedDocument {
  id: string;
  doc_type: string;
  title: string;
  content: string;
}
