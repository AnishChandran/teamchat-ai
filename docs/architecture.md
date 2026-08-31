# Architecture

## Overview

TEAMCHAT AI is a multi-tenant collaborative chat platform where users in the same organization share rooms, exchange messages in real time, and invoke Gemini AI via `@Gemini` or `@AI` mentions.

## Layers

| Layer | Responsibility |
|-------|----------------|
| Frontend | React UI, Firebase Auth (client), WebSocket client, REST client |
| Backend | Auth validation, tenant isolation, REST APIs, WebSocket hub, Gemini streaming |
| Firestore | Persistent storage for organizations, users, rooms, messages |
| Firebase Auth | User authentication |

## Realtime delivery

**Do not use client-side Firestore realtime listeners** (`onSnapshot`, polling for chat).

The FastAPI backend owns realtime delivery over WebSockets:

- New messages
- Typing indicators
- Online presence
- Gemini streaming chunks

Initial room lists, message history, and user data are loaded via REST.

## Multi-tenancy

1. Every user belongs to exactly one organization.
2. `organizationId` is derived server-side from the authenticated user — never trusted from the client.
3. Every room operation verifies: authenticated user, user's organization, room belongs to organization, user is a room member.
4. Backend authorization is mandatory regardless of Firestore security rules.

## Data flow (high level)

```
Client --REST--> FastAPI --> Firestore (read/write)
Client <--WS-->  FastAPI --> broadcast to room members
Client --REST--> FastAPI --> Vertex AI Gemini (on @AI/@Gemini mention)
```
