from app.db import fetch_all


def main() -> None:
    counts = {}
    for table in ["teams", "players", "tournaments", "maps", "matches", "tournament_results"]:
        rows = fetch_all(f"SELECT COUNT(*) FROM {table}")
        counts[table] = rows[0][0] if rows else 0

    print("Table counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")

    sample_matches = fetch_all(
        """
        SELECT m.match_id, t.name AS tournament, tm1.team_name AS team1, tm2.team_name AS team2, tmw.team_name AS winner
        FROM matches m
        JOIN tournaments t ON m.tournament_id = t.tournament_id
        JOIN teams tm1 ON m.team1_id = tm1.team_id
        JOIN teams tm2 ON m.team2_id = tm2.team_id
        LEFT JOIN teams tmw ON m.winner_team_id = tmw.team_id
        ORDER BY m.match_date
        LIMIT 5;
        """
    )
    print("\nSample matches:")
    for row in sample_matches:
        print(f"  id={row[0]} | {row[2]} vs {row[3]} | winner={row[4]} | tournament={row[1]}")


if __name__ == "__main__":
    main()
