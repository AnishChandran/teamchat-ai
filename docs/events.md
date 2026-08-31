# WebSocket Events

All events include a `type` field used as a discriminator for parsing.

## Client → Server

### `join_room`

Subscribe to realtime events for a room.

```json
{ "type": "join_room", "roomId": "..." }
```

### `leave_room`

Unsubscribe from a room.

```json
{ "type": "leave_room", "roomId": "..." }
```

### `send_message`

Send a chat message to a room.

```json
{ "type": "send_message", "roomId": "...", "content": "..." }
```

### `typing`

Broadcast typing state.

```json
{ "type": "typing", "roomId": "...", "isTyping": true }
```

## Server → Client

### `message_created`

A new message was persisted and should appear in the room.

```json
{ "type": "message_created", "message": { ... } }
```

### `presence_updated`

Online users currently joined to a room (snapshot).

```json
{
  "type": "presence_updated",
  "payload": {
    "roomId": "...",
    "users": [{ "id": "...", "name": "..." }]
  }
}
```

### `typing_updated`

Users currently typing in a room (snapshot).

```json
{
  "type": "typing_updated",
  "payload": {
    "roomId": "...",
    "users": [{ "id": "...", "name": "..." }]
  }
}
```

### `ai_started`

Gemini response generation began.

```json
{
  "type": "ai_started",
  "payload": {
    "roomId": "...",
    "messageId": "..."
  }
}
```

### `ai_chunk`

Streaming chunk from Gemini.

```json
{
  "type": "ai_chunk",
  "payload": {
    "roomId": "...",
    "messageId": "...",
    "delta": "..."
  }
}
```

### `ai_completed`

Gemini response finished and was persisted.

```json
{
  "type": "ai_completed",
  "payload": {
    "roomId": "...",
    "messageId": "..."
  }
}
```

### `ai_error`

Gemini generation failed.

```json
{
  "type": "ai_error",
  "payload": {
    "roomId": "...",
    "messageId": "...",
    "message": "AI is temporarily unavailable. Please try again."
  }
}
```
