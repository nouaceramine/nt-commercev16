---
name: runTest targets backend port in dev
description: Why Playwright runTest hits FastAPI 404 instead of the React app in this dual-port dev setup
---

The `runTest` (testing skill) subagent navigates the project's *primary* external URL,
which in this repo maps to the backend, not the frontend.

**Why:** `.replit` ports map `localPort 8000 -> externalPort 80` (FastAPI) and
`localPort 5000 -> externalPort 5000` (CRA `yarn start`, the webview). The primary
`.replit.dev` domain = externalPort 80 = backend. In dev the backend does NOT serve the
React build (only the deployment `build` step copies `frontend/build` into
`backend/static/frontend`). So `runTest` opening `/` or `/portal` gets FastAPI
`{"detail":"Not Found"}` and reports `unable`/`failure` at the navigation step.

**How to apply:** Browser e2e via `runTest` is effectively blocked in this dev config.
The `app_preview` screenshot tool DOES target the frontend (port 5000) and works. For
verifying frontend-only changes here, rely on a clean webpack compile + `app_preview`
render checks; drive API/data flows with `curl` against `localhost:8000`. Seeded dev
logins live in `backend/reset_db.py` (tenant + super-admin accounts).
