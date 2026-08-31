# TEAMCHAT AI

Multi-tenant collaborative AI chat platform.

## Monorepo layout

```
teamchat-ai/
├── frontend/     React + TypeScript + Vite
├── backend/      FastAPI + Python
├── firebase/     Firebase config (added in later tasks)
├── scripts/      Dev and deploy scripts
└── docs/         Architecture and domain documentation
```

## Prerequisites

- Node.js 18+
- Python 3.11+
- pip

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check: `curl http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Fill in Firebase web app config values
npm run dev
```

Open the URL shown in the terminal (default `http://localhost:5173`).

Routes:
- `/login` — email/password sign in via Firebase Auth
- `/chat` — protected placeholder (requires authenticated session)

Local dev uses the Vite proxy for `/api` requests to the backend on port 8000.

### Tests

```bash
cd backend
pytest
```

## Seed dev data

Populate Firestore and Firebase Auth with two demo organizations (Acme Inc and Globex Corp), test users, rooms, and message history:

```bash
cd backend
source .venv/bin/activate

export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export FIREBASE_PROJECT_ID=your-firebase-project-id

python ../scripts/seed_dev_data.py
```

Test credentials and setup details: [docs/seed-credentials.md](docs/seed-credentials.md)

## Architecture notes

- Firestore is the durable source of truth.
- Realtime events (messages, typing, presence, AI streaming) are delivered via backend WebSockets — not client-side Firestore listeners.
- Initial data is loaded through REST APIs.
- `organizationId` is always derived server-side from the authenticated user.

See `docs/` for detailed architecture, data model, event definitions, [Cloud Run deployment](docs/cloud-run-deployment.md), and [Firebase Hosting deployment](docs/firebase-hosting-deployment.md).
