# CatManager Development

## Product objective
Build a lightweight Category Management application for equipment panels and their linked suppliers. Flask is the web layer; SQLite is the initial persistence layer. The canonical interchange format remains the complete panel JSON object.

## Evidence rules
An item is complete only when the source is present, relevant tests pass, and CI passes on the commit containing the change.

## V1 — Foundation and usable panel workflow
- [x] DEV-001 Flask application factory and SQLite storage.
- [x] DEV-002 Taiju-style Category Panel portfolio based on the supplied mock-up.
- [x] DEV-003 Panel create/edit with controlled Category, Business, Region level and multi-MDF selection with one Lead MDF.
  - Evidence: panel form supports multiple MDF selections; canonical JSON stores `mdfCodes` plus `leadMdfCode`; legacy `mdfCode` remains the lead for compatibility.
- [x] DEV-004 User-defined supplier fields: Number, Text, Dropdown and Date.
- [x] DEV-005 Panel view with fixed supplier fields followed by custom fields.
- [x] DEV-006 Supplier add form generated dynamically from panel field definitions.
- [x] DEV-007 Raw JSON Data / Settings screen plus JSON API.
- [x] DEV-008 Automated tests and GitHub Actions CI.

## V1 next development
- [x] DEV-009 Supplier edit and delete with exact-ID confirmation and audit-safe snapshots.
  - Evidence: supplier edit/delete routes in `app.py`, edit/delete controls in `panel_view.html`, audit trail snapshots in panel metadata, behavioural tests.
- [x] DEV-009A Existing supplier maintenance after panel-field changes, using two edit methods.
  - Method 1: click Supplier ID/name to open the normal supplier edit screen with the current panel field schema.
  - Method 2: "Edit supplier data" opens a spreadsheet-style grid where fixed fields are read-only and only custom fields are editable.
  - Evidence: `supplier_bulk_edit` route, `supplier_bulk_edit.html`, clickable supplier links, automatic display of newly-added custom fields, bulk-change audit entries and behavioural tests.
- [x] DEV-010 Reversible panel archive lifecycle with explicit confirmation and restore.
  - Evidence: SQLite `archived_at` migration, archive/restore routes, archived portfolio filter, lifecycle audit entries and behavioural tests.
- [x] DEV-011 MDF master-data administration screen with SQLite-backed reference data.
  - Evidence: `mdf_codes` table and seed migration, `/settings/mdf` administration, active/inactive controls with in-use guard, panel-form selector sourced from database, behavioural tests.
- [x] DEV-011A Scalable MDF selection for the full catalogue.
  - Evidence: supplied MDF catalogue loaded from `data/mdf_codes.json`; panel create/edit uses a compact searchable multi-select dropdown with selected chips; Lead MDF dropdown is restricted to selected MDFs.
- [x] DEV-012 Portfolio favourites, sorting, pagination and persistent filters.
  - Evidence: persistent SQLite favourite flag and toggle route; Favourites portfolio tab; sortable portfolio headers; configurable 10/20/50/100 row pagination; session-backed search/category/business/sort/page-size persistence with Reset; behavioural tests.
- [x] DEV-013 True dashboard calculations with configurable spend/currency semantics and qualification review dates.
  - Evidence: `/settings/dashboard` maps supplier field IDs to dashboard meanings; configurable base currency and manual conversion rates; active-panel spend is converted before aggregation while unknown currencies are surfaced separately; top suppliers are calculated from live records; qualification status is dynamic; qualification review dates are bucketed into overdue, due within 30 days, future, missing/invalid; portfolio row spend uses the configured base currency; behavioural tests.
- [ ] DEV-014 Field deletion impact preview when supplier data exists; preserve orphan data until explicit migration.
- [ ] DEV-015 Import/export JSON file actions and schema-version migration.
- [ ] DEV-016 Audit log for panel schema and supplier changes.
- [ ] DEV-017 Authentication/authorization with Category Manager and read-only roles.
- [ ] DEV-018 Production configuration, CSRF protection, migrations and deployment documentation.
- [ ] DEV-019 Accessibility and responsive UI review against the reference design.
- [x] DEV-020 Supplier-master integration with CSV import, BPID/name typeahead, generated placeholder addresses, and reversible removal.
  - Evidence: SQLite `supplier_master` table; `/settings/suppliers` CSV import/update screen; missing addresses receive deterministic generic placeholders marked `address_source=generated`; suppliers can be removed from active selection and restored; `/api/supplier-master/search` searches BPID or Supplier Name; Add Supplier typeahead populates fixed fields from the master; behavioural tests.

## Data model decisions
1. A panel is the aggregate root and is stored as metadata columns plus a complete JSON object.
2. Custom values are keyed by immutable fieldId, never display label.
3. Region is represented by level and value.
4. Panel IDs are immutable from the raw JSON editor.
5. Schema version 3 adds multi-MDF panels (`mdfCodes` + `leadMdfCode`) while retaining legacy `mdfCode` as the lead MDF for compatibility. Append-only audit and reversible lifecycle metadata continue from version 2.
