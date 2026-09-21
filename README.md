# Interaction Receiver

FastAPI backend that receives browser interaction recordings, stores them in PostgreSQL, and can replay those actions with Playwright. Optional LLM analysis (OpenAI or AvalAI) can turn the captured page into structured product data.

Companion Chrome extension: [interaction-tracker](https://github.com/soheylrahmani/interaction-tracker).

## Features

- **Extension ingest**: `POST /api/v1/interactions/extension-action` stores clicks and form changes from the tracker
- **Session lookup**: fetch recordings by session ID or retail ID
- **Action replay**: Playwright replays recorded actions and returns filtered HTML
- **Optional LLM analysis**: extract structured product fields from the captured page
- **Docker Compose**: PostgreSQL + API on public images, no private registry required

## Layout

```
interaction-receiver/
  compose.yml
  .env.example
  LICENSE
  postgres/init/     # optional first-boot SQL (gitignored dumps)
  ai/                # FastAPI app, Dockerfile, sample extension
```

## Quick start (Docker)

1. Copy the env file and set a database password (and API keys if you use LLM analysis):

```bash
cp .env.example .env
```

2. Start PostgreSQL and the API:

```bash
docker compose up --build
```

3. Open Swagger UI at `http://localhost:8000/docs`. Health check: `GET /health`.

Point the [interaction-tracker](https://github.com/soheylrahmani/interaction-tracker) (or the sample extension under `ai/static/`) at:

```
https://your-domain.com/api/v1/interactions/extension-action
```

For local testing use `http://localhost:8000/api/v1/interactions/extension-action`. Add that origin to `CORS_ORIGINS` if a browser client calls the API directly.

## Local development (without Docker)

Requires PostgreSQL 16 and Python 3.12.

```bash
cd ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# set DATABASE_URL to your local Postgres
python run_dev.py
```

Optional migrations:

```bash
cd ai
alembic upgrade head
```

Compose already runs `create_all` on startup, so migrations are optional for a fresh database.

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/interactions/extension-action` | Receive actions from the browser extension |
| `GET` | `/api/v1/interactions/` | List stored interactions |
| `GET` | `/api/v1/interactions/by-session-id/{session_id}` | Lookup by session |
| `GET` | `/api/v1/interactions/by-retail-id/{retail_id}` | Latest interaction for a retail ID |
| `POST` | `/api/v1/interactions/scan` | Replay actions and store filtered HTML |
| `POST` | `/api/v1/interactions/scan-and-analyze` | Replay + LLM product extraction |
| `POST` | `/api/v1/gpt-agent/create-product/{retail_id}` | LLM analysis of already-scanned HTML |
| `GET` | `/api/v1/interactions/extension-download` | Download the sample extension zip |

### Extension payload

```json
{
  "user_id": 1,
  "session_id": "string",
  "client_recommendation": "string",
  "actions": [
    {
      "type": "click|change",
      "selector": "string",
      "value": "string",
      "timestamp": "ISO string"
    }
  ],
  "url": "string"
}
```

[interaction-tracker](https://github.com/soheylrahmani/interaction-tracker) sends `user_id`. This API also accepts `retail_id`. Either value must be an integer; it is stored as `retail_id`.

## Configuration

See `.env.example`. Important keys:

- `POSTGRES_*` / `DATABASE_URL` — database
- `CORS_ORIGINS` — comma-separated allowed origins (no hardcoded production hosts)
- `OPENAI_API_KEY` / `AVALAI_API_KEY` — optional, only needed for analysis endpoints

Do not commit `.env`. Rotate any keys that previously lived in a private copy of this project.

## Sample extension

`ai/static/` and `ai/extension_deployment/` contain a sample recorder. Before packaging, replace `https://your-domain.com` in `content.js` with your API host, then run:

```bash
cd ai
./deploy_extension.sh
```

For the standalone public extension, use [interaction-tracker](https://github.com/soheylrahmani/interaction-tracker).

## License

MIT. See [LICENSE](LICENSE).
