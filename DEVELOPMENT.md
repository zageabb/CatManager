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
  - Panel qualification uses the worst supplier status: Not qualified > In review > Qualified; unknown non-empty states are treated conservatively at review severity, and empty panels show No data. Historical Europe Hub demo panels include generated qualification examples so the rule is visible during demonstrations.
- [x] DEV-014 Field deletion impact preview with preserved orphan data and explicit migration actions.
  - Evidence: removing a populated custom field first shows affected supplier counts/examples and requires confirmation; removed definitions are stored under `metadata.orphanedSupplierFields` while supplier values remain untouched; panel view surfaces orphan management; users can restore the field with all values intact or explicitly purge orphan values using exact field-ID confirmation; purge snapshots remain in the audit trail; behavioural tests.
- [x] DEV-015 Import/export JSON file actions and schema-version migration.
  - Evidence: portfolio Import Panel workflow accepts JSON schema versions 1–3, migrates older MDF/metadata structures to schema 3, validates controlled values and MDF master references, requires explicit replacement for existing Panel IDs, and persists searchable metadata consistently; panel view offers downloadable JSON export; future schema versions are rejected; behavioural tests.
- [x] DEV-016 User-facing audit log for panel schema, supplier, lifecycle, import and raw-data changes.
  - Evidence: audit events now carry stable event IDs, actor, entity ID, timestamp, action and structured details; panel create/edit records schema and metadata diffs; supplier create/edit/delete/bulk changes and field-orphan actions remain append-only; panel import/replacement and raw JSON edits preserve prior history and append new events; `/panels/<id>/audit` provides searchable/filterable history with expandable details; panel detail shows the audit-event count; behavioural tests.
- [ ] DEV-017 Authentication/authorization with Category Manager and read-only roles.
- [ ] DEV-018 Production configuration, CSRF protection, migrations and deployment documentation.
- [ ] DEV-019 Accessibility and responsive UI review against the reference design.
- [x] DEV-020 Supplier-master integration with CSV import, BPID/name typeahead, generated placeholder addresses, and reversible removal.
  - Evidence: SQLite `supplier_master` table; `/settings/suppliers` CSV import/update screen; missing addresses receive deterministic generic placeholders marked `address_source=generated`; suppliers can be removed from active selection and restored; `/api/supplier-master/search` searches BPID or Supplier Name; Add Supplier typeahead populates fixed fields from the master; behavioural tests.
- [x] DEV-021 Historical ABB demo panels for Europe Hub.
  - Evidence: curated panel/supplier data derived from `Dynamic Supplier Panel 07Sep2021.xlsm` is stored in `legacy_demo_data.py`; demo seeding creates Europe Hub panels for transformers, cables, MV switchgear, instrument transformers, civil works, engineering services and protection/control; old ABB MDF references are retained as inactive legacy MDF master entries; workbook-only supplier attributes are represented as custom fields; missing fixed addresses use deterministic generic demo addresses; behavioural tests verify region, legacy metadata and field mapping.

## Data model decisions
1. A panel is the aggregate root and is stored as metadata columns plus a complete JSON object.
2. Custom values are keyed by immutable fieldId, never display label.
3. Region is represented by level and value.
4. Panel IDs are immutable from the raw JSON editor.
5. Schema version 3 adds multi-MDF panels (`mdfCodes` + `leadMdfCode`) while retaining legacy `mdfCode` as the lead MDF for compatibility. Append-only audit and reversible lifecycle metadata continue from version 2.

6. Schema version 4 adds panel-level ordered `fieldGroups`; custom field definitions reference groups through stable `groupId`, while supplier custom values remain keyed exclusively by immutable `fieldId`. Missing/legacy grouping is represented as Ungrouped and existing schema-3 panels migrate non-destructively.

- [x] DEV-022 Custom field groups, grouped supplier forms, and existing-panel migration.
  - Evidence: schema version 4 adds ordered panel-level `fieldGroups` with stable `groupId` references on custom field definitions while supplier values remain keyed only by immutable `fieldId`; the panel editor can create, rename, reorder, delete and assign groups; supplier add/edit renders visible grouped sections with an Ungrouped fallback; the bulk editor renders matching grouped column bands; existing stored schema-3 panels are migrated automatically on application startup without changing supplier values; schema 1–3 JSON imports migrate to schema 4; historical ABB demo panels are seeded with sensible groups; behavioural tests cover grouped rendering and an in-place existing-database migration. CI run 37606765991 passed on commit a1eab991ec4bafbeec3b3b8b73a818f7b527855f.

- [x] DEV-023 Separate panel metadata editing from panel configuration.
  - Evidence: Edit Panel now contains only core panel metadata (Panel ID/name, category, business, region, owner and MDF selections); custom supplier fields and field groups are managed on the dedicated /panels/<id>/configuration Panel Configuration page; panel detail exposes both actions separately; metadata edits preserve the existing field schema; configuration changes retain field-removal impact preview, orphan preservation/restoration semantics and dedicated audit events; behavioural tests verify the separation and existing custom-field workflows. CI run 37608778960 passed on commit 5c99d58ba76a651a923270f681be632bd41b5ba9.

## V3 — Panel reuse and supplier reporting (baseline tag: Version_2_Demo)
- [x] DEV-024 Duplicate panel configuration into a newly named/identified panel. Copy metadata, MDF selection, field groups and field definitions (and future widget definitions) but **never** supplier rows, archived state, orphaned supplier data or audit history. Validate uniqueness and keep source unchanged. Add behavioural tests.
  - Evidence: new duplicate route, prefilled create form, independent JSON aggregate with no supplier or audit copy, regression tests; PR CI run 37766497820 succeeded on efcd74f5539004c01ec0e83785b986f05cef10ef.
- [x] DEV-025 Reusable SQLite-managed custom-field template library. Selecting a template creates a new independent field ID and copies name, type and options; allow saving a panel field as a template.
- [x] DEV-026 Boolean supplier field with separate true/false/unset state, checkbox or Yes/No editing and accessible colour block in read-only tables. Preserve existing data and migration compatibility.
- [x] DEV-027 Up to six panel-specific KPI cards with count, conditional count, sum, average, min, max, distinct count, percent and bounded arithmetic on aggregations; configurable formats, safe zero division and currency handling. Expose configuration under Panel Configuration and preserve definitions on panel duplicate/import/export.

## V3 execution rule
Build on feature/v3-panel-enhancements; keep `Version_2_Demo` immutable. Update this file before each development stage, add regression tests and record verification evidence only after tests and commit-specific CI pass.

## V3 implementation notes
- DEV-025: `field_templates` SQLite table, seeded electrical equipment field examples, /api/field-templates GET/POST, add-from-template and save-to-library buttons in Panel Configuration. Each insertion creates a new independent field ID (no shared binding), with field type and dropdown options copied. Regression test verifies isolation.
- DEV-026: `boolean` joins allowed custom field types; supplier edit and bulk edit accept true/false/unassessed values; normal view shows text-labelled green/red/grey blocks. Reversible values preserved as JSON booleans/null. Regression test verifies all three states.
- DEV-027: `dashboardWidgets` definitions in canonical panel JSON (up to six), editable from Panel Configuration; count, conditional count, distinct, sum, average, min, max, ratio and percentage supported with safe zero-division. Aggregations update on supplier edits, currency-aware sums use existing Spend/currency dashboard mappings, and invalid/unconverted values are surfaced. Duplication preserves widgets without data. Regression tests verify calculations, six-widget limit, currency conversion and duplication.
- Schema v5 migration adds `dashboardWidgets: []` to older panels without changing supplier values, accepts older JSON imports and validates widget definitions; `metadata.version` is synchronized with v5. V2 demo remains frozen at `Version_2_Demo`.
- Validation rule: mark completion evidence authoritative only after CI passes for the final commit; CI run URL and SHA should be recorded before merging.

- [x] DEV-028 Supplier-level KPI calculated columns. Add panel/supplier/both visibility per existing widget (backward-compatible default: panel); calculate each supplier row with the same source fields, base-currency conversion, missing-value and zero-denominator safeguards as the panel KPI; supplier columns are read-only. Extend tests for view settings and calculations. Merge to main after CI passes for UDA.
  - Evidence: Panel Configuration now offers Panel KPI / Supplier column / Both per widget; supplier table renders read-only derived values, preserving currency conversion and zero-division behaviour, and defaults older widgets to panel-only. Added regression tests; CI run 37769925273 passed on d2bad128b06eb117c618c3107047682933ba9e2b.

- [x] DEV-029 Star Rating custom type (0–5 in half-point steps), numeric editing/validation, accessible star display in supplier list, reusable templates, star-formatted KPI cards and supplier KPI columns, tests and CI before merge to main.
  - Evidence: `stars` type with half-step supplier numeric editing; validated 0–5 range on supplier create/edit/bulk edit; accessible stars in the supplier list and star-formatted dashboard/supplier KPI values; predefined quality rating field; regression test. PR CI run 37777729624 passed on f9baef933407fd69c68c1b7f943dfc197c025082.

- [x] DEV-030 Multi-Select Colour Blocks: one configurable options field (e.g. EU/MED/MEA/NAM/LAM/APAC), checklist supplier editing and bulk grid, one supplier-table cell with adjacent green/neutral labelled segments. Store selected option values as JSON arrays, reject unknown selections, preserve existing suppliers and shared field-template support. Regression tests + passing CI before main merge.
  - Evidence: `multiselect_blocks` field stores validated selected-option arrays; Panel Configuration edits labels/options; supplier forms and bulk editor use checkboxes; supplier table renders all configured option segments with green/neutral status. New regression test validates multi-select persistence, view, bulk edits, invalid values and clearing. CI run 37778592840 passed on commit 30c3bc56b040992b26e3e7d13db8cafa02ac9392.

- [x] DEV-029 follow-up: make star KPI setup explicit: choose numeric/star source field, choose Average/Minimum/Maximum (and other numeric metrics where appropriate), and select Stars/Number/Both output independently from panel/supplier display location. Validate star formatting uses a suitable custom field and meaningful metric. Add regression tests, pass CI, merge to main for UDA.
  - Evidence: numeric/star field selector in KPI editor, Average/Minimum/Maximum constraints for star output, Stars/Number/Stars and number formats, server validation, behavioural regression test. PR CI run 37779062414 passed on 98bf2efea760b4948cd4ce6b95b1027fecf9c638.

- [x] BUG-031 MDF multi-select search: CSS `.mdf-option{display:flex!important}` overrides rows' `hidden` property. Ensure live case-insensitive filtering by code and description actually hides non-matching options, while preserving selected MDFs and Lead MDF. Add a regression guard and pass CI prior to main/UDA merge.

  - Evidence: CSS `[hidden]` override prevents forced flex styling from showing filtered-out MDF rows; regression checks CSS/JS/template contract. PR CI run 37810061015 passed on 79d02261790fe1105356dfc42eab43d9c1d22a70.


## Version 3 baseline and proposed development (management ideas register, 08 October 2026)
- **Delivered Version 3 baseline:** commit `967e48ae8fc9f980032934c23cd38b6bb38af585` on `main`, incorporating V3 enhancements DEV-024–DEV-030, DEV-029 refinement and BUG-031. Original immutable V2 demo tag: `Version_2_Demo` at `384bac5588bd1a633754a108c5ebbbc85572b16a`.
- **Requested release tag:** `version3`, pointing to baseline commit above. **NOT CREATED**; connected GitHub write actions do not expose creation of Git tags. To create using an authenticated repository clone: `git tag version3 967e48ae8fc9f980032934c23cd38b6bb38af585 && git push origin version3`. Verify the ref before creating to avoid replacing an existing tag.
- **Scope distinction:** Items below are **proposals only** for discussion, not approved, implemented or part of the delivered version3 code baseline. Existing DEV-017–019 remain unfinished.
- **Design principles:** preserve panel-specific custom field IDs and JSON contract; link cross-panel suppliers by BPID where available; use reversible migrations and audited changes; stage work by value/risk.

### Proposed V3+ ideas backlog — not approved
| Ref | Priority | Proposal | Indicative effort | Outcome |
| --- | --- | --- | --- | --- |
| DEV-032 | High | Supplier table filtering/sorting by all custom field types | Medium | Find matching suppliers faster |
| DEV-033 | High | Configurable supplier columns: visibility/order/sticky ID/name/saved view | Medium | Keep wide panels usable |
| DEV-034 | High | Excel export/edit/re-import with preview, validation and conflict safety | Medium–High | Scale supplier updates |
| DEV-035 | High | Guided KPI designer with live calculation/display preview | Medium | Easier self-service reporting |
| DEV-036 | High | Side-by-side selected-supplier comparison | Medium | Support evaluation decisions |
| DEV-037 | High | Unsaved changes navigation protection | Low | Reduce accidental data loss |
| DEV-038 | Medium | Weighted supplier scoring with transparent criteria and evidence | Medium–High | Consistent evaluation |
| DEV-039 | Medium | Supplier actions/owners/due dates and follow-up tracking | Medium | Close qualification gaps |
| DEV-040 | Medium | Configurable review/expiry notifications and dashboard flags | Medium | Proactive qualification upkeep |
| DEV-041 | Medium | Regional/MDF coverage and single-source risk analysis | Medium | Identify sourcing gaps |
| DEV-042 | Medium | Governed reusable panel templates | Medium | Consistent panel setup |
| DEV-043 | Medium | Supplier trend history and field-change comparison | Medium | Explain progress |
| DEV-044 | Future | Shareable management summaries (Excel/PDF) | Medium | Communicate panel results |
| DEV-045 | Future | Cross-panel BPID-linked supplier profile | High | One supplier across categories |
| DEV-046 | Future | Data-quality/completeness dashboard | Medium | Trustworthy assessment data |
| DEV-047 | Future | Governed supplier-master synchronisation | High | Reduce manual reference upkeep |
| DEV-048 | Foundation | Complete DEV-017/018 authentication, access controls, CSRF, migrations and production readiness | High | Safe broader rollout |

### Proposed sequencing and decision gates
1. **Usability first:** DEV-032, DEV-033 and DEV-037; validate on panels with large custom-field sets.
2. **Data maintenance and comparison:** DEV-034, DEV-035 and DEV-036; demonstrate time saved and decision quality.
3. **Category intelligence:** DEV-038–043; agree scoring and qualification policies with business owners.
4. **Scale and govern:** DEV-044–048 plus existing DEV-017/018/019; agree data owners, deployment and permissions before multi-user expansion.
5. **Management review required:** prioritise and size the options above before implementation. No delivery dates or ROI claims have yet been validated.


### Current implementation: DEV-032 (supplier table filtering and sorting)
- [x] DEV-032: Local supplier table keyword search, field-specific filters for fixed and custom fields, and type-aware column sorting (including numeric/star, boolean and selected region values); do not modify data or disrupt row actions. Regression tests and CI required before main merge.
  - Evidence: field-specific or all-column live keyword search, visible results count, reset, numeric/star-aware sorting and per-field values for regions/boolean states. Server-side supplier data remains unchanged. Tests pass in PR CI run 37812669255, commit 50f4a3491f2628668fabda8f39bab76db8764e9c.

### Current implementation: DEV-033 (supplier column views)
- [x] DEV-033: On the supplier table, configure visible columns, reorder nonessential columns with up/down controls, keep Supplier ID/Name and Actions fixed, and save view preferences per panel in browser storage. Maintain DEV-032 search/sort correctness when columns move or are hidden; tests and CI before main merge.
  - Evidence: browser-local per-panel saved column visibility and order, fixed Supplier ID/Name/Actions, optional column movement, reset to default, original cell-index lookup retains DEV-032 filtering/sorting semantics. Regression tests passed, CI run 37813713324 on fb8c8bd4c2bd9baf4ace463500f8423235103efa.

### DEV-037 — Unsaved changes protection
- [ ] Add dirty-form navigation warnings on panel metadata/configuration, supplier edit/new, and bulk edit. Track user input/change (including dynamic widgets), avoid warning on successful form submission or unchanged forms, and use native beforeunload to cover reload/browser navigation. Regression tests and CI required.
