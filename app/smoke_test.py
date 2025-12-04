"""
Simple smoke test to verify CRUD operations work against a local DB.
This exercises create/read/update/delete across teams, players, tournaments, matches, and results.
"""
from datetime import date
from decimal import Decimal

from app.db import execute, execute_returning, fetch_one


def main() -> None:
    print("Running smoke test against DATABASE_URL...")
    # Create minimal fixtures
    team_id = execute_returning(
        "INSERT INTO teams (team_name, region, founded_year) VALUES (%s, %s, %s) RETURNING team_id",
        ("Smoke Test Team", "EU", 2024),
    )
    print(f"Created team id={team_id}")

    player_id = execute_returning(
        "INSERT INTO players (player_name, country, role, team_id) VALUES (%s, %s, %s, %s) RETURNING player_id",
        ("Smoke Player", "Nowhere", "Rifler", team_id),
    )
    print(f"Created player id={player_id}")

    tournament_id = execute_returning(
        """
        INSERT INTO tournaments (name, organizer, prize_pool, start_date, end_date, location)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING tournament_id
        """,
        ("Smoke Open", "TestOrg", Decimal("10000"), date(2025, 1, 1), date(2025, 1, 2), "Online"),
    )
    print(f"Created tournament id={tournament_id}")

    # Use existing map id 1 (Mirage) and existing team 1 as opponent to satisfy FK
    match_id = execute_returning(
        """
        INSERT INTO matches (tournament_id, team1_id, team2_id, winner_team_id, map_id, match_date, best_of, team1_score, team2_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING match_id
        """,
        (tournament_id, team_id, 1, team_id, 1, date(2025, 1, 1), 1, 1, 0),
    )
    print(f"Created match id={match_id}")

    result_id = execute_returning(
        """
        INSERT INTO tournament_results (tournament_id, team_id, placement, earnings)
        VALUES (%s, %s, %s, %s)
        RETURNING result_id
        """,
        (tournament_id, team_id, 1, Decimal("5000")),
    )
    print(f"Created result id={result_id}")

    # Update and read back the team
    execute("UPDATE teams SET team_name = %s WHERE team_id = %s", ("Smoke Test Team Updated", team_id))
    updated = fetch_one("SELECT team_name FROM teams WHERE team_id = %s", (team_id,))
    print(f"Updated team name -> {updated[0] if updated else 'not found'}")

    # Cleanup in FK-friendly order
    execute("DELETE FROM tournament_results WHERE result_id = %s", (result_id,))
    execute("DELETE FROM matches WHERE match_id = %s", (match_id,))
    execute("DELETE FROM players WHERE player_id = %s", (player_id,))
    execute("DELETE FROM tournaments WHERE tournament_id = %s", (tournament_id,))
    execute("DELETE FROM teams WHERE team_id = %s", (team_id,))
    print("Cleanup complete. Smoke test passed.")


if __name__ == "__main__":
    main()
