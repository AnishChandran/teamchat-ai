# Firestore Security

This document describes Firestore security rules for TEAMCHAT AI and how they relate to backend authorization.

## Admin SDK bypasses rules

The FastAPI backend reads and writes Firestore through the **Firebase Admin SDK** using a service account. **Admin SDK requests bypass Firestore security rules entirely.**

Therefore:

- **Backend authorization is mandatory** and remains the primary enforcement layer (`AuthService`, `RoomAuthorizationService`, org-scoped repositories).
- Firestore rules are **defense-in-depth** against direct client SDK access (accidental future frontend usage, stolen ID tokens used against Firestore REST/SDK APIs).
- **Do not remove or weaken backend checks** because rules exist.

## Architecture context

| Component | Firestore access |
|-----------|------------------|
| Frontend | Firebase Auth only — **no Firestore SDK** in the current app |
| Backend | Admin SDK — all reads/writes for rooms, messages, users |
| Realtime chat | WebSockets via backend — not Firestore listeners |

Initial data loads use REST; realtime updates use WebSockets.

## Data hierarchy

```
organizations/{organizationId}
organizations/{organizationId}/users/{userId}
organizations/{organizationId}/rooms/{roomId}
organizations/{organizationId}/rooms/{roomId}/messages/{messageId}
```

## Assumptions

1. **Single organization per user** — encoded in Firebase Auth custom claims as `organizationId`.
2. **App user ID in claims** — custom claims include `userId` (app document ID, e.g. `sarah`), set by the seed script. Room membership checks use `memberIds` on room documents.
3. **User document path** — `organizations/{orgId}/users/{userId}` where `userId` matches the claim and `firebaseUid` matches Firebase Auth UID (backend resolves users this way).
4. **Room membership** — `memberIds` array on room documents lists app user IDs allowed to read the room and its messages.
5. **Client writes disabled** — all mutations go through the backend (Admin SDK). Rules deny client writes to prevent impersonation and unauthorized creates at the Firestore layer.
6. **Admin operations** — room creation, member management, and message persistence are enforced in the backend; Firestore rules deny client writes so admin-only flows cannot be bypassed via direct Firestore access.

## Custom claims

After seeding (or provisioning), each Firebase Auth user should have:

```json
{
  "organizationId": "acme",
  "userId": "sarah"
}
```

Users must **sign out and sign in again** (or refresh ID token) after claims change for rules to see updated tokens.

## Security goals mapping

| Goal | Enforcement |
|------|-------------|
| Org isolation | `orgClaim() == orgId` on every allowed read |
| Room membership | `userClaim() in room.memberIds` for rooms and messages |
| Message scoping | Same room membership check on message subcollection |
| No impersonation | Client writes denied; backend sets `senderId` / `senderName` |
| Admin-only ops | Backend `RoomAuthorizationService`; client Firestore writes denied |

## Deploy rules

From `teamchat-ai/` with Firebase CLI logged into the project:

```bash
firebase deploy --only firestore:rules
```

Rules have no effect until deployed to the Firebase project.

## Recommended test cases (Rules Emulator)

Use the [Firebase Rules Emulator](https://firebase.google.com/docs/rules/emulator-setup) with `firestore.rules` and authenticated contexts that include `organizationId` and `userId` claims.

| # | Scenario | Auth context | Operation | Expected |
|---|----------|--------------|-----------|----------|
| 1 | Unauthenticated | none | read `organizations/acme` | Deny |
| 2 | Org member | `organizationId: acme`, `userId: sarah` | read `organizations/acme` | Allow |
| 3 | Cross-tenant | `organizationId: acme` | read `organizations/globex` | Deny |
| 4 | Room member | sarah ∈ `general.memberIds` | read `.../rooms/general` | Allow |
| 5 | Non-member | sarah ∉ `engineering.memberIds` | read `.../rooms/engineering` | Deny |
| 6 | Room member | sarah ∈ room | read `.../rooms/general/messages/{id}` | Allow |
| 7 | Non-member | sarah ∉ room | read messages in that room | Deny |
| 8 | Any user | valid claims | create/update/delete org, user, room, message | Deny |
| 9 | Missing `userId` claim | only `organizationId` | read room | Deny (fail closed) |
| 10 | List rooms query | member of some rooms | query `organizations/acme/rooms` | Returns only documents passing read rule (non-member rooms omitted) |

### Example emulator setup (conceptual)

```javascript
// Acme sarah — member of general
testEnv.authenticatedContext("sarah-firebase-uid", {
  organizationId: "acme",
  userId: "sarah",
});
```

Seed Firestore with Acme org, users, and rooms before running read tests.

## Backend regression tests (unchanged)

Continue to verify via pytest / manual API checks:

- Acme user cannot access Globex data through REST or WebSocket.
- Non-admin cannot `POST /api/rooms`.
- Non-member cannot load messages for a room they do not belong to.
- Message `senderId` is set server-side from the authenticated user.

These tests validate production behavior; rules emulator tests validate direct Firestore client access is blocked or scoped correctly.
