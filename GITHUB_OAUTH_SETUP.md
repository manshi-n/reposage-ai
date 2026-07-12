# GitHub OAuth setup for RepoSage AI

## 1. Create a GitHub OAuth App

GitHub → Settings → Developer settings → OAuth Apps → New OAuth App

Use these local-development values:

- Application name: `RepoSage AI Local`
- Homepage URL: `http://localhost:5173`
- Authorization callback URL: `http://localhost:8000/api/v1/auth/github/callback`

Copy the Client ID and generate a Client Secret.

## 2. Create backend configuration

From the project root in PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Edit `backend/.env` and set:

```env
GITHUB_CLIENT_ID=<your client id>
GITHUB_CLIENT_SECRET=<your client secret>
JWT_SECRET_KEY=<first generated value>
TOKEN_ENCRYPTION_KEY=<second generated value>
```

Keep these callback values unchanged for local development:

```env
GITHUB_OAUTH_CALLBACK_URL=http://localhost:8000/api/v1/auth/github/callback
GITHUB_FRONTEND_CALLBACK_URL=http://localhost:5173/auth/github/callback
```

## 3. Create frontend configuration

```powershell
Copy-Item frontend\.env.example frontend\.env
```

Its content should be:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## 4. Start infrastructure

```powershell
docker compose up -d postgres redis
docker compose ps
```

## 5. Start backend

```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend docs: `http://localhost:8000/docs`

## 6. Start frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## 7. Test the login

Open `http://localhost:5173/auth` and click **Continue with GitHub**.

Expected flow:

1. Browser opens GitHub authorization.
2. GitHub redirects to the FastAPI callback.
3. FastAPI validates OAuth state and exchanges the code.
4. The GitHub token is encrypted before database storage.
5. FastAPI creates a single-use Redis login ticket.
6. React exchanges the ticket for the RepoSage JWT.
7. The user reaches `/dashboard` and remains logged in after refresh.

## Common errors

### `GitHub OAuth is not configured`

`GITHUB_CLIENT_ID` or `GITHUB_CLIENT_SECRET` is empty in `backend/.env`.

### `Invalid or expired GitHub OAuth state`

Restart the flow from `/auth`. Do not reuse an old callback URL.

### `Login session service is unavailable`

Redis is not running. Run:

```powershell
docker compose up -d redis
```

### GitHub callback mismatch

The callback configured in GitHub must exactly equal:

`http://localhost:8000/api/v1/auth/github/callback`
