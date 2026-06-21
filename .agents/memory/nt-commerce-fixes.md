---
name: NT Commerce Bug Fixes
description: Critical auth, schema, route, and duplicate operation ID fixes for the NT Commerce multi-tenant FastAPI+React POS system
---

## JWT Auth Fix
JWT `sub` must be the actual user `id` (UUID from tenant DB), NOT the `tenant_id`. Token payload: `{sub: user_id, tenant_id: tenant_id, type: "tenant"}`. File: `backend/routes/auth_users_routes.py`.

**Why:** `get_current_user` does `db.users.find_one({"id": payload["sub"]})` — if sub is tenant_id the lookup fails → 401 everywhere.

## Default Warehouse Required
Tenant DB must have a `main-warehouse` doc in `warehouses` collection on creation. See `backend/reset_db.py`. Without it, warehouse-dependent routes return empty/error.

## Pydantic Schema Flexibility
`SaleItem`, `SaleCreate`, `PurchaseItem`, `PurchaseCreate` must use `model_config = ConfigDict(extra="ignore")` and make `product_id: Optional[str] = None` (frontend sends null for custom/cash items). `paid_amount` and `subtotal` should default to 0.

**Why:** Frontend sends extra fields (barcode, originalPurchasePrice, etc.) and null product_id for custom sales items. Strict models caused 500 errors.

## Duplicate Operation IDs Pattern
FastAPI warns on duplicate Python function names across routes registered to same app. Fix: add `operation_id="unique_name"` to `@router.xxx()` decorator. Affected files in this project: `notifications_routes.py` (internal dups), `notification_routes.py`, `system_sync_routes.py`, `families_permissions_routes.py`, `utility_routes.py`.

## Repair Routes: Two Formats
- `POST /api/repairs` — accepts full RepairReceptionPage format: `device_brand`, `device_model`, `problems[]`, `problem_description`, `advance_payment`, `estimated_days`
- `POST /api/repairs/tickets` — accepts the legacy `RepairTicketCreate` schema: `brand_name`, `model_name`, `reported_issue`

**Why:** RepairReceptionPage.js posts to `/api/repairs` with a richer schema than the legacy `/tickets` endpoint.

## Settings Features: PUT + POST
`PUT /api/settings/features` must exist alongside `POST`. Frontend uses PUT. File: `backend/routes/system_sync_routes.py`.

## Auth for Certain Routes
- `GET /api/settings/datetime` → public (no auth), called before login
- `GET /api/robots/status`, `GET /api/auto-reports`, `GET /api/wallet/stats` → use `get_current_user` not `get_super_admin`

## Spare Parts CRUD
All CRUD endpoints (`GET/POST/PUT/DELETE /api/spare-parts`, `/api/spare-parts/stats`) were missing — added to `backend/routes/families_permissions_routes.py`.

## Test Credentials
- Seeded dev test accounts exist for a tenant user (role `tenant_admin`) and the super admin.
  Do NOT store the actual emails/passwords here — retrieve them from the secure dev environment.

## Divergent get_current_user copies & super-admin token shape

- There are THREE `get_current_user` implementations: `main.py` (canonical, used by factory
  routers via AppContext), `utils/auth.py` (used by module-level routers that import it directly:
  families_permissions, system_sync, accounting), and `utils/dependencies.py` (UNUSED).
- **Super-admin JWT contains `role: "super_admin"` and NO `type` field**, and the super-admin
  record lives in **`main_db.users`** (the `super_admins` collection is empty). Any auth dep that
  keys off `payload.get("type")` and looks in `super_admins` will FAIL for super admin.
- **Why it bit us:** `utils/auth.py.get_current_user` defaulted `type` to `"tenant"` and looked in
  `super_admins`, so `/api/product-families` (and other module-level-router endpoints) returned
  **401** for super admin. The frontend `lib/apiClient.js` interceptor force-logs-out on ANY 401,
  so super admin logged in then got instantly kicked out.
- **How to apply:** super-admin detection must check BOTH `type == "super_admin"` OR
  `role == "super_admin"`, and resolve from `main_db.users` (super_admins as fallback). Keep the
  three copies behaviorally consistent. A valid-token-but-wrong-role case ideally is 403, not 401,
  because the frontend treats 401 as "token dead → logout".

## Impersonation error was really a malformed-data 500

- Super-admin "الدخول لحساب المشترك" (impersonate, `POST /api/saas/impersonate/{tenant_id}`) works
  fine on its own (200 + valid tenant JWT). The visible "error" came from the dashboard the browser
  redirects to: it immediately calls `GET /api/products`, which 500'd.
- **Root cause:** tenant DBs can contain malformed product docs (no `id`, or `id: null`). Endpoints
  that did `p["id"]` crashed with `KeyError: 'id'`. Fixed in `products_routes.py` (filter/`.get`)
  and `notifications_routes.py` generate-low-stock (skip docs without id, `.get("quantity",0)`).
- **Why:** when debugging an impersonation/login failure, test the WHOLE post-redirect flow, not
  just the auth endpoint — the failure is usually a downstream tenant data call, not auth itself.
- **How to apply:** never index Mongo docs with `doc["id"]` in tenant-scoped list/aggregation
  endpoints; use `.get("id")` and skip falsy ids. Tenant data integrity is not guaranteed (imports
  can insert id-less docs).
