---
name: Unified document print system (Phase 1)
description: How per-record print/preview works and why it coexists with the older POS/barcode print code
---

# Unified document print system (Phase 1)

A preset-template print/preview system for per-record printing across Customers, Products,
Purchases, Sales, Expenses. Thermal 58/80mm + A4, RTL, accent color, logo/header/footer/columns toggles.

- Builder: `frontend/src/lib/printDocuments.js` — `buildPrintHTML({docType,record,options,branding,language})`.
  Uses `formatCurrency` from `globalDateFormatter` (already appends دج/DA — never re-append).
  `safeImageUrl()` allowlists data:image/http(s)/blob for the logo (XSS guard for iframe srcDoc).
- UI: `components/print/PrintDocumentDialog.js` (iframe srcDoc preview, paper-size switch, prints via
  `iframe.contentWindow.print()` gated on iframe `onLoad`, logs to POST `/printing/log`) and
  `components/print/PrintButton.js` (per-row icon button).
- Settings: options persist in receipt settings under key `document_print[docType]`, edited in
  `pages/settings/PrinterTab.js`. Read at print time via GET `/settings/receipt` + GET `/settings/tenant-branding`.

**Why it coexists with old print code:** POS thermal receipt (`generateThermalReceiptHtml`/`printThermalReceipt`
in POSPage.js via window.open), BarcodePrintPage, and ExportPrintButtons (list CSV/Excel/print) were
left untouched on purpose — consolidating them risked breaking working flows. This system is additive.

**Phase 2 (Task: visual drag-drop template editor)** is the planned follow-on; not built yet.
