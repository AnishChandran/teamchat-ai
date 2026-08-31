# Firebase Hosting Deployment

Deploy the TEAMCHAT AI React frontend to Firebase Hosting. Production uses **Firebase Hosting rewrites for REST** (`/api/**`) and a **direct Cloud Run URL for WebSockets** (`VITE_WS_URL`).

**Do not deploy until the backend is running on Cloud Run.** See [Cloud Run deployment](cloud-run-deployment.md).

---

## Architecture (recommended)

```
https://YOUR-PROJECT.web.app
├── /login, /chat, …     → frontend/dist (SPA, index.html fallback)
├── /api/**              → Cloud Run service teamchat-ai-backend (Hosting rewrite)
└── WebSocket chat       → wss://teamchat-ai-backend-….run.app/ws (direct; see below)
```

Firebase Hosting rewrites work for HTTP APIs but **do not reliably proxy WebSocket upgrades** to Cloud Run (connections fail with HTTP 404). Point `VITE_WS_URL` at your Cloud Run service URL instead.

With empty `VITE_API_URL`, REST calls stay same-origin via Hosting — no backend CORS changes required for `/api`.

---

## Prerequisites

1. [Firebase CLI](https://firebase.google.com/docs/cli) installed (`npm install -g firebase-tools`)
2. Firebase project with **Hosting** enabled
3. Cloud Run backend deployed as `teamchat-ai-backend` in `us-central1` (or update `firebase.json` rewrites)
4. Firebase **web app** registered (for client SDK config)
5. Firebase Auth **Authorized domains** includes:
   - `YOUR-PROJECT.web.app`
   - `YOUR-PROJECT.firebaseapp.com`
   - Any custom domain you add later

---

## Environment variables

Vite embeds `VITE_*` variables at **build time**. Rebuild after changing them.

| Variable | Dev (`.env`) | Production (`.env.production`) |
|----------|--------------|--------------------------------|
| `VITE_API_URL` | Empty (Vite proxy) | Empty (Hosting rewrite) **or** Cloud Run URL |
| `VITE_WS_URL` | Empty (Vite proxy) | **`wss://YOUR-SERVICE.run.app`** (required) |
| `VITE_FIREBASE_API_KEY` | From Firebase Console | Same |
| `VITE_FIREBASE_AUTH_DOMAIN` | From Firebase Console | Same |
| `VITE_FIREBASE_PROJECT_ID` | From Firebase Console | Same |
| `VITE_FIREBASE_APP_ID` | From Firebase Console | Same |

Copy templates:

```bash
cd teamchat-ai/frontend
cp .env.example .env              # local dev
cp .env.production.example .env.production   # production build
```

### Option A — Hosting rewrite for API + direct Cloud Run WebSocket (recommended)

Get your Cloud Run URL:

```bash
gcloud run services describe teamchat-ai-backend \
  --region us-central1 \
  --format='value(status.url)'
```

`.env.production`:

```env
VITE_API_URL=
VITE_WS_URL=wss://teamchat-ai-backend-PROJECT_NUMBER.us-central1.run.app
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_APP_ID=...
```

Requires `firebase.json` hosting rewrite for `/api/**` only. WebSockets connect directly to Cloud Run.

### Option B — Direct Cloud Run URLs for both API and WebSocket

```env
VITE_API_URL=https://teamchat-ai-backend-xxxxx-uc.a.run.app
VITE_WS_URL=wss://teamchat-ai-backend-xxxxx-uc.a.run.app
```

Requires CORS on the backend (not enabled by default). Prefer Option A.

---

## Firebase project setup

```bash
cd teamchat-ai
cp .firebaserc.example .firebaserc
# Edit .firebaserc — set your Firebase project ID

firebase login
firebase use your-firebase-project-id
```

Update rewrite targets in `teamchat-ai/firebase.json` if your Cloud Run service name or region differs:

```json
"run": {
  "serviceId": "teamchat-ai-backend",
  "region": "us-central1"
}
```

---

## Production build

```bash
cd teamchat-ai/frontend
npm ci

# Ensure .env.production is configured
npm run build:prod
# Output: frontend/dist/
```

Verify locally (optional):

```bash
npm run preview
# Note: preview does not apply Firebase Hosting rewrites; API/WS need backend running separately
```

---

## Deploy to Firebase Hosting

```bash
cd teamchat-ai/frontend
npm run build:prod

cd ..
firebase deploy --only hosting
```

Deploy hosting and Firestore rules together:

```bash
firebase deploy --only hosting,firestore:rules
```

---

## Verify deployment

1. Open `https://YOUR-PROJECT.web.app/login`
2. Sign in with a seeded user (see [seed-credentials.md](seed-credentials.md))
3. Confirm redirect to `/chat` and room list loads (`/api/rooms`)
4. Send a message — WebSocket should connect to `wss://YOUR-PROJECT.web.app/ws`
5. Refresh `/chat` — should not 404 (SPA rewrite)

Health check via rewrite:

```bash
curl https://YOUR-PROJECT.web.app/api/../health
# Prefer direct Cloud Run health check during backend setup
```

---

## SPA routing

React Router uses `BrowserRouter` with routes `/`, `/login`, `/chat`.

Firebase Hosting serves `index.html` for all non-file paths:

```json
{ "source": "**", "destination": "/index.html" }
```

API and WebSocket rewrites are listed **before** this catch-all.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 404 on `/chat` refresh | Confirm SPA rewrite exists and hosting was redeployed |
| API calls fail with CORS | Use Option A (empty `VITE_API_URL`) or add CORS to backend |
| WebSocket fails / “Connection lost. Reconnecting…” | Firebase Hosting cannot proxy WebSocket upgrades — set `VITE_WS_URL` to your Cloud Run `wss://…` URL, rebuild, and redeploy hosting |
| Auth `unauthorized-domain` | Add Hosting domain to Firebase Auth authorized domains |
| Blank page after deploy | Check browser console; verify `VITE_FIREBASE_*` were set at build time |
| Stale frontend | Rebuild after env changes; redeploy hosting |

---

## Security notes

- Never commit `.env.production` with secrets (Firebase web API keys are public by design; restrict with Auth domains + App Check if needed)
- Firestore client SDK is **not** used for chat data — rules still protect against direct Firestore access
- Backend authorization remains mandatory for all API/WebSocket operations
