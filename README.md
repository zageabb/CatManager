# CatManager

CatManager is a Flask + SQLite Category Management application for equipment panels and their linked suppliers.

The initial implementation follows the supplied Taiju Category Panel mock-up: dashboard cards across the top, a searchable panel portfolio table, panel create/edit, dynamic supplier fields, supplier entry and a raw JSON data/settings view.

## Run locally
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. python app.py

Open http://127.0.0.1:5000. On first run the SQLite database is created under instance/ and populated with demonstration panels.

## Test
Run: pytest -q

## Data model
Each panel is persisted as searchable SQLite metadata plus its canonical JSON object. Custom supplier values use stable field IDs so visible labels can change without breaking stored supplier records.

See DEVELOPMENT.md for implementation evidence and planned development and AGENTS.md for autonomous development rules.
