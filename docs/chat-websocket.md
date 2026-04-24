# Chat WebSocket

## Connection

```
ws://localhost:8080/api/chat/conversations/{conversation_id}/ws
```

**Query parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `last_message_id` | UUID | No | UUID of the last received message. If provided, the server replays all missed messages after it (useful for reconnects) |

---

## Authentication

After the WebSocket connection is established, the client **must** send an auth message **within 10 seconds**, otherwise the connection is closed with code `4001`.

**Client → Server:**
```json
{ "type": "auth", "token": "<JWT access token>" }
```

**Server → Client (success):**
```json
{ "type": "auth_ok", "conversation_id": "<UUID>" }
```

**Server → Client (failure — connection closes):**
```json
{ "type": "error", "code": "<error code>" }
```

---

## Messages: Client → Server

### `auth` — authenticate the connection
```json
{ "type": "auth", "token": "<JWT access token>" }
```

### `ping` — keep-alive
```json
{ "type": "ping" }
```

### `typing` — typing indicator
```json
{ "type": "typing" }
```

---

## Messages: Server → Client

### `auth_ok` — authentication confirmed
```json
{ "type": "auth_ok", "conversation_id": "<UUID>" }
```

### `pong` — keep-alive response
```json
{ "type": "pong" }
```

### `message` — new message
```json
{
  "id": "<UUID>",
  "conversation_id": "<UUID>",
  "sender_id": "<UUID>",
  "content": "Message text",
  "is_deleted": false,
  "created_at": "2026-04-12T10:30:00+00:00"
}
```
> `content` is `null` when `is_deleted` is `true`.

### `message_deleted` — a message was deleted
```json
{ "type": "message_deleted", "message_id": "<UUID>" }
```

### `typing` — the other participant is typing
```json
{ "type": "typing", "user_id": "<UUID>" }
```

### `messages_read` — the other participant read the messages
```json
{ "type": "messages_read", "user_id": "<UUID>" }
```
> Emitted when the participant opens the chat (WS connect) or fetches message history via `GET /conversations/{id}/messages`. All messages sent before this moment should be treated as read by that user.

### `error` — an error occurred (connection closes after)
```json
{ "type": "error", "code": "<error code>" }
```

---

## Error Codes

| Code | WS Close Code | Reason |
|---|---|---|
| `invalid_token` | `4001` | Token is malformed or missing |
| `auth_timeout` | `4001` | No auth message received within 10 seconds |
| `token_expired` | `4001` | JWT token has expired |
| `forbidden` | `4003` | User is not a participant of the conversation |

---

## Lifecycle

```
Client                              Server
  |                                   |
  |-------- WS connect -------------->|
  |                                   |
  |-- { type: auth, token: "..." } -->|   must be sent within 10s
  |                                   |
  |<-- { type: auth_ok, ... } --------|
  |<-- [ missed messages replay ] ----|   only if last_message_id was provided
  |                                   |
  |-------- { type: ping } ---------->|
  |<------- { type: pong } -----------|
  |                                   |
  |-------- { type: typing } -------->|
  |<-- { type: typing, user_id } -----|   broadcast to other participant(s)
  |                                   |
  |<-- { message object } ------------|   real-time incoming messages
  |                                   |
  |<-- { type: messages_read, ... } --|   when other participant opens chat or fetches messages
  |                                   |
  |-------- disconnect -------------->|
```

---

## Notes

- **Presence** — the server tracks online status in Redis (TTL 30s, refreshed every 15s). If the recipient is offline, an FCM push notification is sent to their registered devices (iOS / Android).
- **Message replay** — on reconnect, pass `last_message_id` to receive up to 200 messages that arrived while disconnected.
- **Malformed JSON** — invalid JSON received after authentication is silently ignored; the connection stays open.
- **Soft deletes** — deleted messages are never removed from the database. On deletion the server broadcasts a `message_deleted` event (with only `message_id`) to all connected participants. When fetching message history via REST, deleted messages are returned with `is_deleted: true` and `content: null`.
- **Read receipts** — the server broadcasts `messages_read` to the conversation channel whenever a participant marks messages as read (on WS connect or REST message fetch). The `unread_count` field on conversation objects and the `GET /conversations/unread-count` endpoint reflect the current unread state.
