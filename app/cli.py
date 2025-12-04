import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Sequence, Tuple

from app.db import execute, execute_returning, fetch_all


def prompt_str(label: str, allow_blank: bool = False) -> Optional[str]:
    while True:
        val = input(f"{label}: ").strip()
        if val:
            return val
        if allow_blank:
            return None
        print("Please enter a value.")


def prompt_int(label: str, allow_blank: bool = False) -> Optional[int]:
    while True:
        val = input(f"{label}: ").strip()
        if not val and allow_blank:
            return None
        try:
            return int(val)
        except ValueError:
            print("Enter a valid integer.")


def prompt_decimal(label: str, allow_blank: bool = False) -> Optional[Decimal]:
    while True:
        val = input(f"{label}: ").strip()
        if not val and allow_blank:
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, ValueError):
            print("Enter a valid number.")


def prompt_date(label: str, allow_blank: bool = False) -> Optional[str]:
    while True:
        val = input(f"{label} (YYYY-MM-DD): ").strip()
        if not val and allow_blank:
            return None
        try:
            dt = datetime.strptime(val, "%Y-%m-%d").date()
            return dt.isoformat()
        except ValueError:
            print("Enter a valid date in YYYY-MM-DD format.")


def friendly_error(err: Exception) -> str:
    msg = str(err)
    lower = msg.lower()
    if "team_region_chk" in lower:
        return "region is required for a team"
    if "team_name" in lower and "already exists" in lower:
        return "team name must be unique"
    if "player_name_chk" in lower:
        return "player name is required"
    if "different_teams_chk" in lower:
        return "team1 and team2 must be different"
    if "winner_valid_chk" in lower:
        return "winner must be one of the two teams"
    if "active players" in lower and "5" in lower:
        return "roster cap is 5 active players"
    return msg.split("\n")[0]


def print_error(context: str, err: Exception) -> None:
    print(f"[Error] {context}: {friendly_error(err)}")


def print_rows(headers: Sequence[str], rows: Sequence[Tuple[Any, ...]]) -> None:
    if not rows:
        print("No rows.")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("-" * len(line))
    for row in rows:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))


# Teams
def list_teams() -> None:
    rows = fetch_all(
        "SELECT team_id, team_name, region, COALESCE(founded_year::text, '-') AS founded "
        "FROM teams ORDER BY team_name"
    )
    print_rows(["ID", "Name", "Region", "Founded"], rows)


def create_team() -> None:
    name = prompt_str("Team name")
    region = prompt_str("Region")
    founded_year = prompt_int("Founded year (blank to skip)", allow_blank=True)
    try:
        team_id = execute_returning(
            "INSERT INTO teams (team_name, region, founded_year) VALUES (%s, %s, %s) RETURNING team_id",
            (name, region, founded_year),
        )
        print(f"Created team with id {team_id}.")
    except Exception as e:
        print_error("Creating team", e)


def update_team() -> None:
    list_teams()
    team_id = prompt_int("Enter team ID to update")
    if team_id is None:
        return
    new_name = prompt_str("New name (blank to keep)", allow_blank=True)
    new_region = prompt_str("New region (blank to keep)", allow_blank=True)
    new_year = prompt_int("New founded year (blank to keep)", allow_blank=True)
    updates: Dict[str, Any] = {}
    if new_name is not None:
        updates["team_name"] = new_name
    if new_region is not None:
        updates["region"] = new_region
    if new_year is not None:
        updates["founded_year"] = new_year
    if not updates:
        print("No changes provided.")
        return
    sets = ", ".join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [team_id]
    try:
        execute(f"UPDATE teams SET {sets} WHERE team_id = %s", params)
        print("Team updated.")
    except Exception as e:
        print_error("Updating team", e)


def delete_team() -> None:
    list_teams()
    team_id = prompt_int("Enter team ID to delete")
    if team_id is None:
        return
    try:
        execute("DELETE FROM teams WHERE team_id = %s", (team_id,))
        print("Team deleted (if it existed).")
    except Exception as e:
        print_error("Deleting team", e)


# Players
def list_players() -> None:
    rows = fetch_all(
        """
        SELECT p.player_id, p.player_name, COALESCE(p.country, '-'), COALESCE(p.role, '-'),
               COALESCE(t.team_name, 'Free Agent') AS team
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        ORDER BY p.player_name
        """
    )
    print_rows(["ID", "Name", "Country", "Role", "Team"], rows)


def create_player() -> None:
    name = prompt_str("Player name")
    country = prompt_str("Country (blank to skip)", allow_blank=True)
    role = prompt_str("Role (blank to skip)", allow_blank=True)
    team_id = prompt_int("Team ID (blank for free agent)", allow_blank=True)
    try:
        player_id = execute_returning(
            "INSERT INTO players (player_name, country, role, team_id) VALUES (%s, %s, %s, %s) RETURNING player_id",
            (name, country, role, team_id),
        )
        print(f"Created player with id {player_id}.")
    except Exception as e:
        print_error("Creating player", e)


def update_player() -> None:
    list_players()
    player_id = prompt_int("Enter player ID to update")
    if player_id is None:
        return
    new_name = prompt_str("New name (blank to keep)", allow_blank=True)
    new_country = prompt_str("New country (blank to keep)", allow_blank=True)
    new_role = prompt_str("New role (blank to keep)", allow_blank=True)
    new_team = prompt_int("New team ID (blank for free agent/keep)", allow_blank=True)
    updates: Dict[str, Any] = {}
    if new_name is not None:
        updates["player_name"] = new_name
    if new_country is not None:
        updates["country"] = new_country
    if new_role is not None:
        updates["role"] = new_role
    if new_team is not None:
        updates["team_id"] = new_team
    if not updates:
        print("No changes provided.")
        return
    sets = ", ".join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [player_id]
    try:
        execute(f"UPDATE players SET {sets} WHERE player_id = %s", params)
        print("Player updated.")
    except Exception as e:
        print_error("Updating player", e)


def delete_player() -> None:
    list_players()
    player_id = prompt_int("Enter player ID to delete")
    if player_id is None:
        return
    try:
        execute("DELETE FROM players WHERE player_id = %s", (player_id,))
        print("Player deleted (if it existed).")
    except Exception as e:
        print_error("Deleting player", e)


# Tournaments
def list_tournaments() -> None:
    rows = fetch_all(
        """
        SELECT tournament_id, name, organizer, prize_pool, start_date, end_date, location
        FROM tournaments
        ORDER BY start_date DESC NULLS LAST, name
        """
    )
    print_rows(["ID", "Name", "Organizer", "Prize", "Start", "End", "Location"], rows)


def create_tournament() -> None:
    name = prompt_str("Tournament name")
    organizer = prompt_str("Organizer (blank to skip)", allow_blank=True)
    prize = prompt_decimal("Prize pool (blank for 0)", allow_blank=True) or Decimal("0")
    start = prompt_date("Start date", allow_blank=True)
    end = prompt_date("End date", allow_blank=True)
    location = prompt_str("Location (blank to skip)", allow_blank=True)
    try:
        tournament_id = execute_returning(
            """
            INSERT INTO tournaments (name, organizer, prize_pool, start_date, end_date, location)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING tournament_id
            """,
            (name, organizer, prize, start, end, location),
        )
        print(f"Created tournament with id {tournament_id}.")
    except Exception as e:
        print_error("Creating tournament", e)


def update_tournament() -> None:
    list_tournaments()
    tournament_id = prompt_int("Enter tournament ID to update")
    if tournament_id is None:
        return
    new_name = prompt_str("New name (blank to keep)", allow_blank=True)
    new_org = prompt_str("New organizer (blank to keep)", allow_blank=True)
    new_prize = prompt_decimal("New prize pool (blank to keep)", allow_blank=True)
    new_start = prompt_date("New start date (blank to keep)", allow_blank=True)
    new_end = prompt_date("New end date (blank to keep)", allow_blank=True)
    new_loc = prompt_str("New location (blank to keep)", allow_blank=True)
    updates: Dict[str, Any] = {}
    if new_name is not None:
        updates["name"] = new_name
    if new_org is not None:
        updates["organizer"] = new_org
    if new_prize is not None:
        updates["prize_pool"] = new_prize
    if new_start is not None:
        updates["start_date"] = new_start
    if new_end is not None:
        updates["end_date"] = new_end
    if new_loc is not None:
        updates["location"] = new_loc
    if not updates:
        print("No changes provided.")
        return
    sets = ", ".join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [tournament_id]
    try:
        execute(f"UPDATE tournaments SET {sets} WHERE tournament_id = %s", params)
        print("Tournament updated.")
    except Exception as e:
        print_error("Updating tournament", e)


def delete_tournament() -> None:
    list_tournaments()
    tournament_id = prompt_int("Enter tournament ID to delete")
    if tournament_id is None:
        return
    try:
        execute("DELETE FROM tournaments WHERE tournament_id = %s", (tournament_id,))
        print("Tournament deleted (if it existed).")
    except Exception as e:
        print_error("Deleting tournament", e)


# Maps
def list_maps() -> None:
    rows = fetch_all("SELECT map_id, map_name FROM maps ORDER BY map_name")
    print_rows(["ID", "Map"], rows)


def create_map() -> None:
    name = prompt_str("Map name")
    try:
        map_id = execute_returning(
            "INSERT INTO maps (map_name) VALUES (%s) RETURNING map_id",
            (name,),
        )
        print(f"Created map with id {map_id}.")
    except Exception as e:
        print_error("Creating map", e)


def update_map() -> None:
    list_maps()
    map_id = prompt_int("Enter map ID to update")
    if map_id is None:
        return
    new_name = prompt_str("New map name (blank to keep)", allow_blank=True)
    if new_name is None:
        print("No changes provided.")
        return
    try:
        execute("UPDATE maps SET map_name = %s WHERE map_id = %s", (new_name, map_id))
        print("Map updated.")
    except Exception as e:
        print_error("Updating map", e)


def delete_map() -> None:
    list_maps()
    map_id = prompt_int("Enter map ID to delete")
    if map_id is None:
        return
    try:
        execute("DELETE FROM maps WHERE map_id = %s", (map_id,))
        print("Map deleted (if it existed).")
    except Exception as e:
        print_error("Deleting map", e)


# Matches
def list_matches() -> None:
    rows = fetch_all(
        """
        SELECT m.match_id, t.name AS tournament, tm1.team_name AS team1, tm2.team_name AS team2,
               COALESCE(tmw.team_name, 'TBD') AS winner, COALESCE(mp.map_name, '-') AS map,
               m.match_date, m.best_of, m.team1_score, m.team2_score
        FROM matches m
        JOIN tournaments t ON m.tournament_id = t.tournament_id
        JOIN teams tm1 ON m.team1_id = tm1.team_id
        JOIN teams tm2 ON m.team2_id = tm2.team_id
        LEFT JOIN teams tmw ON m.winner_team_id = tmw.team_id
        LEFT JOIN maps mp ON m.map_id = mp.map_id
        ORDER BY m.match_date NULLS LAST, m.match_id
        """
    )
    print_rows(
        ["ID", "Tournament", "Team1", "Team2", "Winner", "Map", "Date", "BO", "T1", "T2"],
        rows,
    )


def create_match() -> None:
    # thin prompt here, heavy validation lives in DB fn
    tournament_id = prompt_int("Tournament ID")
    team1_id = prompt_int("Team 1 ID")
    team2_id = prompt_int("Team 2 ID")
    winner_id = prompt_int("Winner team ID (blank if undecided)", allow_blank=True)
    map_id = prompt_int("Map ID (blank to skip)", allow_blank=True)
    match_date = prompt_date("Match date", allow_blank=True)
    best_of = prompt_int("Best of (default 1, blank to skip)", allow_blank=True) or 1
    team1_score = prompt_int("Team 1 score (default 0, blank to skip)", allow_blank=True) or 0
    team2_score = prompt_int("Team 2 score (default 0, blank to skip)", allow_blank=True) or 0
    try:
        match_id = execute_returning(
            """
            SELECT validate_and_insert_match(%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tournament_id,
                team1_id,
                team2_id,
                winner_id,
                map_id,
                match_date,
                best_of,
                team1_score,
                team2_score,
            ),
        )
        print(f"Created match with id {match_id}.")
    except Exception as e:
        print_error("Creating match", e)


def update_match() -> None:
    list_matches()
    match_id = prompt_int("Enter match ID to update")
    if match_id is None:
        return
    fields = {
        "tournament_id": prompt_int("New tournament ID (blank to keep)", allow_blank=True),
        "team1_id": prompt_int("New team1 ID (blank to keep)", allow_blank=True),
        "team2_id": prompt_int("New team2 ID (blank to keep)", allow_blank=True),
        "winner_team_id": prompt_int("New winner team ID (blank to keep)", allow_blank=True),
        "map_id": prompt_int("New map ID (blank to keep)", allow_blank=True),
        "match_date": prompt_date("New match date (blank to keep)", allow_blank=True),
        "best_of": prompt_int("New best of (blank to keep)", allow_blank=True),
        "team1_score": prompt_int("New team1 score (blank to keep)", allow_blank=True),
        "team2_score": prompt_int("New team2 score (blank to keep)", allow_blank=True),
    }
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        print("No changes provided.")
        return
    sets = ", ".join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [match_id]
    try:
        execute(f"UPDATE matches SET {sets} WHERE match_id = %s", params)
        print("Match updated.")
    except Exception as e:
        print_error("Updating match", e)


def delete_match() -> None:
    list_matches()
    match_id = prompt_int("Enter match ID to delete")
    if match_id is None:
        return
    try:
        execute("DELETE FROM matches WHERE match_id = %s", (match_id,))
        print("Match deleted (if it existed).")
    except Exception as e:
        print_error("Deleting match", e)


# Tournament results
def list_results() -> None:
    rows = fetch_all(
        """
        SELECT r.result_id, t.name AS tournament, tm.team_name, r.placement, r.earnings
        FROM tournament_results r
        JOIN tournaments t ON r.tournament_id = t.tournament_id
        JOIN teams tm ON r.team_id = tm.team_id
        ORDER BY t.start_date NULLS LAST, r.placement
        """
    )
    print_rows(["ID", "Tournament", "Team", "Place", "Earnings"], rows)


def create_result() -> None:
    tournament_id = prompt_int("Tournament ID")
    team_id = prompt_int("Team ID")
    placement = prompt_int("Placement (1 = winner)")
    earnings = prompt_decimal("Earnings (blank for 0)", allow_blank=True) or Decimal("0")
    try:
        result_id = execute_returning(
            """
            INSERT INTO tournament_results (tournament_id, team_id, placement, earnings)
            VALUES (%s, %s, %s, %s)
            RETURNING result_id
            """,
            (tournament_id, team_id, placement, earnings),
        )
        print(f"Created tournament result with id {result_id}.")
    except Exception as e:
        print_error("Creating result", e)


def update_result() -> None:
    list_results()
    result_id = prompt_int("Enter result ID to update")
    if result_id is None:
        return
    new_tournament = prompt_int("New tournament ID (blank to keep)", allow_blank=True)
    new_team = prompt_int("New team ID (blank to keep)", allow_blank=True)
    new_place = prompt_int("New placement (blank to keep)", allow_blank=True)
    new_earnings = prompt_decimal("New earnings (blank to keep)", allow_blank=True)
    updates: Dict[str, Any] = {}
    if new_tournament is not None:
        updates["tournament_id"] = new_tournament
    if new_team is not None:
        updates["team_id"] = new_team
    if new_place is not None:
        updates["placement"] = new_place
    if new_earnings is not None:
        updates["earnings"] = new_earnings
    if not updates:
        print("No changes provided.")
        return
    sets = ", ".join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [result_id]
    try:
        execute(f"UPDATE tournament_results SET {sets} WHERE result_id = %s", params)
        print("Tournament result updated.")
    except Exception as e:
        print_error("Updating result", e)


def delete_result() -> None:
    list_results()
    result_id = prompt_int("Enter result ID to delete")
    if result_id is None:
        return
    try:
        execute("DELETE FROM tournament_results WHERE result_id = %s", (result_id,))
        print("Result deleted (if it existed).")
    except Exception as e:
        print_error("Deleting result", e)


# Roster
def list_roster() -> None:
    rows = fetch_all(
        """
        SELECT r.roster_id, tm.team_name, p.player_name, r.is_active
        FROM team_roster r
        JOIN teams tm ON r.team_id = tm.team_id
        JOIN players p ON r.player_id = p.player_id
        ORDER BY tm.team_name, p.player_name
        """
    )
    print_rows(["ID", "Team", "Player", "Active"], rows)


def add_to_roster() -> None:
    team_id = prompt_int("Team ID")
    player_id = prompt_int("Player ID")
    is_active = prompt_str("Active? (y/n, default y)", allow_blank=True)
    active_bool = True if is_active is None else is_active.lower().startswith("y")
    try:
        roster_id = execute_returning(
            "INSERT INTO team_roster (team_id, player_id, is_active) VALUES (%s, %s, %s) RETURNING roster_id",
            (team_id, player_id, active_bool),
        )
        print(f"Added roster entry id {roster_id}.")
    except Exception as e:
        print_error("Adding to roster", e)


def toggle_roster() -> None:
    list_roster()
    roster_id = prompt_int("Roster ID to toggle")
    if roster_id is None:
        return
    try:
        execute(
            "UPDATE team_roster SET is_active = NOT is_active WHERE roster_id = %s",
            (roster_id,),
        )
        print("Toggled roster active state.")
    except Exception as e:
        print_error("Toggling roster", e)


def remove_from_roster() -> None:
    list_roster()
    roster_id = prompt_int("Roster ID to delete")
    if roster_id is None:
        return
    try:
        execute("DELETE FROM team_roster WHERE roster_id = %s", (roster_id,))
        print("Roster entry deleted (if it existed).")
    except Exception as e:
        print_error("Deleting roster entry", e)


# Interesting queries
def run_queries() -> None:
    options = {
        "1": ("Earnings by team", earnings_by_team),
        "2": ("Win counts by map", wins_by_map),
        "3": ("Active roster size per team", active_roster_counts),
        "4": ("Team summary (server function)", team_summary_query),
    }
    while True:
        print("\nInteresting queries:")
        for key, (label, _) in options.items():
            print(f"{key}) {label}")
        print("0) Back")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            return
        if choice in options:
            _, func = options[choice]
            func()
        else:
            print("Invalid choice.")


def earnings_by_team() -> None:
    rows = fetch_all(
        """
        SELECT tm.team_name, SUM(r.earnings) AS total_earnings
        FROM tournament_results r
        JOIN teams tm ON r.team_id = tm.team_id
        GROUP BY tm.team_name
        ORDER BY total_earnings DESC
        """
    )
    print_rows(["Team", "Total Earnings"], rows)


def wins_by_map() -> None:
    rows = fetch_all(
        """
        SELECT mp.map_name, COUNT(*) AS wins
        FROM matches m
        JOIN maps mp ON m.map_id = mp.map_id
        WHERE m.winner_team_id IS NOT NULL
        GROUP BY mp.map_name
        ORDER BY wins DESC
        """
    )
    print_rows(["Map", "Match Wins Played On"], rows)


def active_roster_counts() -> None:
    rows = fetch_all(
        """
        SELECT tm.team_name, COUNT(*) FILTER (WHERE r.is_active) AS active_players
        FROM teams tm
        LEFT JOIN team_roster r ON tm.team_id = r.team_id AND r.is_active
        GROUP BY tm.team_name
        ORDER BY tm.team_name
        """
    )
    print_rows(["Team", "Active Players"], rows)


def team_summary_query() -> None:
    rows = fetch_all(
        """
        SELECT team_name, matches_played, wins, total_earnings
        FROM team_summary()
        ORDER BY team_name
        """
    )
    print_rows(["Team", "Matches", "Wins", "Earnings"], rows)


# Menu wiring
def menu_loop() -> None:
    actions = {
        "1": ("Teams", teams_menu),
        "2": ("Players", players_menu),
        "3": ("Tournaments", tournaments_menu),
        "4": ("Maps", maps_menu),
        "5": ("Matches", matches_menu),
        "6": ("Tournament Results", results_menu),
        "7": ("Team Roster", roster_menu),
        "8": ("Interesting Queries", run_queries),
    }
    while True:
        print("\nCS2 Esports DB - Main Menu")
        for key, (label, _) in actions.items():
            print(f"{key}) {label}")
        print("0) Exit")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Bye.")
            return
        if choice in actions:
            _, func = actions[choice]
            func()
        else:
            print("Invalid choice.")


def teams_menu() -> None:
    options = {
        "1": ("List teams", list_teams),
        "2": ("Create team", create_team),
        "3": ("Update team", update_team),
        "4": ("Delete team", delete_team),
    }
    simple_menu("Teams", options)


def players_menu() -> None:
    options = {
        "1": ("List players", list_players),
        "2": ("Create player", create_player),
        "3": ("Update player", update_player),
        "4": ("Delete player", delete_player),
    }
    simple_menu("Players", options)


def tournaments_menu() -> None:
    options = {
        "1": ("List tournaments", list_tournaments),
        "2": ("Create tournament", create_tournament),
        "3": ("Update tournament", update_tournament),
        "4": ("Delete tournament", delete_tournament),
    }
    simple_menu("Tournaments", options)


def maps_menu() -> None:
    options = {
        "1": ("List maps", list_maps),
        "2": ("Create map", create_map),
        "3": ("Update map", update_map),
        "4": ("Delete map", delete_map),
    }
    simple_menu("Maps", options)


def matches_menu() -> None:
    options = {
        "1": ("List matches", list_matches),
        "2": ("Create match", create_match),
        "3": ("Update match", update_match),
        "4": ("Delete match", delete_match),
    }
    simple_menu("Matches", options)


def results_menu() -> None:
    options = {
        "1": ("List tournament results", list_results),
        "2": ("Create tournament result", create_result),
        "3": ("Update tournament result", update_result),
        "4": ("Delete tournament result", delete_result),
    }
    simple_menu("Tournament Results", options)


def roster_menu() -> None:
    options = {
        "1": ("List roster entries", list_roster),
        "2": ("Add player to roster", add_to_roster),
        "3": ("Toggle active flag", toggle_roster),
        "4": ("Delete roster entry", remove_from_roster),
    }
    simple_menu("Team Roster", options)


def simple_menu(title: str, options: Dict[str, Tuple[str, Any]]) -> None:
    while True:
        print(f"\n{title} Menu")
        for key, (label, _) in options.items():
            print(f"{key}) {label}")
        print("0) Back")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            return
        if choice in options:
            _, func = options[choice]
            func()
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    try:
        menu_loop()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(0)
