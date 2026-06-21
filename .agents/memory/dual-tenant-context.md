---
name: Dual tenant-context systems (NT Commerce)
description: Why auth/db "duplication" between main.py and config/database.py must NOT be mechanically merged
---

# Tenant DB context is now UNIFIED on config/database.py (single ContextVar)

NT Commerce binds the per-request tenant database through ONE shared ContextVar/proxy defined in `config/database.py`. `main.py` now imports `client, main_db, db, _tenant_db_ctx, get_tenant_db, set_tenant_context, init_tenant_database` from it (it used to define its own duplicate set — that drift is gone).

- **main.py `tenant_context_middleware`** sets that shared ContextVar from the JWT per request, but ONLY for tenant users (`type`/`role` != `super_admin`), and `reset()`s the token in a `finally` so super_admin/platform requests stay on `main_db` and there is no intra-request/cross-request bleed.
- **Modular routers (15 files):** `utils/auth.py:get_current_user` calls `set_tenant_context()` (same shared var). 
- **main.py `get_current_user`** still additionally **injects plan `features`/`limits`** onto the user (frontend feature-gating depends on this); `utils/auth.py`'s version does NOT. These two auth impls are intentionally kept separate (NOT merged) — keep role/permission checks in sync to avoid security drift. Warning docstring lives in utils/auth.py.

**Why:** Both writers now target the same ContextVar object, so legacy + modular routes can never read an unset var and fall back to `main_db` mid-request → no cross-tenant leakage. Before unification two distinct ContextVars coexisted (the dangerous part). Only `backend/server.py` imports from `main`.

**How to apply:** db naming is `tenant_<id with '-'→'_'>` via `get_tenant_db()`. Any new platform-only behavior must NOT bind tenant context. Verified by architect (isolation preserved). Confirmed with user: "DB is unified with a per-tenant sub-database for each tenant."

# Sidebar menu is NOT a dupe either
`Layout.js` (`tenantNavSections`) = runtime nav with permission `featureKey` (x21) + dynamic i18n labels. `config/sidebarMenu.js` (`defaultMenuSections`) = defaults for the customization/reorder UI (SidebarReorder.js, SidebarSettingsPage.js), no featureKey. Different purposes.

# Super-admin frontend routing quirk (App.js ProtectedRoute)
`ProtectedRoute` redirects super_admin AWAY from any path NOT in a hardcoded `startsWith()` allowlist (line ~132). To make a page reachable by super_admin you MUST add its path to that allowlist, else the menu item bounces to `/saas-admin`. Platform-only pages use the `superAdminOnly` prop (added) + must be in the allowlist. `/payments` is now platform-only (super_admin nav + `superAdminOnly` guard + allowlist).

# Low-stock filter has 3 intentional variants — only one is shared
The "low stock" Mongo filter exists in several forms: `$lt`+`ifNull 10` (the dominant one, now centralized in `utils/inventory_queries.py:low_stock_filter()` and used by stats/notifications/products/sendgrid routes), `$lte`+`ifNull 10` (inventory_robot — "at or below"), and `$lte` with NO default (stats restock-suggestions endpoint). The last two were deliberately NOT merged — `$lt` vs `$lte` changes which products count as low, so unifying them would change reported numbers. Report aggregations (sales totals, top products/customers, profit) across stats_routes/report_robot/profit_robot also LOOK duplicated but DIFFER in returned-status filters, date formats, and data sources — do NOT mechanically merge.

# /ai router prefixes
Two `/ai` routers existed; `ai_assistant_routes.py` now uses prefix `/ai-assistant` (matches AIAssistant.js), `routes/ai/chat_routes.py` keeps `/ai` (AI Accountant, AIChatPage.js). Don't reintroduce `/ai` on ai_assistant — it re-creates the `POST /ai/chat` shadow.
