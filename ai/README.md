# Interaction Receiver API

FastAPI service that stores browser interaction recordings, replays them with Playwright, and can optionally extract product fields with an LLM.

See the [root README](../README.md) for Docker Compose, environment variables, and API overview.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
python run_dev.py
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

Set `DATABASE_URL` in `.env` to a local PostgreSQL instance.

## Sample extension

Files in `static/` and `extension_deployment/` send actions to:

`https://your-domain.com/api/v1/interactions/extension-action`

Replace that URL before you package the extension (`./deploy_extension.sh`).
