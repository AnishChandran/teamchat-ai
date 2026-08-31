# Seed Credentials

Deterministic development accounts for local testing of TEAMCHAT AI.

## Prerequisites

1. **Firebase project** with Firestore enabled.
2. **Email/Password sign-in** enabled in Firebase Console → Authentication → Sign-in method.
3. **Service account** with permissions to manage Firebase Auth users and read/write Firestore.
4. **Environment variables** (same as backend):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export FIREBASE_PROJECT_ID=your-firebase-project-id
```

Optional:

```bash
export SEED_USER_PASSWORD='TeamChatDev123!'   # override default dev password
```

Never commit service account JSON or real production secrets to git.

## Run the seed script

From the backend virtualenv:

```bash
cd teamchat-ai/backend
source .venv/bin/activate
python ../scripts/seed_dev_data.py
```

### Flags

| Flag | Description |
|------|-------------|
| *(none)* | Idempotent upsert — safe to rerun |
| `--dry-run` | Preview planned creates/updates without writing |
| `--reset` | Delete seeded orgs + auth users, then reseed |

Examples:

```bash
python ../scripts/seed_dev_data.py --dry-run
python ../scripts/seed_dev_data.py --reset
```

## Rerun behavior

**Default mode is idempotent.** Re-running the script:

- Upserts organizations, users, rooms, and messages by deterministic IDs
- Updates Firebase Auth passwords and `organizationId` custom claims
- Does **not** duplicate messages or users

Use `--reset` when you want a completely clean slate.

## Test accounts

Default password: **`TeamChatDev123!`** (override with `SEED_USER_PASSWORD`).

### Acme Inc (`organizationId: acme`)

| Name | Email | Password | Role |
|------|-------|----------|------|
| Sarah | sarah@acme.test | `TeamChatDev123!` | admin |
| Mike | mike@acme.test | `TeamChatDev123!` | member |
| Lisa | lisa@acme.test | `TeamChatDev123!` | member |

Rooms: `general`, `engineering` (all Acme users are members)

### Globex Corp (`organizationId: globex`)

| Name | Email | Password | Role |
|------|-------|----------|------|
| John | john@globex.test | `TeamChatDev123!` | admin |
| Jane | jane@globex.test | `TeamChatDev123!` | member |
| Bob | bob@globex.test | `TeamChatDev123!` | member |

Rooms: `general`, `engineering` (all Globex users are members)

## Firebase Auth setup details

The seed script automatically:

1. Creates or updates each user in **Firebase Auth** by email
2. Sets the password from `SEED_USER_PASSWORD`
3. Sets custom claims `{ "organizationId": "<org-slug>", "userId": "<app-user-id>" }` required by the backend auth flow and Firestore rules
4. Writes matching Firestore user documents with `firebaseUid`

After seeding, users can sign in through Firebase Auth (email/password) in the frontend and obtain ID tokens for REST/WebSocket APIs.

## Seeded data summary

| Organization | Slug | Users | Rooms | Messages per room |
|--------------|------|-------|-------|-------------------|
| Acme Inc | `acme` | 3 | general, engineering | 10 each |
| Globex Corp | `globex` | 3 | general, engineering | 10 each |

## Verify after seeding

1. Sign in as `sarah@acme.test` and call `GET /api/me` — should return org `acme`.
2. Call `GET /api/rooms` — should list `general` and `engineering`.
3. Call `GET /api/rooms/general/messages` — should return seeded history.
4. Sign in as `john@globex.test` — should only see Globex data (tenant isolation).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Permission denied` on Firestore/Auth | Ensure service account has Firebase Auth Admin + Cloud Datastore User roles |
| `Invalid authentication token` after login | Re-run seed to refresh custom claims; sign out/in to refresh ID token |
| Email sign-in disabled | Enable Email/Password in Firebase Console |
| Wrong project | Check `FIREBASE_PROJECT_ID` and service account project match |
