# Supplier-first Panel Workspace — UX specification

Status: **Approved design direction; not implemented**. Version 3 UX backlog.

## Purpose and priority
A category panel is primarily a working list of suppliers and their fields. Open a panel directly in the **Suppliers workspace**; configuration, intelligence and administration are secondary. Combine Design 1 (clean header/overflow actions) with Design 3 (card-based Configuration Hub). Keep existing Taiju brand, light enterprise surfaces, compact high-density tables and existing data.

## Primary panel view
- Title: panel name and ID, small active/archived status, concise subtitle; optionally a one-line context row (category, business, region, MDF).
- Persistent actions **Edit Panel**, **Panel Configuration**, **Add Supplier**. On archived panels use an archived indicator and expose **Restore** via the overflow menu.
- A **More actions** menu groups **Reports & exports**, **Supplier operations**, **Panel management & audit**, and **Advanced/data**. Never drop existing functions. Use proper labels, keyboard focus, Escape/outside-click behaviour, ARIA and a mobile-safe overlay.
- Default tab **Suppliers**. Other tabs: **Overview**, **Dashboard**, **Scoring**, **Actions**, **History**. Configuration opens the hub rather than being mixed into the supplier tab. Keep the initial tab in the URL query/hash if useful for shareable navigation, with **Suppliers** always the first-load default.
- Optional four concise KPI cards (total suppliers, qualified, average assessment, spend) above the table only when data/configuration supports them. No fabricated values; invalid/unavailable data displays an explicit dash or label. Keep cards compact enough that the first rows of suppliers are visible without scrolling on standard desktop.
- **Supplier table leads the page**: search by BPID/name, existing type-ahead/filters, configurable visible columns, sort, multi-select, row count and pagination. Preserve fields' definitions, order, group context and user table preferences. Use a horizontal scroll within the table for wide field sets; do not turn the page into a long scrolling field matrix.
- Supplier columns should include fixed identity first, then panel custom fields, with qualification/review/score where configured. Preserve block/multiselect and star rendering and distinction between missing and invalid ratings.
- Each row has a discreet contextual **⋯** with Edit, Actions/follow-ups, History and Cross-panel Profile. Expose supplier detail by supplier name/BPID and preserve existing bulk comparison.
- Place longer sections currently stacked on panel view (qualification review alerts, regional sourcing coverage, full scoring breakdown and detailed KPI data) in the respective tabs, not ahead of suppliers.
- Archived panels are read-only; restore remains possible by authorised workflow. All existing audit and CSRF behaviour remains intact.

## Configuration hub
Open **Panel Configuration** into a card-grid landing page (two columns desktop, one mobile), with brief descriptions and meaningful icons. Card destinations:
1. **Panel Details** — existing panel edit and identity/MDF metadata.
2. **Supplier Fields** — custom fields, field groups, field library and panel-specific column/table setup.
3. **Dashboard Widgets** — KPI builder and live preview.
4. **Weighted Supplier Scoring** — assessment rules and weights.
5. **Templates** — save/apply/copy configuration; no supplier data copied.
6. **Import / Export** — supplier Excel and panel JSON tools.
7. **Master Data Sync** — governed preview/confirm workflow.

Do not invent backend features. Until a section is independently routable, use an anchored subsection in the existing form, but **do not present a fake navigation destination**. Later split configurations into focused pages with clear Save/Cancel and unsaved-changes protection. Both hub and detail pages provide an obvious **Back to Suppliers** action.

## More actions information architecture
- **Reports & exports:** Management Excel, Print/Save PDF, supplier workbook export, JSON export, audit reports.
- **Supplier operations:** Bulk edit, import supplier Excel, sync master, supplier comparison where applicable.
- **Panel management:** Duplicate, Save as Template, Template library, audit history, orphaned field recovery.
- **Danger zone (visually separated):** Archive (and Restore on archived panels).

Avoid nesting more than one menu level. Grouped sections show labels, not many top-row buttons. Keep destructive actions behind existing explicit confirmation.

## Visual and accessibility standards
White/off-white content surfaces, deep navy navigation, restrained pink accent for primary/high-priority actions, neutral borders, rounded 8–12 px cards, deliberate white space and 14–16 px normal text. Compact but readable tables; hover/focus styling. Visible keyboard focus, labels, tooltips when necessary and no essential hover-only controls. At <= 760 px: cards stack, table scrolls within container, actions menu stays on-screen, search remains accessible, headers do not overlap.

## Behaviour acceptance
1. Opening any active panel shows supplier search and at least the table header immediately, ahead of lengthy analytics/setup.
2. Header has three primary controls plus one overflow control. No controls are lost.
3. Supplier search, MDF/region data display, sorting, column settings, comparisons, Excel workflows, edit and delete safeguards behave as before.
4. Tabs expose historic dashboard, scoring, alerts, regional risk, actions and history in sensible places; no duplicated live calculations or schema mutation.
5. Hub contains the seven cards above with working navigation or honest anchored destinations.
6. Navigation and CSRF-enabled POST forms work with mouse, keyboard and mobile.
7. Older panel JSON and demo/legacy panels render without schema migration.
8. No source data is modified simply by opening tabs, hub, menu or viewing KPIs.

## Boundaries
This is a **design target, not deployed software**. Mock-ups illustrate layout rather than actual supplier numbers, data, or already-built routes. All real values come from the current panel.
