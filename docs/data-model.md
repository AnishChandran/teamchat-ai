# Data Model

Firestore hierarchy:

```
organizations/{organizationId}
organizations/{organizationId}/users/{userId}
organizations/{organizationId}/rooms/{roomId}
organizations/{organizationId}/rooms/{roomId}/messages/{messageId}
```

## Organization

| Field | Type | Description |
|-------|------|-------------|
| id | string | Document ID |
| name | string | Display name |
| slug | string | URL-friendly identifier |
| createdAt | timestamp | Creation time |

## User

| Field | Type | Description |
|-------|------|-------------|
| id | string | Document ID |
| firebaseUid | string | Firebase Auth UID |
| name | string | Display name |
| email | string | Email address |
| role | `"admin"` \| `"member"` | Organization role |
| createdAt | timestamp | Creation time |

## Room

| Field | Type | Description |
|-------|------|-------------|
| id | string | Document ID |
| name | string | Room name |
| description | string | Room description |
| memberIds | string[] | User IDs of members |
| createdBy | string | Creator user ID |
| createdAt | timestamp | Creation time |

## Message

| Field | Type | Description |
|-------|------|-------------|
| id | string | Document ID |
| senderId | string | Sender user ID (or system/AI identifier) |
| senderName | string | Display name at send time |
| type | `"user"` \| `"ai"` \| `"system"` | Message kind |
| content | string | Message body |
| createdAt | timestamp | Creation time |
| status | `"streaming"` \| `"complete"` \| `"error"` | Delivery/state for AI messages |
