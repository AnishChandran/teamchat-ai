# Cloud Run Deployment

Deploy the TEAMCHAT AI FastAPI backend to Google Cloud Run. This guide covers container build, IAM, environment configuration, and WebSocket considerations.

**Do not bake credentials into the Docker image.** Cloud Run provides [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/application-default-credentials) via the attached runtime service account.

The Firebase Admin SDK **bypasses Firestore security rules** at runtime. Backend authorization remains mandatory regardless of deployment target.

---

## Prerequisites

1. Google Cloud project with billing enabled
2. [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated
3. Firebase project linked to the same GCP project (or shared project ID)
4. Firestore in Native mode enabled
5. Firebase Authentication (Email/Password) enabled
6. APIs enabled:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com \
  aiplatform.googleapis.com
```

---

## Runtime service account permissions

Create a dedicated service account for the Cloud Run service (example name: `teamchat-ai-backend`).

| Capability | IAM role | Why |
|------------|----------|-----|
| Firestore read/write | `roles/datastore.user` | Organizations, users, rooms, messages |
| Firebase Auth token verification | `roles/firebaseauth.admin` | `auth.verify_id_token()` via Admin SDK |
| Vertex AI Gemini | `roles/aiplatform.user` | `@Gemini` / `@AI` streaming responses |

Example binding:

```bash
PROJECT_ID=your-gcp-project-id
SA=teamchat-ai-backend@${PROJECT_ID}.iam.gserviceaccount.com

gcloud iam service-accounts create teamchat-ai-backend \
  --display-name="TeamChat AI backend"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/firebaseauth.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user"
```

Use narrower custom roles in production if your security team requires least privilege beyond these defaults.

**Do not set `GOOGLE_APPLICATION_CREDENTIALS` on Cloud Run.** The attached service account supplies ADC automatically.

---

## Environment variables

Set these on the Cloud Run service (Console or `gcloud run deploy --set-env-vars`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Set by Cloud Run | `8080` | HTTP/WebSocket listen port |
| `FIREBASE_PROJECT_ID` | Yes | — | Firebase / Firestore project ID |
| `VERTEX_AI_PROJECT_ID` | No | `FIREBASE_PROJECT_ID` | Vertex AI billing project |
| `VERTEX_AI_LOCATION` | No | `us-central1` | Gemini region |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Model name |
| `GEMINI_MAX_RETRIES` | No | `3` | Retry count for transient Gemini errors |
| `GEMINI_RETRY_BASE_DELAY_SECONDS` | No | `0.5` | Base retry delay |
| `DEBUG` | No | `false` | Keep `false` in production |
| `APP_NAME` | No | `teamchat-ai` | FastAPI title |

Local development may use `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service-account JSON file. **Never copy that file into the Docker image.**

---

## Build the container

From the repository root:

```bash
cd teamchat-ai/backend

# Optional: build locally
docker build -t teamchat-ai-backend .

# Or submit to Cloud Build
PROJECT_ID=your-gcp-project-id
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/teamchat-ai-backend"
```

The Dockerfile:

- Installs production dependencies only (`requirements-prod.txt`)
- Runs as a non-root user
- Starts uvicorn with `--host 0.0.0.0 --port $PORT --workers 1`

---

## Deploy to Cloud Run

```bash
PROJECT_ID=your-gcp-project-id
REGION=us-central1
SA=teamchat-ai-backend@${PROJECT_ID}.iam.gserviceaccount.com

gcloud run deploy teamchat-ai-backend \
  --image "gcr.io/${PROJECT_ID}/teamchat-ai-backend" \
  --region "${REGION}" \
  --platform managed \
  --service-account "${SA}" \
  --set-env-vars "FIREBASE_PROJECT_ID=${PROJECT_ID},DEBUG=false,VERTEX_AI_LOCATION=${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 10
```

### WebSocket notes

- Cloud Run supports WebSockets on the same service URL (`wss://SERVICE_URL/ws?token=...`).
- The backend uses **one uvicorn worker** (`--workers 1`) because connection presence, typing, and dedup state are in-memory.
- Request timeout up to **3600s** supports long-lived WebSocket connections.
- If you scale beyond one instance, clients on different instances will not share realtime state. Mitigations:
  - `--min-instances 1` for small deployments, or
  - `--session-affinity` to improve sticky routing (optional), or
  - accept reconnect + REST message resync (frontend already reloads on reconnect).

Optional session affinity:

```bash
gcloud run services update teamchat-ai-backend \
  --region "${REGION}" \
  --session-affinity
```

---

## Verify deployment

```bash
SERVICE_URL=$(gcloud run services describe teamchat-ai-backend \
  --region "${REGION}" \
  --format='value(status.url)')

curl "${SERVICE_URL}/health"
# {"status":"ok"}
```

Test authenticated REST (requires a valid Firebase ID token):

```bash
curl -H "Authorization: Bearer ${ID_TOKEN}" "${SERVICE_URL}/api/me"
```

---

## Frontend configuration

Point the frontend at the Cloud Run service:

```env
VITE_API_URL=https://YOUR-SERVICE-URL
VITE_WS_URL=wss://YOUR-SERVICE-URL
```

If the frontend is hosted on a **different origin**, configure a reverse proxy or add CORS support separately. The current backend does not enable CORS middleware by default.

---

## Local Docker smoke test

```bash
cd teamchat-ai/backend
docker build -t teamchat-ai-backend .

docker run --rm -p 8080:8080 \
  -e FIREBASE_PROJECT_ID=your-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/key.json \
  -v /path/to/service-account.json:/secrets/key.json:ro \
  teamchat-ai-backend
```

For local smoke tests only, mount credentials with `-v`. Production Cloud Run relies on the attached service account instead.

---

## Security checklist

- [ ] `DEBUG=false` on Cloud Run
- [ ] No service-account JSON in the image or repo
- [ ] Dedicated runtime service account with minimal roles
- [ ] Firestore security rules deployed (`firebase deploy --only firestore:rules`)
- [ ] Firebase Auth custom claims (`organizationId`, `userId`) set for users
- [ ] Vertex AI API enabled in the deployment region
