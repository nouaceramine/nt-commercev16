---
name: Wallet-funded recharge & table-code scheme
description: How recharge debits the platform wallet and the EM/CA/DP/FA/RE/PF code conventions
---

# Wallet-funded recharge

- The platform wallet lives in **main_db.wallets / main_db.wallet_transactions** (shared with super admin, topped up via super-admin add-funds). Tenant wallet is keyed by `entity_id == tenant_id`.
- A recharge **debits the wallet by COST** (`amount - profit`), while the **cash box is credited by full AMOUNT** — this is intentional margin capture, not a bug.
- Debit happens **before** inserting the recharge doc. If any downstream write fails, the route compensates with `credit_wallet(... ref_type="recharge_refund")`. Shared helpers live in `backend/services/wallet_service.py` (`debit_wallet`, `credit_wallet`, `get_or_create_wallet`).
- `debit_wallet` uses an atomic conditional update `{"balance": {"$gte": amount}}` + `$inc` and raises HTTP 400 `"الرصيد غير كافي"` when insufficient.

**Why:** user linked the existing super-admin platform wallet to recharge funding (same wallet also funds SaaS subscription). Cross-collection/cross-db writes are not transactional here, so the compensating-credit pattern is the safety net.

# Table-code scheme

- Central generator: `backend/services/code_generator.generate_code(db, collection, prefix, digits=5, with_year=True)` — regex-matches the `code` field and increments.
- **Entities = no year** (`with_year=False`): Employees `EM`, Caisses/cash_boxes `CA`, Dépôts/warehouses `DP`, Familles/product_families `FA`.
- **Operations = with year** (`with_year=True`): Recharge `RE` (e.g. `RE00001/26`), Wallet transactions `PF` (e.g. `PF00002/26`).
- `RechargeResponse` and `ProductFamilyResponse` carry an optional `code` field so codes surface in API responses.

**How to apply:** when adding a new countable record, decide entity (no year) vs operation (with year), call `generate_code` with the right prefix, and store under the `code` field.

# 3-tier wallet hierarchy (balance-selling chain)

- **Invariant:** balance is only ever created when super-admin funds the single platform wallet (`entity_id == "platform_main"`). Everything else is a **transfer** down the chain super-admin → distributor (`entity_type="agent"`, nests via `parent_agent_id`) → tenant; a topup approval debits the approver/seller and credits the recipient, so total balance is conserved.
- A tenant's own unified wallet is debited by COST on every sale (recharge AND digital/IPTV subscriptions) — one wallet funds all tenant spend.

**Why / CRITICAL quirk:** mongod here is **standalone (no replica set)** → no multi-doc transactions are available. Money integrity therefore depends on two atomic primitives that any new approve/transfer path MUST reuse:
1. Atomic debit guard `{"balance": {"$gte": amount}}` so a wallet can never go negative.
2. Atomic **claim** of the request before moving money: `find_one_and_update({id, status:"pending"}, {$set:{status:"processing"}})`, do the transfer, then set `approved`; revert `processing → pending` on any failure. Skipping this lets two concurrent approvals double-spend the same request.

**Why log on compensation failure:** the credit-failure refund can itself fail; that case must `logger.critical` (never swallow) because it leaves balance unreconciled and needs manual fixing.

**How to apply:** super-admin maps to `platform_main` regardless of account; agent self-service wallet endpoints live under SaaS routes where `db` IS the platform/main db, and an agent may only approve requests it owns (its tenants/sub-agents) — check ownership BEFORE claiming.
