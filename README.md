# Cortex

A production-ready AI-powered e‑commerce operations and growth assistant. The application provides a conversational interface and financial insights, with clean Markdown rendering for readable outputs.

- Official URL: https://cortex-projects.vercel.app
- Frontend: Next.js (App Router) in `Cortex/`
- Backend: Flask in `openai_purelybackend/`
- Deployments: Vercel (frontend), Render (backend)

## Architecture

- Frontend
  - Framework: Next.js
  - Server routes proxy to the backend using `process.env.BACKEND_BASE_URL`
  - Key routes:
    - Chat API: `Cortex/src/app/ai/chatbot/route.ts`
    - Generic proxy: `Cortex/src/app/api/[...path]/route.ts`
  - Markdown rendering via `react-markdown` and `remark-gfm` in UI pages

- Backend
  - Framework: Flask
  - Health endpoint: `GET /api/health`
  - Chat handler: `POST /ai/chatbot`
  - Production served with `gunicorn` on Render

- Configuration
  - Frontend env: `BACKEND_BASE_URL`
  - Backend env: `GEMINI_API_KEY` (managed as a Render Secret), `PORT`, `HOST`, `FLASK_DEBUG`

## Features

- Conversational assistant with Markdown-formatted responses
- Financial insights page with Markdown formatting
- Environment-driven proxy between frontend and backend
- Health checks and production server configuration

## Getting Started

### Prerequisites

- Node.js 18+
- npm
- Python 3.10+
- pip

### Backend (local)

```bash
cd openai_purelybackend
pip install -r requirements.txt
# Run in development
PORT=5001 HOST=0.0.0.0 FLASK_DEBUG=True python3 app.py
# Or run via gunicorn
# gunicorn app:app --workers 1 --threads 8 --timeout 90
```

- Verify health:

```bash
curl http://127.0.0.1:5001/api/health
```

### Frontend (local)

```bash
cd Cortex
npm install
# Configure backend URL for local proxy
printf "BACKEND_BASE_URL=http://127.0.0.1:5001\n" > .env.local
npm run dev
```

- Open `http://localhost:3000`
- Test chat route:

```bash
curl -X POST http://localhost:3000/ai/chatbot \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello"}'
```

## Deployment

### Backend (Render)

- Blueprint file: `render.yaml` (root)
- Recommended: create the service via the Render Dashboard
  - New → Blueprint → connect repository
  - Ensure service config:
    - Type: Web, Env: `python`
    - Root: `openai_purelybackend`
    - Build: `pip install -r requirements.txt`
    - Start: `gunicorn app:app --workers 1 --threads 8 --timeout 90`
    - Health Check Path: `/api/health`
    - Secrets: add `gemini_api_key` → `GEMINI_API_KEY`

- CLI management (after service exists):

```bash
# Install the official Render CLI (v2+)
brew tap render-oss/render && brew install render
# Set workspace interactively
render workspace set
# List services
render services list --output json
# Trigger a deploy
render deploys create --service <service-id> --output text
```

### Frontend (Vercel)

- Production env configured in `Cortex/vercel.json`:

```json
{
  "env": {
    "BACKEND_BASE_URL": "https://cortex-v2ee.onrender.com"
  }
}
```

- Deploy via CLI:

```bash
cd Cortex
vercel --prod --yes
```

- Alias the deployment to the official URL:

```bash
vercel alias set <deployment>.vercel.app cortex-projects.vercel.app
```

## Environment Variables

- Frontend
  - `BACKEND_BASE_URL`: Base URL for backend API (example: `https://cortex-v2ee.onrender.com`)

- Backend
  - `GEMINI_API_KEY`: API key for model integration (set as a Render Secret)
  - `PORT`: Server port (example: `5001`)
  - `HOST`: Bind address (example: `0.0.0.0`)
  - `FLASK_DEBUG`: `True` or `False`

## Project Structure

```
CORTEX/
├─ Cortex/                   # Next.js frontend
│  ├─ src/app/               # App Router pages and routes
│  ├─ next.config.ts         # Next.js configuration
│  ├─ vercel.json            # Vercel environment configuration
│  └─ .env.local             # Local env (not committed)
├─ openai_purelybackend/     # Flask backend
│  ├─ app.py                 # Flask app entry
│  └─ requirements.txt       # Python dependencies
├─ render.yaml               # Render blueprint for backend service
└─ README.md                 # Project documentation
```

## Troubleshooting

- Vercel build error `ENOENT: ... .next/routes-manifest.json`
  - Cause: customized `outputFileTracingRoot` breaks Next.js path resolution on Vercel
  - Fix: remove `outputFileTracingRoot` from `Cortex/next.config.ts`

- "Error contacting AI backend" in frontend
  - Ensure `Cortex/.env.local` has `BACKEND_BASE_URL` set to the correct backend URL
  - Restart the dev server after changing envs

- Port conflicts on local
  - Use `PORT=5001` for backend and configure the frontend to match

## Security

- Do not commit secrets; use Render Secrets for `GEMINI_API_KEY`
- Keep `.env.local` untracked in Git (already configured in `.gitignore`)

## License

This project’s license is not set. Add a license file if needed.
