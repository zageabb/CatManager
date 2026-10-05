# CatManager Development

## Product objective
Build a lightweight Category Management application for equipment panels and their linked suppliers. Flask is the web layer; SQLite is the initial persistence layer. The canonical interchange format remains the complete panel JSON object.

## Evidence rules
An item is complete only when the source is present, relevant tests pass, and CI passes on the commit containing the change.

## V1 — Foundation and usable panel workflow
- [x] DEV-001 Flask application factory and SQLite storage.
- [x] DEV-002 Taiju-style Category Panel portfolio based on the supplied mock-up.
- [x] DEV-003 Panel create/edit with controlled Category, Business, Region level and MDF selection.
- [x] DEV-004 User-defined supplier fields: Number, Text, Dropdown and Date.
- [x] DEV-005 Panel view with fixed supplier fields followed by custom fields.
- [x] DEV-006 Supplier add form generated dynamically from panel field definitions.
- [x] DEV-007 Raw JSON Data / Settings screen plus JSON API.
- [x] DEV-008 Automated tests and GitHub Actions CI.

## V1 next development
- [x] DEV-009 Supplier edit and delete with exact-ID confirmation and audit-safe snapshots.
  - Evidence: supplier edit/delete routes in `app.py`, edit/delete controls in `panel_view.html`, audit trail snapshots in panel metadata, behavioural tests.
- [x] DEV-010 Reversible panel archive lifecycle with explicit confirmation and restore.
  - Evidence: SQLite `archived_at` migration, archive/restore routes, archived portfolio filter, lifecycle audit entries and behavioural tests.
- [ ] DEV-011 MDF master-data administration screen; move MDF reference data from code to database.
- [ ] DEV-012 Portfolio favourites, sorting, pagination and persistent filters.
- [ ] DEV-013 True dashboard calculations including configurable spend/currency semantics and qualification review dates.
- [ ] DEV-014 Field deletion impact preview when supplier data exists; preserve orphan data until explicit migration.
- [ ] DEV-015 Import/export JSON file actions and schema-version migration.
- [ ] DEV-016 Audit log for panel schema and supplier changes.
- [ ] DEV-017 Authentication/authorization with Category Manager and read-only roles.
- [ ] DEV-018 Production configuration, CSRF protection, migrations and deployment documentation.
- [ ] DEV-019 Accessibility and responsive UI review against the reference design.
- [ ] DEV-020 Optional supplier-master integration so supplier IDs can come from an authoritative source.

## Data model decisions
1. A panel is the aggregate root and is stored as metadata columns plus a complete JSON object.
2. Custom values are keyed by immutable fieldId, never display label.
3. Region is represented by level and value.
4. Panel IDs are immutable from the raw JSON editor.
5. Schema version 2 adds append-only metadata audit and reversible lifecycle metadata. Supplier delete retains a full recovery snapshot; panel removal is implemented as archive/restore rather than destructive deletion.
