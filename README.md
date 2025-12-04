# CS2 Esports Database Project

Quickstart to load the PostgreSQL schema and use the Python CLI to exercise full CRUD.

## Database setup
- Ensure PostgreSQL is running locally and you have a database user with create privileges.
- Create a database (default name used in examples is `cs2_esports`):
  - `createdb cs2_esports`
- Load schema, constraints, indexes, and seed data:
  - `psql -d cs2_esports -f chen_final_project.sql`
- Optional helpers (PowerShell):
  - Reset schema/seed: `./scripts/reset_db.ps1 -User kevin -Db cs2_esports -Server 127.0.0.1 -Password 808080`
  - Reset + smoke test + env setup in one go: `./scripts/reset_and_test.ps1`
  - Smoke test only (assumes DATABASE_URL set or uses default): `./scripts/smoke.ps1`

## Python env (psycopg2 client)
- Create a virtualenv and install dependencies:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Set `DATABASE_URL` if you don't want the default `postgresql://postgres:postgres@localhost:5432/cs2_esports`.
- Test connectivity and view basic counts:
  - `python -m app.db_check`
- Run a quick smoke test that creates/updates/deletes sample data:
  - `python -m app.smoke_test`
- Run the CRUD CLI (menus for teams, players, tournaments, maps, matches, tournament results, roster, and analysis queries):
  - `python -m app.cli`
- Run the GUI (Tkinter) to demo CRUD + queries in tabs:
  - `python -m app.gui`

## Notes
- Interesting queries in the CLI include earnings by team, wins by map, and active roster counts.
- Match creation uses a server-side validator to keep scores/winners consistent.
- FK choices: matches keep team FKs RESTRICT to preserve history; players SET NULL on team delete; tournaments/maps/results/roster cascade.
- If you change the schema, refresh the DB with `psql -d cs2_esports -f chen_final_project.sql`.
