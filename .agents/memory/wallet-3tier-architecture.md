---
name: 3-Tier Wallet Architecture
description: How the platform/agent/tenant wallet hierarchy works — all tiers already implemented, key wiring points.
---

# 3-Tier Wallet Hierarchy

## Tier map
| Tier | entity_id | entity_type | DB |
|---|---|---|---|
| Platform (super-admin) | `"platform_main"` (PLATFORM_WALLET_ID constant) | `"admin"` | main_db.wallets |
| Distributor (agent) | agent's UUID | `"agent"` | main_db.wallets |
| Tenant | tenant UUID | `"tenant"` | main_db.wallets |

## Key files
- `backend/services/wallet_service.py` — `debit_wallet`, `credit_wallet`, `transfer_balance` (atomic debit-source + credit-dest + 2 txns); `PLATFORM_WALLET_ID = "platform_main"`
- `backend/routes/wallet_routes.py` — `_entity_ref(user)` maps super_admin → PLATFORM_WALLET_ID; topup approval = sell from platform_main to recipient
- `backend/routes/saas/agent_self_service_routes.py` — agent wallet GET/request/approve (transfer agent→tenant)
- `backend/routes/digital_panel_routes.py` — subscription sale debits tenant wallet by COST (choice 1-أ, with saga compensation)

## Balance-selling chain
1. Super-admin funds `platform_main` via `/wallet/add-funds` (admin direct credit, no source)
2. Tenant requests topup → super-admin approves → platform_main debited → tenant credited
3. If tenant has `agent_id`: request routed to agent → agent approves → agent wallet debited → tenant credited
4. Agent requests balance from super-admin/parent → same approval flow

**Why:** Prevents balance being created from thin air; every credit has a matching debit upstream.

## Unification
All services draw from the SAME main_db wallet per entity:
- SIM recharge (recharge_sim_routes) debits tenant wallet by cost
- IPTV/digital subscriptions (digital_panel_routes) debit tenant wallet by cost
- SaaS subscription auto-pay debits tenant wallet

## Frontend pages
- `TenantDashboardPage.js` — wallet balance card (fetches GET /wallet)
- `AgentDashboardPage.js` — wallet balance + request topup + approve tenant requests
- `WalletPage.js` — full wallet management; super-admin sees platform_main balance + add-funds + approval queue
