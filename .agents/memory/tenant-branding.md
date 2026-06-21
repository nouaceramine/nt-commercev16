---
name: Tenant branding (sidebar logo + name)
description: How per-tenant custom logo/name is stored and surfaced in the RTL sidebar
---

# Tenant branding

Each tenant can set a custom logo + display name shown at the TOP of the right RTL sidebar (next to/replacing the NT shield), plus on the mobile header.

- **Storage:** tenant-scoped `db.settings` doc with `key: "tenant_branding"`, `value: {name, logo_url}`. Mirrors the receipt-settings pattern in `system_sync_routes.py` (module-level `db` is already tenant-scoped; do NOT reach for `main_db` here).
- **Endpoints:** `GET /api/settings/tenant-branding` (any tenant user; falls back to `user.company_name` then empty) and `POST` (tenant admin only). Logo is a base64 data URL uploaded client-side via FileReader (capped ~512KB in `BrandingTab`).
- **Frontend refresh convention:** after saving, `BrandingTab` dispatches a `window` event `branding-updated`; `Layout` listens for it (and fetches on mount) to re-pull branding without a reload. Display name resolves as `branding.name || user.company_name || t.appName`.

**Why:** branding must be per-tenant in this multi-tenant SaaS; using tenant-scoped `db.settings` keeps it isolated automatically, and the custom window event avoids a full page reload after edits.

**How to apply:** any new place that shows the app name/logo should read the same `/settings/tenant-branding` and listen to `branding-updated`, not hardcode `t.appName`/Shield.
