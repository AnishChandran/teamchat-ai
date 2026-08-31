# Firebase

Firebase configuration for TEAMCHAT AI (Hosting, Auth client config, Firestore rules).

## Hosting

The React app builds to `frontend/dist/` and is deployed via Firebase Hosting.

- **SPA routing:** all routes fall back to `index.html`
- **API rewrite:** `/api/**` → Cloud Run `teamchat-ai-backend`
- **WebSocket rewrite:** `/ws` → Cloud Run (same service)

See [Firebase Hosting deployment](../docs/firebase-hosting-deployment.md) for build and deploy commands.

## Firestore security rules

Rules live in `firestore.rules`. See [Firestore security](../docs/firestore-security.md) for assumptions, Admin SDK behavior, and recommended emulator test cases.

**Important:** The backend uses the Firebase Admin SDK, which **bypasses** Firestore rules. Backend authorization must remain in place.

## Project setup

Firebase CLI must run from **`teamchat-ai/`** (repo app root), not this folder. The root `firebase.json` points at `frontend/dist` and `firebase/firestore.rules`.

```bash
cd teamchat-ai
cp .firebaserc.example .firebaserc   # set your project ID
firebase login
firebase use your-firebase-project-id
```

## Deploy

```bash
cd teamchat-ai/frontend
cp .env.production.example .env.production   # configure Firebase web app keys
npm ci
npm run build:prod

cd ..
firebase deploy --only hosting
firebase deploy --only firestore:rules   # optional
```

## Custom claims

Seed script sets Auth custom claims on each user:

```json
{ "organizationId": "acme", "userId": "sarah" }
```

Both are required for Firestore read rules (org + room membership).

## Local seed

See [scripts/README.md](../scripts/README.md) and [docs/seed-credentials.md](../docs/seed-credentials.md).

After changing claims, users should sign out and sign in to refresh ID tokens.
