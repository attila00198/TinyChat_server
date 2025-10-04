# terminalchat — backend for a static web UI

This repository contains the backend WebSocket server used by a static web-based UI named "terminalchat". The server is a lightweight Python WebSocket application (using the `websockets` library) that accepts JSON messages from browser clients and broadcasts updates to connected clients.

This README documents how to run the server, the JSON protocol the frontend should use, and example client snippets. The project is the backend only — the frontend is expected to be a static web app (HTML/JS) that connects to this server over WebSocket.

Contents

- `main.py` — WebSocket server implementation (entrypoint).
- `test.py` — small smoke/test script demonstrating command handling.
- `README.md` — this document.

Frontend:
- The recommanded frontend located at (Not published yet.)

Prerequisites

- Python 3.10+ (3.8+ is likely fine but not explicitly tested).
- `websockets` Python package (see quick start for install).

Quick start (Windows PowerShell)

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install the runtime dependency

```powershell
pip install websockets
```

3. Run the server

```powershell
python main.py
```

By default the server listens on 0.0.0.0:8765 (see `main.py` constants `HOST` and `PORT`).

Run the smoke/test script

```powershell
python test.py
```

Protocol overview (JSON over WebSocket)

The server communicates using JSON messages. Clients (the static web UI) should open a WebSocket connection and exchange JSON objects. The server expects messages with a `type` field. Supported incoming types:

- `join` — indicates the client joined. Include `username` to set the username on first connection.
- `message` — a public chat message to broadcast.
- `command` — a text command (prefixed with `/`) for server-side command handling.

Server-to-client message types the frontend will receive:

- `user_list` — sent after a user sets their username or when users connect/disconnect. `content` is an array of user objects: `{ username, is_mod, is_timed_out }`.
- `command_list` — a list or info about supported commands (currently a placeholder in the server).
- `system` — system messages, errors and informational notices. Contains `username: "System"` and `content`.
- `private` — private messages (whispers) between users. Contains `{ type: "private", from, to, content, timestamp }`.

Message shapes and examples

Client -> Server: set username (recommended first message)

```json
{ "type": "join", "username": "alice" }
```

Client -> Server: public chat message

```json
{ "type": "message", "username": "alice", "content": "Hello everyone" }
```

Client -> Server: send a command

```json
{ "type": "command", "username": "alice", "content": "/whisper bob Hey Bob!" }
```

Server -> Client: user list

```json
{ "type": "user_list", "content": [ { "username": "alice", "is_mod": false, "is_timed_out": false } ], "timestamp": "12:34:56" }
```

Notes about behavior

- The server sets the client's username the first time it receives any JSON that contains a `username` key while the server's stored username for that connection is `None`. It's recommended that the client immediately send the `join` message with `username` after opening the WebSocket.
- Public broadcasts exclude the sender (the server sends to all other connected clients).
- Commands currently implemented/handled in the code: `/whisper` (implemented), `/login`, `/to`, `/help` (placeholders). The server replies with `system` messages for unknown or unimplemented commands.
- A moderator password is present as a constant (`MOD_PASSWORD = "admin123"` in `main.py`) but authentication flows are not implemented in the public API — treat this constant as a placeholder.

Example browser client (minimal, for the static UI)

```javascript
const url = 'ws://localhost:8765';
const ws = new WebSocket(url);

ws.addEventListener('open', () => {
  // Set username right away
  ws.send(JSON.stringify({ type: 'join', username: 'alice' }));
});

ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data);
  console.log('received', msg);
  // Update UI based on msg.type
});

// Send a public message
function sendMessage(text) {
  ws.send(JSON.stringify({ type: 'message', username: 'alice', content: text }));
}

// Send a command
function sendCommand(text) {
  ws.send(JSON.stringify({ type: 'command', username: 'alice', content: text }));
}
```

Development notes

- The server is implemented using `asyncio` and the `websockets` package in `main.py`.
- Logging is enabled in `main.py`; set `is_debug_enabled` if you want more verbose logs.
- The server currently runs in a background thread and waits for Enter/keyboard interrupt to exit when started from the CLI.

Testing and improvements

- `test.py` contains a minimal command-handling smoke test. Expand it or convert to `pytest` for CI.
- Suggested improvements:
  - Add `requirements.txt` or `pyproject.toml` to pin dependencies.
  - Add CLI/ENV config (host/port) so the server can be configured without editing source.
  - Implement authentication for moderator actions and document the moderator API.
  - Add typed JSON schemas (or JSON Schema) and unit tests for message handling.

Contributing

Contributions are welcome. Open issues for design/feature discussions and submit pull requests with tests where possible.

License

Add a `LICENSE` file to the repo and update this section to reflect your chosen license.

Contact

Open an issue if you want help integrating the static UI with this backend or if you want me to add an example static client page.

---

If you want, I can also:

- Add a `requirements.txt` and pin `websockets` to a tested version.
- Create a minimal static `index.html` + JS client that connects to this backend and demonstrates login, sending messages and whispering.
- Add CLI flags to `main.py` and a small settings loader that reads host/port from environment variables.

Tell me which of those you'd like next and I'll implement it.