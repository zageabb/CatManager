# AGENTS.md — CatManager

## Objective
Develop CatManager autonomously against DEVELOPMENT.md. Preserve the panel-centric JSON contract, Flask/SQLite architecture and Taiju visual language unless a product decision explicitly changes them.

## Working rules
1. Read DEVELOPMENT.md before coding and work on the highest-priority incomplete item.
2. Inspect the current implementation rather than trusting completion labels.
3. Make the smallest coherent change that completes the objective.
4. Add or update tests for behavioural changes.
5. Run the relevant tests before considering work complete.
6. Update DEVELOPMENT.md with evidence when an item is completed or its scope changes.
7. Do not silently alter the canonical JSON schema. Increment/migrate schema versions intentionally.
8. Do not destructively delete panel or supplier data without an explicit, reversible lifecycle design.
9. Custom supplier data must stay keyed by stable fieldId.
10. Keep UI patterns consistent with the Category Panel reference: light surfaces, compact cards/tables, subtle borders/shadows, pink primary action and green status accents.

## Autonomous continuation
Continue autonomously until one of these happens:
1. the current objective is complete and verified;
2. a genuinely ambiguous product decision is required;
3. progress is blocked by something outside the repo;
4. continuing would risk destructive changes.

Do not stop merely because one implementation step completed.

## Validation
Minimum validation: python -m pytest -q
CI is authoritative for the pushed commit. A failed CI run means the objective is not verified.

## Architecture
- app.py: Flask app factory, SQLite persistence and routes.
- templates/: Jinja pages.
- static/: browser CSS/JS.
- tests/: behavioural tests.
- SQLite stores searchable panel metadata and canonical data_json.
- The JSON API is an interchange/debug surface, not a separate source of truth.

## Security
Never commit credentials, tokens, secrets or production databases. Treat raw JSON import as untrusted input and validate before persistence.
