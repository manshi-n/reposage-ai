"""
Language-agnostic security scanner.

Bandit/ESLint/Semgrep cover Python and JS well, but they require those
toolchains to be installed and only cover their own language. This module
is a dependency-free regex pass that runs over *every* text file in the
repo and catches the highest-value, language-agnostic findings: hard-coded
secrets, obvious SQL/command injection patterns, unsafe eval, and exposed
private keys. It's intentionally conservative to keep false positives low,
and always available even when heavier tools (Semgrep/Trivy/Gitleaks)
aren't installed in this environment.
"""
import os
import re
from typing import Any, Dict, List

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".next", "target", "vendor",
}

MAX_FILE_BYTES = 2_000_000  # skip huge/binary-ish files

PATTERNS = [
    {
        "name": "Hard-coded secret / API key",
        "regex": re.compile(
            r"(?i)(secret|api[_-]?key|token|password|passwd)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{8,}['\"]"
        ),
        "severity": "critical",
        "category": "security",
        "risk": "Anyone with repository access can read and reuse this credential.",
        "suggested_fix": "Move the value to an environment variable or a secret manager, and rotate the credential.",
    },
    {
        "name": "Private key committed to repository",
        "regex": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
        "severity": "critical",
        "category": "security",
        "risk": "A committed private key allows full impersonation of the key's owner.",
        "suggested_fix": "Remove the key from git history, rotate it immediately, and store it in a secret manager.",
    },
    {
        "name": "Potential SQL injection (string-built query)",
        "regex": re.compile(
            r"(execute|query)\s*\(\s*['\"].*%s.*['\"]\s*%|"
            r"(execute|query)\s*\(\s*f['\"].*\{.*\}.*(select|insert|update|delete)",
            re.IGNORECASE,
        ),
        "severity": "critical",
        "category": "security",
        "risk": "User input concatenated into SQL allows attackers to read or modify arbitrary data.",
        "suggested_fix": "Use parameterized queries / prepared statements instead of string interpolation.",
    },
    {
        "name": "Use of unsafe eval",
        "regex": re.compile(r"\beval\s*\("),
        "severity": "high",
        "category": "security",
        "risk": "eval() on untrusted input allows arbitrary code execution.",
        "suggested_fix": "Avoid eval(); use a safe parser (e.g. JSON.parse) or an explicit allow-list of operations.",
    },
    {
        "name": "Shell command built from untrusted input",
        "regex": re.compile(r"(?i)(os\.system|subprocess\.(call|run|Popen))\([^)]*\+"),
        "severity": "high",
        "category": "security",
        "risk": "Concatenating input into a shell command enables command injection.",
        "suggested_fix": "Use subprocess with a list of arguments (no shell=True) instead of string concatenation.",
    },
    {
        "name": "Permissive CORS configuration",
        "regex": re.compile(r"(?i)Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"]\*['\"]"),
        "severity": "medium",
        "category": "security",
        "risk": "Wildcard CORS allows any website to make authenticated requests to this API.",
        "suggested_fix": "Restrict Access-Control-Allow-Origin to an explicit allow-list of trusted origins.",
    },
]

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php", ".cs",
    ".cpp", ".c", ".rs", ".yml", ".yaml", ".env", ".json", ".config", ".txt",
}


def scan_for_security_patterns(repo_path: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in TEXT_EXTENSIONS and fname != ".env":
                continue

            full_path = os.path.join(root, fname)
            try:
                if os.path.getsize(full_path) > MAX_FILE_BYTES:
                    continue
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
            except OSError:
                continue

            rel_path = os.path.relpath(full_path, repo_path)
            for lineno, line in enumerate(lines, start=1):
                for pattern in PATTERNS:
                    if pattern["regex"].search(line):
                        issues.append({
                            "title": pattern["name"],
                            "severity": pattern["severity"],
                            "category": pattern["category"],
                            "file_path": rel_path,
                            "line_number": lineno,
                            "language": None,
                            "description": f"Pattern-matched: {pattern['name']} in {rel_path}:{lineno}",
                            "risk": pattern["risk"],
                            "suggested_fix": pattern["suggested_fix"],
                            "generated_patch": None,
                            "source_tool": "reposage-pattern-scanner",
                        })
    return issues
