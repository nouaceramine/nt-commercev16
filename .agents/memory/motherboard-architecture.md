---
name: Motherboard Architecture
description: How NT Commerce's modular self-diagnostics ("motherboard") core works and the non-obvious constraints around it.
---

# Motherboard core (`backend/core/`)

The app was re-architected into a "motherboard": every domain is an independent component
with its own log file, a central diagnostics panel, and a global error handler that tags each
unhandled error by component + short error_id. Built clean in `backend/core/` and wired in by
appending `install_motherboard(app, get_tenant_admin)` to the END of `backend/main.py` (so it
runs after all existing routers are registered — order matters: the global `Exception` handler
and diagnostics router must be installed last).

## Non-obvious constraints / decisions

- **Diagnostics prefix is `/diagnostics`, NOT `/health`.** A pre-existing `/api/health` route
  lives in `routes/system_sync_routes.py` (an `APIRouter()` with no prefix). Reusing `/health`
  would collide. Endpoints: `/api/diagnostics`, `/api/diagnostics/modules`,
  `/api/diagnostics/logs/{key}`, `POST /api/diagnostics/modules/{key}/clear-error`.

- **All diagnostics endpoints are admin-only.** They expose internal route prefixes, collection
  names, error state, and raw operational logs — a reconnaissance/data-exposure surface.
  `install_motherboard` takes a single `get_admin` dependency (we pass `get_tenant_admin`) used
  to gate every diagnostics endpoint. **Why:** code review flagged public `/modules` and
  merely-authenticated `/logs/{key}` as serious access-control violations.

- **`find_by_path()` must match on a path-segment boundary**, not bare `startswith`. A prefix
  matches only when `path == prefix` or `path.startswith(prefix + "/")`, so `/api/cash` does not
  swallow `/api/cash-boxes` (a different component). Longest matching prefix wins.

- **Global handler is registered for `Exception` only**, so FastAPI's built-in `HTTPException`
  and 422 validation handling are preserved — 404/422 behavior is unchanged for the 378+
  existing endpoints. Only genuinely unhandled errors become the motherboard 500 + error_id.

- **Per-component logging:** each module gets a `RotatingFileHandler` → `backend/logs/<key>.log`,
  with ERROR+ mirrored to a shared `backend/logs/errors.log`. Loggers set `propagate = False`
  to avoid root double-logging. `backend/logs/.gitignore` ignores everything except itself.

## Auth quirk relevant to testing diagnostics

- The working login endpoint is **`POST /api/auth/unified-login`** (auto-detects user type and
  returns `access_token`). `POST /api/auth/login` exists but rejected the tenant test creds.
  The tenant test user has role **`tenant_admin`**, which `get_tenant_admin` accepts.
  (Retrieve actual test credentials from the secure dev environment — never store them here.)

## Routes are mounted ONLY via the module layer — main.py imports were dead

- Live route mounting happens exclusively through `mount_all(app, ctx)` in `backend/main.py`,
  which loads each `backend/modules/<key>.py` wrapper; each wrapper imports ITS OWN routers and
  calls `app.include_router(...)`. `main.py` had ~55 leftover `from routes... import create_*_routes`
  / `router as *_router` imports that were **never called/included** there — pure dead code from
  before the migration. Safe to remove; only `get_super_admin`, `record_request_time`,
  `create_permission_checker` are actually referenced in main.py. `app.include_router(api_router)`
  is an empty placeholder.
- **Do NOT re-add `include_router` for route factories in main.py** — it would double-register
  every endpoint. Add/replace routers inside the relevant `modules/<key>.py` wrapper instead.
- **`backend/server.py` must NOT be deleted.** It is a 5-line shim (`from main import app`); the
  production VPS install (`install.sh`) launches `uvicorn server:app`. The Replit workflow uses
  `uvicorn main:app`. **Why:** the plan called it "legacy/duplicate" but it's an active prod entrypoint.
- "Physical migration" of handler code from `routes/*.py` into `modules/<key>/` packages is
  unnecessary churn: the swappable-component boundary already exists via the wrappers. Keeping
  handlers in `routes/*.py` satisfies the modular goal at far lower regression risk.

## Wallet endpoint ownership (IDOR guard)

- `backend/routes/wallet_routes.py`: any read/mutation that accepts an `entity_id` must force
  non-super-admins to their OWN entity (`user.get("tenant_id", user.get("id"))`) and only honor a
  supplied `entity_id` when `user["role"] == "super_admin"`. Applies to `/wallet/transactions`,
  `/transactions/paginated`, `/alerts`, `/alerts/{id}/read`, `/services/purchases`, and the
  purchase endpoint (which derives the wallet owner from the token, never from the body).
  **Why:** code review found these let any authenticated user read/modify another tenant's wallet
  data by passing an arbitrary id.

## Wallet debits MUST be atomic (no read-check-write)

- All balance debits go through `_record_txn`. Debits use a single conditional update
  `find_one_and_update({entity_id, balance: {$gte: amount}}, {$inc:{balance:-amount}}, AFTER)` and
  raise `400 الرصيد غير كافي` when no doc matches — never read balance, compare in Python, then
  `$set` a computed value. **Why:** code review caught a double-spend race; the old read-check-write
  let N concurrent purchases all pass the check and overspend. Verified: 10 concurrent 500-DZD
  purchases against a 1500 balance → exactly 3 succeed, balance lands at 0, never negative.
  **Note:** local mongod is standalone (no replica set), so multi-doc transactions are unavailable;
  the conditional `$inc` is the correct atomicity primitive here.

## Paid services catalog (wallet sub-feature)

- Collections `wallet_services` (super-admin-managed catalog: name_ar/fr, price, is_active) and
  `wallet_service_purchases` (history). Tenants pay from their own wallet via
  `POST /wallet/services/{id}/purchase` (debit reference_type `"service"`). Non-super-admins only
  ever see active services. This is how "use the balance in services" (vs pay-subscription) is met.

## Route-prefix coverage is mandatory (modules_map)

- Every `/api/*` route namespace MUST be listed under some component's prefixes in
  `backend/core/modules_map.py`. Any unmapped path falls through `find_by_path()` → `None`
  → errors get mis-tagged to the `"core"` fallback instead of the real domain component,
  silently defeating the whole "tag each error by component" goal.
- **Why:** code review found ~80 active routes (barcodes, integrations, delivery, marketing/sms,
  transactions, sim, shop, tenant, system, sync, upload, webhook, etc.) had no prefix entry and
  were all attributed to core.
- **How to apply:** after adding/renaming any router prefix, run a live parity scan — iterate
  `app.routes`, and assert `registry.find_by_path(p)` is non-None for every `/api/*` path except
  the genuine core/infra ones (`/api`, `/api/health`, `/api/diagnostics`, `/api/static`,
  `/api/init-default-data`). Expand modules_map until zero business routes are unmapped.
