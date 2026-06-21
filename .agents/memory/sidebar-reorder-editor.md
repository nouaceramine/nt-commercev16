---
name: Sidebar reorder editor
description: How the drag-and-drop sidebar reorder page must stay in sync with the real sidebar, and the hyphen-id DnD pitfall
---

# Sidebar reorder feature

The "easiest way" to reorder sidebar sections/items already exists: the drag-and-drop page at
route `/settings/sidebar` (component `frontend/src/pages/SidebarSettingsPage.js`), reachable from
the sidebar under الإدارة/الإعدادات ← ترتيب القائمة. It saves to backend `/api/settings/sidebar-order`.

## Rule: editor defaults MUST mirror the real sidebar
`SidebarSettingsPage.js`'s hardcoded `defaultMenuSections` must mirror `tenantNavSections` in
`frontend/src/components/Layout.js`, matched by **section `id`** and **item `path`**.

**Why:** Layout applies a saved custom order by looking up each saved section by `id` and each item
by `path` against the real default section. If the editor's section ids / item paths don't match the
real sidebar, saving from the editor silently drops every unmatched item. The two lists drifted once
(editor had 13 invented sections like main/purchases/sales/admin; the real sidebar has only 4:
`main-sales`, `inventory`, `customers-finance-reports`, `services-settings`).

**How to apply:** whenever the real sidebar (`tenantNavSections`) changes, update `defaultMenuSections`
to match (same section ids, same item paths). Item labels/icons in the editor are cosmetic — only
section `id` + item `path` drive the real sidebar.

The sidebar now has **15 main sections** (was 4): `home, customers, products, purchases, sales,
expenses, finance, employees, system-users, services, repairs, ecommerce, shipping, settings,
messages-notifications`. Only `products` keeps `featureKey:'inventory'`; all other 14 are
`featureKey:null` (so their item `subFeature`s are inert, matching prior behavior). Admin-only items
keep `...(isAdmin?[...]:[])` gating — several sections (employees, system-users, shipping, settings,
messages-notifications) are fully admin-only and collapse to empty (dropped by the trailing
`.filter(s=>s.items.length>0)`) for non-admins.

## Security rule: custom-order merge must not resurrect filtered sections
In Layout's `navSections` custom-order builder, a saved section whose `id` is NOT in
`defaultNavSections` must be **skipped unless `customSection.isCustom === true`**. Built-in sections are
absent from defaults precisely because admin/feature filtering removed them; rendering them from saved
data bypasses `isAdmin` and exposes admin-only sections to non-admins. Only genuinely user-created
(`isCustom`) sections use the saved-data fallback.

## Pitfall: stale saved order → empty sidebar after a section restructure
When the section `id` set changes (e.g. the 4→15 restructure), existing tenants still have a saved
`sidebar_order` referencing the OLD ids (`main-sales`, `inventory`, `customers-finance-reports`,
`services-settings`). The security rule above skips every saved section whose id is not in defaults
and not `isCustom`, so the custom-order builder produces an EMPTY array → blank sidebar, no headings
(reported as "العناوين غير موجودة").

**Fix (in Layout `navSections` builder):** when `built.length === 0`, fall back to `defaultNavSections`
ONLY if no saved section is resolvable (`customSidebarOrder.some(cs => defaultMap[cs.id] || cs.isCustom===true)`
is false). If some ARE resolvable but the user hid them all, respect that intent (return empty).
**Why:** distinguishes a stale/incompatible config from a deliberate "hide all". Also keep the
`expandedSections` localStorage default pointed at a CURRENT section title (`['الرئيسية','Accueil']`),
not an obsolete one, or first-load shows everything collapsed.

**Note:** the saved order is stored in tenant settings but NOT in a `tenant_*`-named Mongo DB — a DB
scan filtering db names by "tenant" misses it. Verify via the API: login → `GET /api/settings/sidebar-order`.

## Pitfall: never string-split DnD ids that can contain hyphens
Sortable element ids are `section-${sectionId}` and `item-${sectionId}-${item.id}`. Section ids now
contain hyphens (`main-sales`, etc.), so parsing with `overId.split('-')[1]` truncates them and breaks
reorder/move. Read the sortable payload `over.data.current` instead (`{type, sectionId, item}` for
items, `{type, section}` for sections). `replace('section-', '')` on the prefix is still safe.

Layout dedupes `customItemPaths` with `[...new Set(...)]` to guard against duplicate menu entries from
legacy saved configs.

## Single source of truth: config/sidebarMenu.js
The canonical `defaultMenuSections` now lives in `frontend/src/config/sidebarMenu.js` (exported), imported
by both `SidebarSettingsPage.js` and the inline reorder. It must still mirror `tenantNavSections` in
Layout (section `id` + item `path`). Update this one file when the real sidebar changes.

## Inline reorder in the live sidebar (SidebarReorder.js)
`frontend/src/components/SidebarReorder.js` gives a drag-to-reorder UI directly in the sidebar, toggled by
an admin-only entry button in `Layout.js` (`isAdmin && !isSuperAdmin`, sidebar not collapsed). Scope:
reorder whole sections + reorder items WITHIN a section (no cross-section move — the `/settings/sidebar`
page handles that). dnd-kit: single `DndContext`, namespaced ids `S::<id>` and `I::<sectionId>::<path>`,
type checks via `*.data.current`.

**Save contract (critical):** inline reorder must only change ORDER, never reset visibility or lose custom
metadata. It MUST first GET `/settings/sidebar-order` (shape `{sidebar_order:[...]}`) and MERGE the new
order onto that saved base (fallback canonical only when nothing saved). Carry forward each item/section's
`visible` flag, `titleAr/titleFr`, `labelAr/labelFr`, `icon` id, `isCustom`; append hidden/not-shown base
items & sections preserving their flags. **Why:** rebuilding the payload from scratch forces `visible:true`
on everything → re-enables items the user hid and clobbers custom sections. Block save on a real GET
failure (distinct `loadError` from empty-but-ok) so a transient error can't overwrite saved order with
canonical. PUT body is a **bare array** (not wrapped); then dispatch `sidebarOrderChanged` so Layout re-reads.
