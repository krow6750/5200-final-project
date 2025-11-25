# CS2 Esports Database Project

Quickstart to create and load the PostgreSQL schema, plus a minimal Python connector to build the CRUD app.

## Database setup
- Ensure PostgreSQL is running locally and you have a database user with create privileges.
- Create a database (default name used in examples is `cs2_esports`):
  - `createdb cs2_esports`
- Load schema, constraints, indexes, and seed data:
  - `psql -d cs2_esports -f chen_final_project.sql`

## Python env (psycopg2 client)
- Create a virtualenv and install dependencies:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Set `DATABASE_URL` if you don’t want the default `postgresql://postgres:postgres@localhost:5432/cs2_esports`.
- Test connectivity and view basic counts:
  - `python -m app.db_check`

## Next steps
- Flesh out CRUD flows in Python (or a GUI) using the connection helpers in `app/db.py`.
- Add stored functions/triggers as needed, then re-run `psql -f chen_final_project.sql` to apply changes.
