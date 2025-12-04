"""
Simple Tkinter GUI to exercise CRUD operations and run analysis queries.
Reuses DB helpers to keep logic centralized. Designed for quick demos.
"""
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.db import execute, execute_returning, fetch_all


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


def parse_int(value):
    # quick int helper (blank -> None)
    return int(value) if value not in (None, "") else None


def parse_decimal(value):
    # minimal decimal parsing, keep app logic slim
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError("Invalid decimal")


def parse_date(value):
    # expected format YYYY-MM-DD to keep inputs consistent
    if value in (None, ""):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Use YYYY-MM-DD")


def parse_combo_id(value):
    # combobox values look like "3 - Team Name"; grab the leading id
    if value in (None, ""):
        return None
    try:
        return int(str(value).split(" - ", 1)[0])
    except (ValueError, IndexError):
        raise ValueError("Pick a value from the dropdown")


class BaseCrudFrame(ttk.Frame):
    def __init__(self, master, headers):
        super().__init__(master, padding=10)
        self.headers = headers
        self.sort_dir = {}
        self.status_var = tk.StringVar(value="")
        # dead-simple table view; keep columns narrow to fit in one window
        self.tree = ttk.Treeview(self, columns=headers, show="headings", height=10)
        for h in headers:
            self.tree.heading(h, text=h, command=lambda c=h: self.sort_column(c))
            self.tree.column(h, width=120, anchor=tk.W)
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._refresh_heading_labels()
        # tiny status bar to show success/error without spamming popups
        ttk.Label(self, textvariable=self.status_var, foreground="gray").grid(
            row=99, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

    def get_selected_id(self):
        item = self.tree.selection()
        if not item:
            return None
        values = self.tree.item(item[0])["values"]
        return values[0] if values else None

    def get_selected_values(self):
        item = self.tree.selection()
        if not item:
            return None
        return self.tree.item(item[0])["values"]

    def set_tree(self, rows):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def error(self, msg):
        messagebox.showerror("Error", friendly_error(Exception(msg)))
        self.set_status(msg)

    def sort_column(self, col):
        # Not fancy sorting, just enough for demo to feel nicer.
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        # toggle asc/desc
        descending = self.sort_dir.get(col, False)
        def keyfn(t):
            val = t[0]
            # try numeric first
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
            return str(val).lower()
        items.sort(key=keyfn, reverse=descending)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self.sort_dir[col] = not descending
        self._refresh_heading_labels(active=col, used_desc=descending)

    def _refresh_heading_labels(self, active=None, used_desc=False):
        # Add a tiny ^ or v to show sort direction on the last-clicked column.
        for h in self.headers:
            indicator = ""
            if h == active:
                indicator = " v" if used_desc else " ^"
            self.tree.heading(h, text=f"{h}{indicator}", command=lambda c=h: self.sort_column(c))

    def set_status(self, msg):
        self.status_var.set(msg)

    def on_select(self, event=None):
        # Hook for subclasses to respond to row selections (prefill forms, enable buttons).
        pass


class TeamsFrame(BaseCrudFrame):
    def __init__(self, master):
        super().__init__(master, ["ID", "Name", "Region", "Founded"])
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky="w")
        ttk.Label(self, text="Region").grid(row=2, column=0, sticky="w")
        ttk.Label(self, text="Founded Year").grid(row=3, column=0, sticky="w")
        self.name = ttk.Entry(self)
        self.region = ttk.Entry(self)
        self.founded = ttk.Entry(self)
        self.name.grid(row=1, column=1, sticky="ew")
        self.region.grid(row=2, column=1, sticky="ew")
        self.founded.grid(row=3, column=1, sticky="ew")
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=2, padx=6)
        ttk.Button(self, text="Create", command=self.create).grid(row=1, column=3, padx=6)
        self.btn_update = ttk.Button(self, text="Update", command=self.update)
        self.btn_update.grid(row=2, column=3, padx=6)
        self.btn_delete = ttk.Button(self, text="Delete", command=self.delete)
        self.btn_delete.grid(row=3, column=3, padx=6)
        ttk.Button(self, text="Clear form", command=self.clear_form).grid(row=4, column=3, padx=6, pady=(4, 0))
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.refresh()

    def refresh(self):
        rows = fetch_all(
            "SELECT team_id, team_name, region, COALESCE(founded_year::text, '-') FROM teams ORDER BY team_name"
        )
        self.set_tree(rows)
        self.set_status("Loaded teams")

    def create(self):
        if not self.name.get().strip() or not self.region.get().strip():
            self.error("team name and region are required")
            return
        try:
            founded_year = parse_int(self.founded.get())
            team_id = execute_returning(
                "INSERT INTO teams (team_name, region, founded_year) VALUES (%s, %s, %s) RETURNING team_id",
                (self.name.get(), self.region.get(), founded_year),
            )
            messagebox.showinfo("Success", f"Created team {team_id}")
            self.refresh()
            self.set_status(f"Created team {team_id}")
            self.clear_form()
        except Exception as e:
            self.error(str(e))

    def update(self):
        team_id = self.get_selected_id()
        if not team_id:
            self.error("Select a team to update")
            return
        if not any(field.strip() for field in (self.name.get(), self.region.get(), self.founded.get())):
            self.error("Enter at least one field to update")
            return
        current = self.get_selected_values() or []
        name_val = self.name.get().strip() or (current[1] if len(current) > 1 else "")
        region_val = self.region.get().strip() or (current[2] if len(current) > 2 else "")
        if not name_val or not region_val:
            self.error("team name and region are required")
            return
        try:
            founded_year = parse_int(self.founded.get()) if self.founded.get().strip() else (current[3] if len(current) > 3 else None)
            execute(
                "UPDATE teams SET team_name=%s, region=%s, founded_year=%s WHERE team_id=%s",
                (name_val, region_val, founded_year, team_id),
            )
            self.refresh()
            self.set_status(f"Updated team {team_id}")
        except Exception as e:
            self.error(str(e))

    def delete(self):
        team_id = self.get_selected_id()
        if not team_id:
            self.error("Select a team to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected team?"):
            return
        try:
            execute("DELETE FROM teams WHERE team_id=%s", (team_id,))
            self.refresh()
            self.clear_form()
            self.set_status(f"Deleted team {team_id}")
        except Exception as e:
            self.error(str(e))

    def clear_form(self):
        for entry in (self.name, self.region, self.founded):
            entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.set_status("Form cleared")

    def on_select(self, event=None):
        values = self.get_selected_values() or []
        if not values:
            return
        # prefill form with selected row to make edits smoother
        self.name.delete(0, tk.END)
        self.name.insert(0, values[1])
        self.region.delete(0, tk.END)
        self.region.insert(0, values[2])
        self.founded.delete(0, tk.END)
        if len(values) > 3 and values[3] != "-":
            self.founded.insert(0, values[3])
        self.btn_update.state(["!disabled"])
        self.btn_delete.state(["!disabled"])
        self.set_status(f"Selected team {values[1]}")


class PlayersFrame(BaseCrudFrame):
    def __init__(self, master):
        super().__init__(master, ["ID", "Name", "Country", "Role", "Team"])
        labels = ["Name", "Country", "Role"]
        self.entries = []
        for idx, label in enumerate(labels):
            ttk.Label(self, text=label).grid(row=1 + idx, column=0, sticky="w")
            entry = ttk.Entry(self)
            entry.grid(row=1 + idx, column=1, sticky="ew")
            self.entries.append(entry)
        ttk.Label(self, text="Team").grid(row=4, column=0, sticky="w")
        self.team_combo = ttk.Combobox(self, state="readonly")
        self.team_combo.grid(row=4, column=1, sticky="ew")
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=2, padx=6)
        ttk.Button(self, text="Create", command=self.create).grid(row=1, column=3, padx=6)
        self.btn_update = ttk.Button(self, text="Update", command=self.update)
        self.btn_update.grid(row=2, column=3, padx=6)
        self.btn_delete = ttk.Button(self, text="Delete", command=self.delete)
        self.btn_delete.grid(row=3, column=3, padx=6)
        ttk.Button(self, text="Clear form", command=self.clear_form).grid(row=4, column=3, padx=6, pady=(4, 0))
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.refresh()

    def refresh(self):
        # reload players and the team dropdown so IDs map cleanly
        rows = fetch_all(
            """
            SELECT p.player_id, p.player_name, COALESCE(p.country,'-'), COALESCE(p.role,'-'),
                   COALESCE(t.team_name,'Free Agent')
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.team_id
            ORDER BY p.player_name
            """
        )
        self.set_tree(rows)
        team_options = fetch_all("SELECT team_id, team_name FROM teams ORDER BY team_name")
        self.team_combo["values"] = [""] + [f"{row[0]} - {row[1]}" for row in team_options]
        self.set_status("Loaded players")

    def create(self):
        name, country, role = [e.get() for e in self.entries]
        team = self.team_combo.get()
        if not name.strip():
            self.error("player name is required")
            return
        try:
            team_id = parse_combo_id(team)
            player_id = execute_returning(
                "INSERT INTO players (player_name, country, role, team_id) VALUES (%s, %s, %s, %s) RETURNING player_id",
                (name, country or None, role or None, team_id),
            )
            messagebox.showinfo("Success", f"Created player {player_id}")
            self.refresh()
            self.set_status(f"Created player {player_id}")
            self.clear_form()
        except Exception as e:
            self.error(str(e))

    def update(self):
        player_id = self.get_selected_id()
        if not player_id:
            self.error("Select a player to update")
            return
        name, country, role = [e.get() for e in self.entries]
        team = self.team_combo.get()
        if not any(field.strip() for field in (name, country, role, team)):
            self.error("Enter at least one field to update")
            return
        current = self.get_selected_values() or []
        name_val = name.strip() or (current[1] if len(current) > 1 else "")
        if not name_val:
            self.error("player name is required")
            return
        try:
            team_id = parse_combo_id(team)
            execute(
                "UPDATE players SET player_name=%s, country=%s, role=%s, team_id=%s WHERE player_id=%s",
                (name_val, country or None, role or None, team_id, player_id),
            )
            self.refresh()
            self.set_status(f"Updated player {player_id}")
        except Exception as e:
            self.error(str(e))

    def delete(self):
        player_id = self.get_selected_id()
        if not player_id:
            self.error("Select a player to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected player?"):
            return
        try:
            execute("DELETE FROM players WHERE player_id=%s", (player_id,))
            self.refresh()
            self.clear_form()
            self.set_status(f"Deleted player {player_id}")
        except Exception as e:
            self.error(str(e))

    def clear_form(self):
        for entry in self.entries:
            entry.delete(0, tk.END)
        self.team_combo.set("")
        self.tree.selection_remove(self.tree.selection())
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.set_status("Form cleared")

    def on_select(self, event=None):
        values = self.get_selected_values() or []
        if not values:
            return
        for entry, val in zip(self.entries, values[1:4]):
            entry.delete(0, tk.END)
            if val != "-":
                entry.insert(0, val)
        # team combobox left blank so user explicitly picks a new team
        self.team_combo.set("")
        self.btn_update.state(["!disabled"])
        self.btn_delete.state(["!disabled"])
        self.set_status(f"Selected player {values[1]}")


class TournamentsFrame(BaseCrudFrame):
    def __init__(self, master):
        super().__init__(master, ["ID", "Name", "Organizer", "Prize", "Start", "End", "Location"])
        labels = ["Name", "Organizer", "Prize", "Start (YYYY-MM-DD)", "End (YYYY-MM-DD)", "Location"]
        self.entries = []
        for idx, label in enumerate(labels):
            ttk.Label(self, text=label).grid(row=1 + idx, column=0, sticky="w")
            entry = ttk.Entry(self)
            entry.grid(row=1 + idx, column=1, sticky="ew")
            self.entries.append(entry)
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=2, padx=6)
        ttk.Button(self, text="Create", command=self.create).grid(row=1, column=3, padx=6)
        self.btn_update = ttk.Button(self, text="Update", command=self.update)
        self.btn_update.grid(row=2, column=3, padx=6)
        self.btn_delete = ttk.Button(self, text="Delete", command=self.delete)
        self.btn_delete.grid(row=3, column=3, padx=6)
        ttk.Button(self, text="Clear form", command=self.clear_form).grid(row=4, column=3, padx=6, pady=(4, 0))
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.refresh()

    def refresh(self):
        rows = fetch_all(
            """
            SELECT tournament_id, name, organizer, prize_pool, start_date, end_date, location
            FROM tournaments
            ORDER BY start_date DESC NULLS LAST, name
            """
        )
        self.set_tree(rows)
        self.set_status("Loaded tournaments")

    def create(self):
        name, org, prize, start, end, loc = [e.get() for e in self.entries]
        if not name.strip():
            self.error("tournament name is required")
            return
        try:
            prize_val = parse_decimal(prize) or Decimal("0")
            start_date = parse_date(start)
            end_date = parse_date(end)
            tid = execute_returning(
                """
                INSERT INTO tournaments (name, organizer, prize_pool, start_date, end_date, location)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING tournament_id
                """,
                (name, org or None, prize_val, start_date, end_date, loc or None),
            )
            messagebox.showinfo("Success", f"Created tournament {tid}")
            self.refresh()
            self.set_status(f"Created tournament {tid}")
            self.clear_form()
        except Exception as e:
            self.error(str(e))

    def update(self):
        tid = self.get_selected_id()
        if not tid:
            self.error("Select a tournament to update")
            return
        name, org, prize, start, end, loc = [e.get() for e in self.entries]
        if not any(field.strip() for field in (name, org, prize, start, end, loc)):
            self.error("Enter at least one field to update")
            return
        current = self.get_selected_values() or []
        name_val = name.strip() or (current[1] if len(current) > 1 else "")
        if not name_val:
            self.error("tournament name is required")
            return
        try:
            prize_val = parse_decimal(prize) or Decimal("0")
            start_date = parse_date(start)
            end_date = parse_date(end)
            execute(
                """
                UPDATE tournaments
                SET name=%s, organizer=%s, prize_pool=%s, start_date=%s, end_date=%s, location=%s
                WHERE tournament_id=%s
                """,
                (name_val, org or None, prize_val, start_date, end_date, loc or None, tid),
            )
            self.refresh()
            self.set_status(f"Updated tournament {tid}")
        except Exception as e:
            self.error(str(e))

    def delete(self):
        tid = self.get_selected_id()
        if not tid:
            self.error("Select a tournament to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected tournament?"):
            return
        try:
            execute("DELETE FROM tournaments WHERE tournament_id=%s", (tid,))
            self.refresh()
            self.clear_form()
            self.set_status(f"Deleted tournament {tid}")
        except Exception as e:
            self.error(str(e))

    def clear_form(self):
        for entry in self.entries:
            entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.set_status("Form cleared")

    def on_select(self, event=None):
        values = self.get_selected_values() or []
        if not values:
            return
        for entry, val in zip(self.entries, values[1:]):
            entry.delete(0, tk.END)
            if val is not None and val != "":
                entry.insert(0, val)
        self.btn_update.state(["!disabled"])
        self.btn_delete.state(["!disabled"])
        self.set_status(f"Selected tournament {values[1]}")


class MatchesFrame(BaseCrudFrame):
    def __init__(self, master):
        super().__init__(master, ["ID", "Tournament", "Team1", "Team2", "Winner", "Map", "Date", "BO", "T1", "T2"])
        ttk.Label(self, text="Tournament").grid(row=1, column=0, sticky="w")
        self.tournament_cb = ttk.Combobox(self, state="readonly")
        self.tournament_cb.grid(row=1, column=1, sticky="ew")
        ttk.Label(self, text="Team1").grid(row=2, column=0, sticky="w")
        self.team1_cb = ttk.Combobox(self, state="readonly")
        self.team1_cb.grid(row=2, column=1, sticky="ew")
        ttk.Label(self, text="Team2").grid(row=3, column=0, sticky="w")
        self.team2_cb = ttk.Combobox(self, state="readonly")
        self.team2_cb.grid(row=3, column=1, sticky="ew")
        ttk.Label(self, text="Winner (optional)").grid(row=4, column=0, sticky="w")
        self.winner_cb = ttk.Combobox(self, state="readonly")
        self.winner_cb.grid(row=4, column=1, sticky="ew")
        ttk.Label(self, text="Map (optional)").grid(row=5, column=0, sticky="w")
        self.map_cb = ttk.Combobox(self, state="readonly")
        self.map_cb.grid(row=5, column=1, sticky="ew")
        labels = [
            "Date (YYYY-MM-DD)",
            "Best of",
            "Team1 score",
            "Team2 score",
        ]
        self.entries = []
        for idx, label in enumerate(labels):
            ttk.Label(self, text=label).grid(row=6 + idx, column=0, sticky="w")
            entry = ttk.Entry(self)
            entry.grid(row=6 + idx, column=1, sticky="ew")
            self.entries.append(entry)
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=2, padx=6)
        ttk.Button(self, text="Create", command=self.create).grid(row=1, column=3, padx=6)
        self.btn_update = ttk.Button(self, text="Update", command=self.update)
        self.btn_update.grid(row=2, column=3, padx=6)
        self.btn_delete = ttk.Button(self, text="Delete", command=self.delete)
        self.btn_delete.grid(row=3, column=3, padx=6)
        ttk.Button(self, text="Clear form", command=self.clear_form).grid(row=4, column=3, padx=6, pady=(4, 0))
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.refresh()

    def refresh(self):
        # refresh table and dropdown options
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
        self.set_tree(rows)
        tournament_options = fetch_all("SELECT tournament_id, name FROM tournaments ORDER BY start_date DESC NULLS LAST, name")
        team_options = fetch_all("SELECT team_id, team_name FROM teams ORDER BY team_name")
        map_options = fetch_all("SELECT map_id, map_name FROM maps ORDER BY map_name")
        formatted_t = [""] + [f"{row[0]} - {row[1]}" for row in tournament_options]
        formatted_team = [""] + [f"{row[0]} - {row[1]}" for row in team_options]
        formatted_map = [""] + [f"{row[0]} - {row[1]}" for row in map_options]
        self.tournament_cb["values"] = formatted_t
        self.team1_cb["values"] = formatted_team
        self.team2_cb["values"] = formatted_team
        self.winner_cb["values"] = formatted_team
        self.map_cb["values"] = formatted_map
        self.set_status("Loaded matches")

    def create(self):
        date_val, best_of_val, t1_score, t2_score = [e.get() for e in self.entries]
        try:
            tid = parse_combo_id(self.tournament_cb.get())
            team1 = parse_combo_id(self.team1_cb.get())
            team2 = parse_combo_id(self.team2_cb.get())
            if tid is None or team1 is None or team2 is None:
                self.error("tournament and both teams are required")
                return
            winner = parse_combo_id(self.winner_cb.get())
            map_id = parse_combo_id(self.map_cb.get())
            match_date = parse_date(date_val)
            best_of = parse_int(best_of_val) or 1
            t1s = parse_int(t1_score) or 0
            t2s = parse_int(t2_score) or 0
            # push validation down to validate_and_insert_match
            mid = execute_returning(
                "SELECT validate_and_insert_match(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (tid, team1, team2, winner, map_id, match_date, best_of, t1s, t2s),
            )
            messagebox.showinfo("Success", f"Created match {mid}")
            self.refresh()
            self.set_status(f"Created match {mid}")
            self.clear_form()
        except Exception as e:
            self.error(str(e))

    def update(self):
        mid = self.get_selected_id()
        if not mid:
            self.error("Select a match to update")
            return
        updates = {
            "tournament_id": parse_combo_id(self.tournament_cb.get()),
            "team1_id": parse_combo_id(self.team1_cb.get()),
            "team2_id": parse_combo_id(self.team2_cb.get()),
            "winner_team_id": parse_combo_id(self.winner_cb.get()),
            "map_id": parse_combo_id(self.map_cb.get()),
            "match_date": parse_date(self.entries[0].get()),
            "best_of": parse_int(self.entries[1].get()),
            "team1_score": parse_int(self.entries[2].get()),
            "team2_score": parse_int(self.entries[3].get()),
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            self.error("Enter at least one field to update")
            return
        try:
            sets = ", ".join(f"{k}=%s" for k in updates)
            params = list(updates.values()) + [mid]
            execute(f"UPDATE matches SET {sets} WHERE match_id=%s", params)
            self.refresh()
            self.set_status(f"Updated match {mid}")
        except Exception as e:
            self.error(str(e))

    def delete(self):
        mid = self.get_selected_id()
        if not mid:
            self.error("Select a match to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected match?"):
            return
        try:
            execute("DELETE FROM matches WHERE match_id=%s", (mid,))
            self.refresh()
            self.clear_form()
            self.set_status(f"Deleted match {mid}")
        except Exception as e:
            self.error(str(e))

    def clear_form(self):
        for cb in (self.tournament_cb, self.team1_cb, self.team2_cb, self.winner_cb, self.map_cb):
            cb.set("")
        for entry in self.entries:
            entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())
        self.btn_update.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.set_status("Form cleared")

    def on_select(self, event=None):
        values = self.get_selected_values() or []
        if not values:
            return
        # we don’t have IDs in the grid, so leave dropdowns blank and prefill basic numeric fields
        for entry, val in zip(self.entries, values[6:]):
            entry.delete(0, tk.END)
            if val is not None and val != "":
                entry.insert(0, val)
        self.btn_update.state(["!disabled"])
        self.btn_delete.state(["!disabled"])
        self.set_status(f"Selected match {values[0]}")


class ResultsFrame(BaseCrudFrame):
    def __init__(self, master):
        super().__init__(master, ["ID", "Tournament", "Team", "Placement", "Earnings"])
        ttk.Label(self, text="Tournament").grid(row=1, column=0, sticky="w")
        self.tournament_cb = ttk.Combobox(self, state="readonly")
        self.tournament_cb.grid(row=1, column=1, sticky="ew")
        ttk.Label(self, text="Team").grid(row=2, column=0, sticky="w")
        self.team_cb = ttk.Combobox(self, state="readonly")
        self.team_cb.grid(row=2, column=1, sticky="ew")
        labels = ["Placement", "Earnings"]
        self.entries = []
        for idx, label in enumerate(labels):
            ttk.Label(self, text=label).grid(row=3 + idx, column=0, sticky="w")
            entry = ttk.Entry(self)
            entry.grid(row=3 + idx, column=1, sticky="ew")
            self.entries.append(entry)
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=2, padx=6)
        ttk.Button(self, text="Create", command=self.create).grid(row=1, column=3, padx=6)
        self.btn_delete = ttk.Button(self, text="Delete", command=self.delete)
        self.btn_delete.grid(row=2, column=3, padx=6)
        ttk.Button(self, text="Clear form", command=self.clear_form).grid(row=3, column=3, padx=6, pady=(4, 0))
        self.btn_delete.state(["disabled"])
        self.refresh()

    def refresh(self):
        rows = fetch_all(
            """
            SELECT r.result_id, t.name, tm.team_name, r.placement, r.earnings
            FROM tournament_results r
            JOIN tournaments t ON r.tournament_id = t.tournament_id
            JOIN teams tm ON r.team_id = tm.team_id
            ORDER BY t.start_date DESC NULLS LAST, r.placement
            """
        )
        self.set_tree(rows)
        tournament_options = fetch_all("SELECT tournament_id, name FROM tournaments ORDER BY start_date DESC NULLS LAST, name")
        team_options = fetch_all("SELECT team_id, team_name FROM teams ORDER BY team_name")
        self.tournament_cb["values"] = [""] + [f"{row[0]} - {row[1]}" for row in tournament_options]
        self.team_cb["values"] = [""] + [f"{row[0]} - {row[1]}" for row in team_options]
        self.set_status("Loaded results")

    def create(self):
        placement, earnings = [e.get() for e in self.entries]
        if not self.tournament_cb.get().strip() or not self.team_cb.get().strip() or not placement.strip():
            self.error("tournament, team, placement are required")
            return
        try:
            tid = parse_combo_id(self.tournament_cb.get())
            team = parse_combo_id(self.team_cb.get())
            placement_val = parse_int(placement)
            earnings_val = parse_decimal(earnings) or Decimal("0")
            rid = execute_returning(
                """
                INSERT INTO tournament_results (tournament_id, team_id, placement, earnings)
                VALUES (%s, %s, %s, %s)
                RETURNING result_id
                """,
                (tid, team, placement_val, earnings_val),
            )
            messagebox.showinfo("Success", f"Created result {rid}")
            self.refresh()
            self.set_status(f"Created result {rid}")
            self.clear_form()
        except Exception as e:
            self.error(str(e))

    def delete(self):
        rid = self.get_selected_id()
        if not rid:
            self.error("Select a result to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected result?"):
            return
        try:
            execute("DELETE FROM tournament_results WHERE result_id=%s", (rid,))
            self.refresh()
            self.clear_form()
            self.set_status(f"Deleted result {rid}")
        except Exception as e:
            self.error(str(e))

    def clear_form(self):
        self.tournament_cb.set("")
        self.team_cb.set("")
        for entry in self.entries:
            entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())
        self.btn_delete.state(["disabled"])
        self.set_status("Form cleared")

    def on_select(self, event=None):
        values = self.get_selected_values() or []
        if not values:
            return
        # dropdowns need explicit choice; prefill placement/earnings
        for entry, val in zip(self.entries, values[3:]):
            entry.delete(0, tk.END)
            if val is not None and val != "":
                entry.insert(0, val)
        self.btn_delete.state(["!disabled"])
        self.set_status(f"Selected result {values[0]}")


class QueriesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.sort_dir = {}
        self.headers = ["C1", "C2", "C3"]
        ttk.Button(self, text="Earnings by team", command=self.earnings).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(self, text="Wins by map", command=self.wins).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(self, text="Active roster counts", command=self.roster).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(self, text="Team summary (server fn)", command=self.team_summary).grid(row=0, column=3, padx=4, pady=4)

        self.tree = ttk.Treeview(self, columns=self.headers, show="headings", height=12)
        for i in self.headers:
            self.tree.heading(i, text=i, command=lambda c=i: self.sort_column(c))
            self.tree.column(i, width=160, anchor=tk.W)
        self.tree.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._refresh_heading_labels()

    def set_headers(self, headers):
        self.headers = headers
        self.tree["columns"] = headers
        for h in headers:
            self.tree.heading(h, text=h, command=lambda c=h: self.sort_column(c))
            self.tree.column(h, width=160, anchor=tk.W)
        self.sort_dir = {}
        self._refresh_heading_labels()

    def set_rows(self, rows):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def sort_column(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        descending = self.sort_dir.get(col, False)
        def keyfn(t):
            val = t[0]
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
            return str(val).lower()
        items.sort(key=keyfn, reverse=descending)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self.sort_dir[col] = not descending
        self._refresh_heading_labels(active=col, used_desc=descending)

    def _refresh_heading_labels(self, active=None, used_desc=False):
        for h in self.headers:
            indicator = ""
            if h == active:
                indicator = " v" if used_desc else " ^"
            self.tree.heading(h, text=f"{h}{indicator}", command=lambda c=h: self.sort_column(c))

    def earnings(self):
        headers = ["Team", "Total Earnings"]
        self.set_headers(headers)
        rows = fetch_all(
            """
            SELECT tm.team_name, SUM(r.earnings) AS total_earnings
            FROM tournament_results r
            JOIN teams tm ON r.team_id = tm.team_id
            GROUP BY tm.team_name
            ORDER BY total_earnings DESC
            """
        )
        self.set_rows(rows)

    def wins(self):
        headers = ["Map", "Wins"]
        self.set_headers(headers)
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
        self.set_rows(rows)

    def roster(self):
        headers = ["Team", "Active Players"]
        self.set_headers(headers)
        rows = fetch_all(
            """
            SELECT tm.team_name, COUNT(*) FILTER (WHERE r.is_active) AS active_players
            FROM teams tm
            LEFT JOIN team_roster r ON tm.team_id = r.team_id AND r.is_active
            GROUP BY tm.team_name
            ORDER BY tm.team_name
            """
        )
        self.set_rows(rows)

    def team_summary(self):
        headers = ["Team", "Matches", "Wins", "Earnings"]
        self.set_headers(headers)
        rows = fetch_all(
            """
            SELECT team_name, matches_played, wins, total_earnings
            FROM team_summary()
            ORDER BY team_name
            """
        )
        self.set_rows(rows)


def launch():
    root = tk.Tk()
    root.title("CS2 Esports DB")
    root.geometry("1100x700")
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    nb.add(TeamsFrame(nb), text="Teams")
    nb.add(PlayersFrame(nb), text="Players")
    nb.add(TournamentsFrame(nb), text="Tournaments")
    nb.add(MatchesFrame(nb), text="Matches")
    nb.add(ResultsFrame(nb), text="Results")
    nb.add(QueriesFrame(nb), text="Queries")
    root.mainloop()


if __name__ == "__main__":
    launch()
