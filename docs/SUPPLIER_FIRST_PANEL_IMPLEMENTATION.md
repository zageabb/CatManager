# Supplier-first Panel UX — implementation plan

Status: **Deferred / planned**. Approved pairing: Design 1 panel actions + Design 3 configuration hub. See [UX specification](SUPPLIER_FIRST_PANEL_UX_SPEC.md).

## Code touchpoints
- `templates/panel_view.html`: refactor top bar, default supplier tab, strip long analytics from initial viewport, group overflow actions, row-action menu.
- `templates/panel_configuration.html`: hub entry point and focused sections/pages; preserve the existing field editor while migrating it behind a card.
- `templates/base.html`: if reusable tab/page navigation is appropriate, avoid impacting portfolio pages.
- `static/app.css`: scoped enterprise header, hub cards, tabs, dropdowns, responsive table containers and accessibility states.
- `static/app.js`: progressive enhancements for tabs, search, menus, dismiss, focus handling; preserve current supplier filtering/sorting/column preferences, KPI preview and CSRF header logic.
- `app.py`: minimal read-only route/context changes as needed. Preserve `panel_view`, `panel_configuration`, `supplier_new`, master sync, supplier Excel, panel export and audit routes; new route names must be accompanied by tests.
- `tests/test_app.py`: acceptance and backwards-compatibility tests.

## Implementation stages (one reviewed PR at a time)
### UX-051 — Supplier-first panel shell
1. Extract/restructure current `panel_view.html` without losing route links or data.
2. Move three primary actions to header: Edit Panel, Panel Configuration, Add Supplier; group other functions in a categorized menu. Revisit existing unmerged/previous menu design rather than duplicating functionality.
3. Add Suppliers, Overview, Dashboard, Scoring, Actions, History navigation. Make Suppliers default. Keep links valid for archived panels.
4. Relocate lengthy analytics sections from initial supplier viewport into respective tabs; reuse current calculation context rather than changing formulas.
5. Ensure no CSS/layout regressions at 1440px, 1024px and 390px widths.

### UX-052 — Supplier table usability
1. Reuse existing search, supplier checkboxes/comparison, local column preferences and sort/filter controls.
2. Present compact contextual row menu for Edit / Actions / History / Profile, retaining clear focus and accessible labels.
3. Preserve ordered field rendering, wide-table horizontal scrolling and type-specific stars/region displays.
4. Add compact KPI strip only where the values are supported and ensure table is the visual anchor.

### UX-053 — Configuration hub
1. Build hub route or a GET mode for `panel_configuration`, leaving old configuration POST endpoint compatible.
2. Cards: Panel Details, Supplier Fields, Dashboard Widgets, Weighted Supplier Scoring, Templates, Import/Export, Master Sync.
3. Introduce focused view(s) incrementally. Initially anchor to existing editors when needed, without falsely implying a functional route.
4. Preserve Save Configuration flow and payloads: `fields_json`, `field_groups_json`, `dashboard_widgets_json`, `scoring_criteria_json`; retain field-removal confirmation/orphan recovery.
5. Preserve unsaved-change warning, live KPI preview including CSRF token, and every existing calculation.

### UX-054 — Polish, QA and adoption
1. Keyboard navigation: Tab/Shift+Tab, Enter/Space, Escape, outside click, clear focus movement.
2. Test with CSRF_ENABLED on; all POST forms must carry tokens and JSON preview must continue returning JSON.
3. Verify desktop/mobile; ensure top menu, table and hub cards never overflow viewport.
4. Regression suite `python -m pytest -q`, lint/checks as configured, GitHub Actions CI green, deploy `main` only after reviewed PR.
5. Update `DEVELOPMENT.md` with evidence after every stage; screenshots and short before/after summary for manager's Version 3 ideas report.

## Tests to add
- Supplier workspace is default on active and archived panels; table rows and correct custom fields remain visible.
- Header retains exactly intended top-level primary actions; full capability inventory remains reachable via menu/hub.
- Hidden panes have no side effects and existing query-driven table search/sort/columns work.
- KPI values, weighted scoring, coverage and alerts agree with pre-redesign calculations.
- Existing supplier and panel POST endpoints, supplier Excel import, template save and archive/restore retain CSRF protection.
- Menu/hub are keyboard operable and usable on narrow screens (manual browser smoke test plus structural regression checks).
- Multiple real/demo panels and empty panels render, including large field sets and wide multi-select matrices.

## Non-goals for these UX tickets
No new authentication system, no change to supplier master data, no new scoring algorithms, no backend schema migration, no removal of history or imports, and no fabricated metrics.

## Rollback
Keep UI changes segregated by PR. A reverted UI PR should leave canonical panel JSON and existing routes untouched, allowing safe roll back if users need the old screen.
