---
name: Digital Services Reseller Panel
description: IPTV/digital subscriptions + resellers + wallet money-flow rules and the saga/compensation pattern used for financial integrity
---

# Digital Services Reseller Panel (بانل الخدمات الرقمية)

Part of the "services" idea. Tenant-scoped collections: `digital_services` (catalog),
`digital_subscriptions`, `resellers`, `reseller_transactions` (ledger). Routes mounted
as a motherboard module (`modules/digital_panel.py`, registered in COMPONENT_MODULES
after "services"). Frontend: 4 pages under `/digital-panel/*`.

## Money-flow rule (non-obvious, load-bearing)
On selling a subscription:
- **The SaaS platform wallet (`main_db.wallets`) is NEVER debited.** That wallet is
  the tenant's prepaid balance with the super admin and belongs ONLY to the
  mobile-recharge service (recharge credits come from the SaaS provider's stock).
  IPTV/digital lines are bought from the tenant's OWN suppliers, so subscription cost
  is recorded for profit reporting but never moves the SaaS wallet.
- **Reseller balance is debited by PRICE** (what the reseller owes), when the sale is
  attributed to a `reseller_id`. This is a tenant-local ledger (`resellers` /
  `reseller_transactions`), unrelated to the SaaS wallet.
**Why:** the user reported "the tenant buys subscriptions from the super admin account
(SaaS)" — debiting `main_db.wallets` for IPTV wrongly consumed the recharge balance
held with the SaaS provider for an unrelated supplier purchase. `payment_method` for
subscriptions is cash | reseller | debt (no "wallet" option).

## Compensation / saga pattern
There are NO Mongo multi-doc transactions here, so financial writes use ordered
compensation:
- `_move_reseller_balance` is atomic-from-caller: it `find_one_and_update`s the balance
  then writes the ledger; **if the ledger insert fails it reverts the balance `$inc`**
  so a balance never moves without a recorded transaction.
- `create_subscription` order: reseller debit (only when `reseller_id` set) → insert
  subscription. A failed final insert **refunds the reseller balance**. There is NO
  SaaS-wallet step anymore (see Money-flow rule above).
**How to apply:** when adding any new financial step, refund every prior step on
failure, and never mutate a balance without pairing it with a ledger write that
self-reverts on failure.

## Status / profit
- `profit = price - cost` (stored). `status` is computed live from `end_date`
  (active / expiring within 7d / expired) — never trust a stored status field.
- `end_date` = start + duration_months via calendar-safe `_add_months` unless an
  explicit `end_date` is provided.

## Known accepted limitation
Routes use `require_tenant` (the app-wide tenant dependency). super_admin without a
`tenant_id` is permitted by that dependency everywhere; not special-cased here on
purpose, to stay consistent with all other tenant routes. See `dual-tenant-context.md`.
