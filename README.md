# RepoSage AI

AI-powered GitHub repository analysis platform that combines static analysis with LLM-powered code review to identify security vulnerabilities, performance issues, code quality problems, architecture insights, documentation, automated test generation, repository chat, and AI-generated pull requests.

Developed by **Manshi **

GitHub: https://github.com/manshi-n

---

## Features

- Analyze public and private GitHub repositories
- Automatic language and framework detection
- Security analysis
  - Bandit (Python)
  - npm audit (JavaScript/TypeScript)
  - Regex-based multi-language security scanning
- Code quality analysis
- Performance analysis
- Architecture analysis using AI
- Documentation generation
- Test generation
- AI-generated code fixes
- Automatic GitHub Pull Request creation
- Repository-aware AI chat
- Repository health scoring
- Export reports in:
  - PDF
  - Markdown
  - HTML
  - JSON
  - CSV

---

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- React Query
- Axios

### Backend

- FastAPI
- SQLAlchemy
- Celery
- Redis
- PostgreSQL
- ChromaDB
- GitPython

### AI

- Anthropic Claude
- Repository-aware RAG
- Specialized AI agents
- LLM-powered documentation
- AI test generation
- AI refactoring suggestions

### Static Analysis

- Bandit
- Ruff
- ESLint
- npm audit
- Custom HTML/CSS/JavaScript analyzers
- PHP analyzer
- Dependency scanner

---

# Project Structure

```
reposage-ai/
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── stores/
│
├── backend/
│   └── app/
│       ├── agents/
│       ├── analyzers/
│       ├── api/
│       ├── models/
│       ├── parsers/
│       ├── services/
│       ├── workers/
│       └── utils/
│
├── docker/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/manshi-n/reposage-ai.git

cd reposage-ai
```

---

## Backend

```bash
cd backend

python -m venv venv

source venv/bin/activate

# Windows

venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
```

Backend runs on

```
http://localhost:8000
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend runs on

```
http://localhost:5173
```

---

## Docker

```bash
cp .env.example .env

docker compose up --build
```

---

# Environment Variables

Create a `.env` file.

```
ANTHROPIC_API_KEY=

GITHUB_CLIENT_ID=

GITHUB_CLIENT_SECRET=

DATABASE_URL=

REDIS_URL=

JWT_SECRET_KEY=
```

If AI credentials are not configured, static analysis continues to work while AI-generated content is disabled gracefully.

---

# GitHub OAuth

Before using **Continue with GitHub**, complete the setup described in

```
GITHUB_OAUTH_SETUP.md
```

OAuth flow includes

- State validation
- Encrypted GitHub token storage
- Single-use Redis login tickets
- Secure backend callback

---

# Security

RepoSage protects the analysis environment by

- HTTPS-only repository cloning
- SSRF protection
- Repository size limits
- File size limits
- File count limits
- Symlink rejection
- Temporary clone cleanup after analysis

Repository code is **never executed**.

Only static analysis tools inspect source files.

---

# Reports

RepoSage generates

- Repository Health Score
- Security Report
- Code Quality Report
- Performance Report
- Architecture Report
- Documentation
- Generated Tests
- Dependency Report
- Repository Chat

Reports can be downloaded as

- PDF
- HTML
- Markdown
- JSON
- CSV

---

# Pull Requests

RepoSage can

- Generate AI code fixes
- Create a dedicated GitHub branch
- Commit validated generated fixes
- Open a Draft Pull Request automatically
- Include AI-generated explanations inside the PR

Generated patches are validated before committing.

---

# Future Improvements

- Tree-sitter based parsing
- Better semantic code embeddings
- Additional language analyzers
- Incremental repository indexing
- CI/CD integration
- Multi-repository workspaces

---

# Author

**Manshi **

GitHub

https://github.com/manshi-n



---

# License

MIT License
