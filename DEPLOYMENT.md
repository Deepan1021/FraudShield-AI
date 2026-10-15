# Deployment

## Local (Windows 10/11)

See `README.md`. `setup.bat` then `run.bat` (development) or `run.bat prod` (UI built and served by the API on port 8000).

## Docker

```bash
docker compose up --build            # http://localhost:8000
AUTO_SEED_DEMO=false docker compose up --build    # start without demo data
```

The image builds the frontend (Node 20) and runs the API (Python 3.12-slim) as a non-root user with `APP_ENV=production`.
Database, reports, backups and logs live in the `fraudshield_data` volume (`/data`). A health check calls `/api/health`.

## Production notes

* Authentication is not built in: place the service behind an authenticating reverse proxy (TLS, rate limits, body limits).
* Set `CORS_ORIGINS` to the exact UI origin when the UI is hosted separately; with `SERVE_FRONTEND=true` everything is same-origin.
* Back up the database with the Settings page / `POST /api/system/backup` or copy the volume.
* Startup fails with an actionable message if the database cannot be opened, the schema is invalid or no rules load.
* For PostgreSQL see `docs/database.md`.

## Troubleshooting (Windows)

| Symptom | Fix |
|---|---|
| `python` / `py` not found | Reinstall Python and tick "Add python.exe to PATH" |
| `npm` not found | Install Node.js LTS, reopen the terminal |
| Port 8000 or 5173 busy | Set `API_PORT` in `.env` (and the proxy target in `frontend/vite.config.ts`), or stop the other process |
| UI shows "Cannot reach the FraudShield API" | Start the API window; check <http://127.0.0.1:8000/api/health> |
| PowerShell blocks `activate` | `Set-ExecutionPolicy -Scope Process Bypass`, or use `cmd` |
| `Startup check ... failed` | Read the message; typical causes are an unwritable `database/` folder or a corrupt rule file |
