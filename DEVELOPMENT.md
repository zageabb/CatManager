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
- [x] Add dirty-form navigation warnings on panel metadata/configuration, supplier edit/new, and bulk edit. Track user input/change (including dynamic widgets), avoid warning on successful form submission or unchanged forms, and use native beforeunload to cover reload/browser navigation. Regression tests and CI required.
  - Evidence: editing forms marked with data-unsaved-guard; browser beforeunload and navigation confirmations react to user edits, including dynamic editors; normal save submissions bypass warning. Regression tests, PR CI run 37814176992 passed on 561c48e4e6b5544733f8d2742f798378d0e5a708.

### DEV-034 — Excel supplier round-trip (in progress)
- [x] Export a native XLSX workbook containing panel ID, field-ID-aligned editable supplier custom values and an integrity baseline. Import must validate exact supplier IDs, column fields, value types and initial baseline, show a preview without changes, and require explicit confirmation before atomic audited application. Preserve fixed supplier master data; no silent updates. Tests and CI before merging.
  - Evidence: supplier_excel.py exports native .xlsx and enforces strict per-field validation including stars, regions and booleans; signed 30-minute preview and conflict checks block stale edits before atomic save and audit. UI actions are available on panel view. Regression tests passed in CI 37820844135 on 98d1514b127c9a2eaa8ec295a1cefdd5f718ba66. Additional text safety fix on ecfc065aadec1ca16f4291bb6922e40fd44a67c8; verify final CI before merge.

### DEV-035 — Guided KPI designer with live preview
- [x] Introduce clearer KPI configuration (title, calculation, source, matching value/denominator, format, location) and a live read-only server-calculated preview using the panel's supplier records and existing KPI calculation functions. Preview must not save configuration; invalid drafts should show helpful validation. Add regression tests and merge after CI.
  - Evidence: guided configuration instructions, preview endpoint using the shared dashboard widget parser and calculator, current supplier data, live updates and non-persisting preview. Tests verified average calculation, rejected invalid field, and no panel mutation. CI run 37821349198 passed on b5d0b43889a5cfa695633fb65bea2ddd8d8170d3.

### DEV-036 — Supplier comparison
- [x] Read-only comparison of 2–5 suppliers within one panel, showing fixed attributes, configured custom field values, ratings, multi-region coverage, and calculated supplier KPIs. Selection via supplier-table checkboxes; validate duplicate/unknown IDs and preserve panel data. Add regression tests and CI before main merge.
  - Evidence: selected 2–5 supplier IDs, guarded route, read-only side-by-side fixed and custom attributes, star and region rendering, supplier KPI values; fixed table column-index compatibility. Regression suite passed in PR CI 37831468013 for 33a361624ef8e5da2b6e97e5da7e65e813c40747.

### DEV-038 — Weighted supplier scoring (in progress)
- [x] Configure panel-specific weighted scoring from numeric/star fields (0–5 scale), requiring positive weights and valid source fields. Display transparent per-supplier total score and missing-data status in a read-only comparison/scorecard. Save configuration with panel JSON, preserve no-score behaviour, test and pass CI before main merge.

  - Evidence: `supplier_scoring.py` validates unique 0–5 numeric/star criteria with positive finite weights and computes complete-case weighted averages without persisting results. Panel Configuration edits rules and panel view shows component scores/missing values. Regression tests and PR CI 37833386400 passed on commit 98fcc2049262aa294c91e6b81724f3052c8d1824.

### DEV-039 — Supplier actions (in progress)
- [x] Add supplier-specific actions with description, owner, due date and Open/In progress/Completed status. Provide create/update workflow and list, validate inputs, preserve records in panel JSON and append audit events. Regression tests, successful CI and merge to main required.

  - Evidence: supplier-scoped action form and list, creation/update with owner, due date, status and audit snapshots; archived panels are read-only. Behavioural tests passed in PR CI run 37834017837 on ee87994700c6c284289ac9f6d0958ce70491c0fd.

### DEV-040 — Qualification review alerts
- [x] Surface existing qualification review dates as actionable per-supplier alerts (overdue, due within 30 days, later, missing or invalid), with links to edit supplier, plus overdue/open action due dates. Respect configured dashboard review field and preserve read-only data. Add tests and pass CI before merge.

  - Evidence: read-only supplier review and action alerts, due/overdue thresholds, missing/invalid categorisation, and direct edit/action links. Regression tests passed, PR CI 37834736853 on ee85ef0cba7176778080628243eb3d1982683286.

### DEV-041 — Supplier coverage and sourcing concentration
- [x] Add read-only coverage summary from configured multi-select regional fields, distinguish coverage records from qualified supplier counts, flag uncovered regions and single-source regions, and show panel MDF scope without inventing supplier-to-MDF mappings. Regression tests and passing CI before merge.

  - Evidence: derived multi-select region coverage, qualification counts, empty/single/multi supplier concentration, explicit panel-only MDF interpretation and display. Regression tests passed in CI 37835126854 at d95de44d703fcad793ee85172c438833ea898c2c.

### DEV-042 — Governed reusable panel templates
- [x] Allow creating a named reusable template from a panel's configuration (field groups, field definitions, KPI widgets and scoring criteria), listing templates, and creating new independent panels from a template without copying supplier records or audit history. Include input validation, snapshot semantics, regression tests and CI before main merge.

  - Evidence: SQLite-backed immutable snapshots of field groups, field definitions, dashboard widgets, and scoring criteria; template library and independent panel creation. Supplier data and prior audit history are excluded. Regression test and PR CI run 37835782381 passed on 3bd4847dc0e24e8efee436381db76d950c0921f4.

### DEV-043 — Supplier change history and trends
- [x] Read-only supplier history from audit entries for supplier edits, bulk edits, Excel imports and action updates, with field-by-field before/after values, dates, actors and numeric rating history. Must handle old and missing audit records without fabricating trends; test and pass CI before main merge.

  - Evidence: supplier_history.py reconstructs exact per-field change records from direct edits, supplier action changes, Excel and bulk imports; shows audited numeric values without inventing historical states. Regression tests passed, PR CI 37839253145 on 8bf15bc370c35b622d9114caead9ea5c84758db7.

### DEV-044 — Management summary reports
- [x] Deliver a shareable Excel management workbook for one panel: overview, supplier qualification and weighted scores, region sourcing risks, review alerts and open actions. Derive values from existing calculations, include reporting timestamp, preserve existing records and include regression tests. Add printable HTML management view if suitable. Verify CI before merge.

  - Evidence: current-state XLSX with overview, supplier qualifications and weighted scores, regional source risks and open actions, plus a print-friendly HTML summary that can be saved to PDF. Audit and supplier JSON remain untouched. Regression tests passed in PR CI 37839978557 on e28059d103e39a6751a1b034c2295e85f503c2f1.

### DEV-045 — Cross-panel supplier profile
- [x] Add read-only supplier profile keyed by exact BPID/supplierId across active and archived panels, showing panel memberships, qualifications, review dates, weighted scores, regional selections and open actions; explicitly avoid merging similar names or treating panel-specific values as global. Link from supplier table; tests, CI and merge.

  - Evidence: exact supplierId cross-panel read-only profile with memberships, qualification, review status, weighted scores, coverage and open actions. Same-named different BPIDs remain separate. Regression tests passed in PR CI run 37841687467 on commit 432df803c4e49921cf784b245c6c13f8ff456fcb.

### DEV-046 — Data quality dashboard
- [x] Add a read-only, cross-panel quality dashboard highlighting missing supplier identity and configured required fields, invalid star/number/region selections, absent review dates, orphaned custom-field values, and broken scorecard references. Group findings by panel and supplier with direct remediation links, no silent repair. Add regression tests and verify CI before merge.

  - Evidence: read-only `/data-quality` dashboard highlights missing identity/required values, invalid star, numeric and multi-select coverage values, missing/invalid configured review dates, orphan custom values, and invalid KPI/scoring field references; findings link to panels/suppliers. Regression tests passed in PR CI 37846055675 for b1f7e013aa4fa1e5c1a09a9189ce8927623e167e.

### DEV-047 — Governed supplier master synchronisation
- [x] Provide panel-scoped supplier master difference preview for exact active BPID matches only. Require a confirmation token bound to current master and panel values, protect archived panels, and audit every applied update. Never touch supplier custom assessments or unknown/inactive master records. Add behavioural tests, verify CI, merge to main.
  - Evidence: signed 30-minute per-panel preview, exact active BPID comparison for name/address/postcode, live conflict checks before applying changes, supplier-scoped audits, unchanged custom fields and archived panel guard. CI 37847400890 passed at fee5452dbf75df6f4e09450e2dbfb3fbd6ccf597.

### DEV-048 — Application security and migrations (phase 1)
- [x] Introduce explicitly opt-in CSRF enforcement with signed session tokens and legacy-compatible HTML form injection, production secret validation, secure cookie defaults and numbered SQLite migration ledger. Preserve test compatibility; add security and migration regression tests, pass CI. Full multi-user authentication/authorization remains separately scoped; do not claim it is delivered.

  - Evidence: `CATMANAGER_CSRF_ENABLED=1` turns on server-side form token checks with token injection for rendered POST forms; `CATMANAGER_REQUIRE_STRONG_SECRET=1` rejects the default secret; idempotent `schema_migrations` baseline registry added. Session cookie HttpOnly/SameSite defaults. Tests passed in PR CI 37849637149 on 30e4687107db4b7ded853682e1e5c73a4b9db350. NOTE: protection is opt-in for compatibility; this is not a multi-user authentication or role-based access control system. Subsequent numbered migrations and authentication remain pending security tasks.

### BUG-049 — KPI preview JSON failure after CSRF rollout
- [x] Panel Configuration KPI live preview must supply session CSRF token on its JSON POST, return a clear error for non-JSON responses, and continue to work under enforced CSRF. Add an end-to-end regression and re-run CI before merge.
  - Fix: pass server-provided session CSRF token in X-CSRF-Token for JSON preview requests and detect non-JSON HTTP responses. Regression tests verified CSRF-enabled panel creation, rejected tokenless preview and successful token-authenticated JSON preview. PR CI 37851308714 passed at cb1eaca291e6fc283c4d8202f83b2ab7f00b0fcf.

## Approved future UX redesign — supplier-first panel (documentation only)
- [x] **UX-051** Supplier workspace as default panel view; three primary actions and grouped overflow menu; tab sections for intelligence. Specification: [Supplier-first UX spec](docs/SUPPLIER_FIRST_PANEL_UX_SPEC.md).
- [x] **UX-052** Supplier-first table polish (compact KPI strip, search/filter/column settings, row menus, responsive wide fields).
- [ ] **UX-053** Card-based Panel Configuration hub, with existing workflows preserved and focused sections introduced incrementally.
- [ ] **UX-054** Accessibility, CSRF/security regression, layout smoke tests, screenshots and release notes.
  - Implementation guide: [Supplier-first implementation plan](docs/SUPPLIER_FIRST_PANEL_IMPLEMENTATION.md). **These are approved plans, NOT completed development. Do not change live UI in this docs-only change.**

### UX-051 implementation — in progress
- [x] Reorder supplier content first, add tab navigation, keep edit/configuration/add supplier and move secondary actions to grouped menu; preserve existing endpoints, tests, and CI.
  - Evidence: supplier list and compact configured KPI strip default, header Edit Panel / Panel Configuration / Add Supplier, grouped actions overflow, and Overview, Dashboard, Scoring, Actions, History server-selected tabs. Existing KPI/scoring/coverage regression tests were redirected to relevant tab; all tests passed in CI run 37855882265 on ed640a8a189d1df485ac465cce27c040adb0f807. UX-052–054 remain future stages.

### UX-052 implementation — in progress
- [x] Replace crowded supplier-row buttons with an accessible actions menu, keep comparisons, filtering, sorting and column preferences, and improve responsive wide-table controls. Preserve deletion confirmation, CSRF, and all existing actions. Verify CI and merge only when green.
  - Evidence: supplier row contextual menu with Edit, Actions, History, Cross-panel Profile, and safeguarded Delete; responsive table scroll, clearer search/filter controls, and Esc/outside-click dismissal. Preserved comparison and browser column settings. All 82 tests passed in PR CI 37898627208 at c7708bd353e5636a1ec613b2f0dd9255e10f5e65. UX-053–054 remain planned.


### DEV-050 — Moveable and groupable fixed supplier fields
- [ ] Extend Panel Configuration so fixed fields (Supplier ID, Supplier Name, Address, Post Code) can be assigned to any existing/new field group or Ungrouped, and reordered alongside custom fields with accessible move controls. Fixed fields remain mandatory, non-deletable, and retain immutable storage keys and supplier-master semantics.
- [ ] Introduce a single panel-level display layout (stable references distinguishing fixed-field keys from custom field IDs), with a backward-compatible migration/default for existing panels, JSON imports/exports, duplicated panels, and reusable panel templates. Never change supplier data or audit history during layout migration.
- [ ] Apply the configured group/order consistently to supplier create/edit forms and grouped bulk editing where applicable. Preserve existing supplier list column preferences and protected identity/action columns; avoid inadvertently changing supplier-master sync and Excel round-trip behaviour.
- [ ] Include validation for unknown/duplicate field references, deleted custom fields, deleted/reordered groups, and accessible movement; add migration and behavioural regression tests. Update AGENTS.md only if new architectural rules are introduced, then run pytest and commit-specific CI before marking complete.
  - Product intent: treat fixed fields as fixed **data definitions**, not fixed **visual positions**. In legacy configurations, display fixed fields first in their existing order, followed by custom fields, until explicitly reordered.

  - Implementation progress (2026-10-09): shared fixed/custom `fieldLayout` reference list, server-side duplicate/missing/group validation, Panel Configuration ordering/group selection, supplier add/edit grouped rendering, legacy layout fallback, duplicate/template snapshot support, and focused unit tests committed to main through 0c5cf63. This is **not yet acceptance-complete**: full pytest and commit-specific GitHub CI have not been confirmed; bulk-edit grouping and template/import integration regression checks remain to verify. Do not mark DEV-050 complete until those checks pass.

  - UX correction (2026-10-09): fixed/custom placement editor brought directly below field groups so Supplier ID/BPID, Supplier Name, Address and Post Code have visible group selectors; custom-field group selector and layout selector are synchronised (fd043296). Verification of full CI remains outstanding.

  - BUG FIX (2026-10-09): the placement editor initially appeared empty because the page-load initialisation invoked renderGroups/renderFields but omitted renderLayout. Restored renderLayout at initialisation and group creation, added regression test. Commit eed6ed7a; CI pending.

  - BUG FIX (2026-10-09): selecting a fixed field group updated a stale layout object after reconcileLayout rebuilt the array, so saving silently retained Ungrouped. The change handler now looks up the current entry by stable ref before synchronising. Added a regression guard (d587739c). Full CI not yet verified.
