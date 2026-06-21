---
name: Bridge Recharge Architecture
description: How the async mobile recharge bridge (cloud + local bridge) works — critical patterns and pitfalls.
---

# Bridge Recharge Architecture

## Flow
1. Cashier submits POST /api/recharge (JWT auth, tenant wallet debited by COST immediately)
2. Backend creates `mobile_recharge_tasks` (status=pending) + stores `entity_id` + `wallet_txn_id` on both recharge doc and task
3. Local bridge polls GET /api/recharge/bridge/tasks (auth: X-Bridge-Secret + X-Tenant-ID headers)
   - Atomically marks fetched tasks as "processing" (update_many pending→processing) — claim semantics
4. Bridge executes USSD, then PATCH /api/recharge/bridge/tasks/{id}/result with {status: success|failed}
   - Idempotent: `find_one_and_update({status: {$nin: [success, failed]}}, ...)` — double-call safe
   - On failure: compensates tenant wallet via `credit_wallet` using stored `wallet_txn_id`
5. Frontend polls GET /api/recharges/{id}/status every 3s until non-pending status

## Critical: Bridge tenant context
Bridge routes (no JWT) use `X-Tenant-ID` header → `get_tenant_db(x_tenant_id)` → correct tenant DB.
**Never** use the `db` ContextVar proxy in bridge handlers — it falls back to main_db without a JWT.
`verify_bridge` returns `tenant_db` and handlers receive it via `Depends(verify_bridge)`.

## Task status lifecycle
`pending` → `processing` (claimed by GET /tasks) → `success | failed` (PATCH /result)
Only success and failed are terminal (TERMINAL_STATUSES set).

## Saga compensation on creation failure
POST /recharge uses boolean flags (recharge_inserted, cashbox_updated, txn_inserted) to track which writes succeeded, then rolls back in reverse order + refunds wallet. `wallet_txn_id` is pre-generated before debit so it can be used as compensation reference.

## Idoom codes (idoom_routes)
Atomic sell: `find_one_and_update({status:available, denomination})` → status=reserved → debit wallet → status=sold.
On wallet debit failure: release code back to available. On DB log failure: credit wallet + release code.
Inventory filter "all" sentinel (not empty string) avoids Radix Select crash.

## Factory call site
`modules/services.py` must pass `ctx.get_tenant_db` to `create_recharge_sim_routes(...)` as 8th arg.
