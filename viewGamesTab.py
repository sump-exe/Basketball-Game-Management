import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, date as _date
from theDB import *

# This module displays and edits scheduled games.
# mainGui will set:
#   refs, scheduled_games (from file3), show_game_details (from file3),
#   edit and delete functions are contained here.
refs = {}
scheduled_games = []
show_game_details = lambda i: None  # will be set by mainGui to file3.show_game_details

def _season_range_for_year(season, year):
    """
    Return (start_date, end_date) for the given season and season-start year.
    Handles seasons that span calendar years (Regular Season).
    """
    mapping = {
        "Pre-season": ((9, 25), (10, 16)),
        "Regular Season": ((10, 17), (4, 16)),  # crosses year boundary
        "Play-in": ((4, 17), (4, 24)),
        "Playoff": ((4, 25), (6, 8)),
        "Finals": ((6, 9), (6, 24)),
        "Off-season": ((6, 25), (9, 24)),
    }
    if season not in mapping:
        return None, None
    (sm, sd), (em, ed) = mapping[season]
    start = _date(year, sm, sd)
    if (em, ed) < (sm, sd):
        end = _date(year + 1, em, ed)
    else:
        end = _date(year, em, ed)
    return start, end

def _season_windows_for_year(year):
    """Return window (start, end) spanning Pre-season of year through Off-season of year+1."""
    start, _ = _season_range_for_year("Pre-season", year)
    _, end = _season_range_for_year("Off-season", year + 1)
    return start, end

def _season_for_date(dt):
    """
    Determine season name for a given date object.
    Tries interpreting season windows anchored at dt.year and dt.year-1,
    so dates like March 2025 are matched to the 2024-2025 Regular Season if appropriate.
    Returns season string or empty string if unknown.
    """
    seasons = [
        "Pre-season",
        "Regular Season",
        "Play-in",
        "Playoff",
        "Finals",
        "Off-season"
    ]
    for season in seasons:
        # Try anchor at dt.year and dt.year-1
        for anchor in (dt.year, dt.year - 1):
            start, end = _season_range_for_year(season, anchor)
            if start is None:
                continue
            if start <= dt <= end:
                return season
    return ""

def _season_from_iso(date_iso):
    """Safe wrapper to parse ISO date string (YYYY-MM-DD) and return season name."""
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
    except Exception:
        return ""
    return _season_for_date(dt)

def _parse_iso(date_iso):
    """Return date object or None for invalid/empty input."""
    try:
        if not date_iso:
            return None
        return datetime.strptime(date_iso, "%Y-%m-%d").date()
    except Exception:
        return None

def _compute_season_start_years_with_games_from_schedule():
    """
    Determine season-start years that have at least one scheduled game within
    their season window, based on the in-memory scheduled_games list.
    Returns list of ints (years), newest first.
    """
    dates = []
    for g in scheduled_games:
        d = _parse_iso(g.get('date'))
        if d:
            dates.append(d.year)
    if not dates:
        return []

    miny = min(dates)
    maxy = max(dates)
    years_with_games = []
    start_candidate = max(1900, miny - 1)
    end_candidate = maxy
    for y in range(start_candidate, end_candidate + 1):
        s, e = _season_windows_for_year(y)
        # check any scheduled game date falls between s and e
        found = False
        for g in scheduled_games:
            dt = _parse_iso(g.get('date'))
            if dt and s <= dt <= e:
                found = True
                break
        if found:
            years_with_games.append(y)
    years_with_games.sort(reverse=True)
    return years_with_games

def on_view_click(index, game):
    """Called when the View button is pressed."""
    # Set selected game
    refs["selected_game"] = {
        "id": game["id"],
        "team1_id": game["team1_id"],
        "team2_id": game["team2_id"]
    }

    panel = refs.get("game_details_frame")
    if not panel:
        return

    # Clear the panel (we are replacing its contents)
    for w in panel.winfo_children():
        try:
            w.destroy()
        except Exception:
            pass

    # --- RECREATE THE DETAILS LABEL ---
    details_label = ctk.CTkLabel(
        panel,
        text="Loading...",
        justify="left",
        anchor="nw"
    )
    details_label.pack(fill="both", expand=True, padx=10, pady=10)

    # Replace old label reference
    refs["details_content"] = details_label

    # Defer calling show_game_details to next event loop turn to avoid first-click missing configure
    try:
        app_widget = refs.get('app')
        if hasattr(app_widget, 'after'):
            app_widget.after(0, lambda i=index: show_game_details(i))
        else:
            show_game_details(index)
    except Exception:
        try:
            show_game_details(index)
        except Exception:
            pass

    # Mark selected game again (redundant but preserves original behavior)
    refs["selected_game"] = {
        "id": game["id"],
        "team1_id": game["team1_id"],
        "team2_id": game["team2_id"]
    }

def refresh_scheduled_games_table(table_frame):
    """Refresh the table of scheduled games grouped by season-start year (Pre-season..next year's Off-season)."""
    # Clear existing rows
    for widget in table_frame.winfo_children():
        try:
            widget.destroy()
        except Exception:
            pass

    # Build quick id -> index map for callbacks
    id_to_index = {}
    for idx, g in enumerate(scheduled_games):
        gid = g.get('id')
        if gid is not None:
            id_to_index[gid] = idx

    # Determine seasons that have games (newest first)
    years = _compute_season_start_years_with_games_from_schedule()

    if not years:
        # Fallback: show flat header and message if no seasons
        header_frame = ctk.CTkFrame(table_frame, fg_color="#1F1F1F")
        header_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(header_frame, text="No scheduled seasons found.", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=8, pady=8)
        return

    # For each season-start year, render a block
    for year in years:
        start_dt, end_dt = _season_windows_for_year(year)

        # Season header
        header_frame = ctk.CTkFrame(table_frame, fg_color="#1E1E1E")
        header_frame.pack(fill="x", padx=8, pady=(12, 6))
        header_frame.grid_columnconfigure(0, weight=1)
        header_lbl = ctk.CTkLabel(header_frame, text=f"Season {year} — {start_dt.isoformat()} → {end_dt.isoformat()}", font=ctk.CTkFont(size=14, weight="bold"))
        header_lbl.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        # Column headers (same columns as before)
        cols = ctk.CTkFrame(table_frame, fg_color="#1F1F1F")
        cols.pack(fill="x", padx=8, pady=(0,4))
        # match grid columns to rows (0..9)
        for ci in range(10):
            # give flexible weights to first 7 columns so they expand equally; action buttons keep minimal width
            cols.grid_columnconfigure(ci, weight=(1 if ci <= 6 else 0))
        ctk.CTkLabel(cols, text="Team 1", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Team 2", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Venue", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=2, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Date", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=3, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Season", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=4, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Time", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=5, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Status", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=6, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="View", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=7, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Edit", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=8, padx=8, pady=4, sticky="w")
        ctk.CTkLabel(cols, text="Delete", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=9, padx=8, pady=4, sticky="w")

        # Collect games in this window and sort by date then start time
        group_games = []
        for g in scheduled_games:
            dt = _parse_iso(g.get('date'))
            if dt and start_dt <= dt <= end_dt:
                group_games.append(g)
        # sort by date then start time (safe defaults)
        def _sort_key(g):
            dt = _parse_iso(g.get('date')) or _date.min
            st = g.get('start') or '00:00'
            return (dt, st)
        group_games.sort(key=_sort_key)

        if not group_games:
            empty_lbl = ctk.CTkLabel(table_frame, text="(No games in this season window)", anchor="w", text_color="#BBBBBB")
            empty_lbl.pack(fill="x", padx=16, pady=(6,8))
            continue

        # Render rows for this group
        for game in group_games:
            gid = game.get('id')
            idx = id_to_index.get(gid, None)
            row_frame = ctk.CTkFrame(table_frame, fg_color="#2A2A2A")
            row_frame.pack(fill="x", padx=8, pady=2)

            # IMPORTANT: ensure row_frame's grid columns match header 'cols' grid so content aligns under header
            for ci in range(10):
                row_frame.grid_columnconfigure(ci, weight=(1 if ci <= 6 else 0))

            # columns align to the header columns above
            ctk.CTkLabel(row_frame, text=game.get('team1')).grid(row=0, column=0, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(row_frame, text=game.get('team2')).grid(row=0, column=1, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(row_frame, text=game.get('venue')).grid(row=0, column=2, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(row_frame, text=game.get('date')).grid(row=0, column=3, padx=8, pady=4, sticky="w")

            # Season column (derived from game date)
            season_name = _season_from_iso(game.get('date') or "")
            ctk.CTkLabel(row_frame, text=season_name).grid(row=0, column=4, padx=8, pady=4, sticky="w")

            ctk.CTkLabel(row_frame, text=f"{game.get('start', '00:00')} - {game.get('end', '00:00')}").grid(row=0, column=5, padx=8, pady=4, sticky="w")

            # Status label: query DB for is_final for this game id
            try:
                cursor = mydb.cursor()
                try:
                    cursor.execute("SELECT is_final FROM games WHERE id = ?", (gid,))
                    r = cursor.fetchone()
                    is_final = bool(r['is_final']) if r and 'is_final' in r.keys() else False
                finally:
                    try:
                        cursor.close()
                    except Exception:
                        pass
            except Exception:
                is_final = False

            if is_final:
                status_lbl = ctk.CTkLabel(row_frame, text="Ended", text_color="#D9534F")  # red-ish
            else:
                status_lbl = ctk.CTkLabel(row_frame, text="Active", text_color="#7CFC00")  # green-ish
            status_lbl.grid(row=0, column=6, padx=8, pady=4, sticky="w")

            # View button (preserve behavior; index may be None if id missing — fallback to using game object)
            view_cmd_index = idx if idx is not None else None
            if view_cmd_index is not None:
                view_btn = ctk.CTkButton(row_frame, text="View", width=60, height=30,
                                        command=lambda i=view_cmd_index, g=game: on_view_click(i, g),
                                        hover_color="#4A90E2", fg_color="#1F75FE")
            else:
                # fallback uses a lambda that finds the index dynamically
                view_btn = ctk.CTkButton(row_frame, text="View", width=60, height=30,
                                        command=lambda g=game: on_view_click(scheduled_games.index(g), g),
                                        hover_color="#4A90E2", fg_color="#1F75FE")
            view_btn.grid(row=0, column=7, padx=4, pady=4, sticky="w")

            # Edit button
            if idx is not None:
                edit_btn = ctk.CTkButton(row_frame, text="Edit", width=60, height=30,
                                         command=lambda i=idx: edit_scheduled_game(i),
                                         hover_color="#FFA500", fg_color="#4CAF50")
            else:
                edit_btn = ctk.CTkButton(row_frame, text="Edit", width=60, height=30,
                                         command=lambda g=game: edit_scheduled_game(scheduled_games.index(g)),
                                         hover_color="#FFA500", fg_color="#4CAF50")
            edit_btn.grid(row=0, column=8, padx=4, pady=4)

            # Delete button
            if idx is not None:
                delete_btn = ctk.CTkButton(row_frame, text="Delete", width=60, height=30,
                                           command=lambda i=idx: delete_scheduled_game(i),
                                           hover_color="#FF4500", fg_color="#F44336")
            else:
                delete_btn = ctk.CTkButton(row_frame, text="Delete", width=60, height=30,
                                           command=lambda g=game: delete_scheduled_game(scheduled_games.index(g)),
                                           hover_color="#FF4500", fg_color="#F44336")
            delete_btn.grid(row=0, column=9, padx=4, pady=4)

def edit_scheduled_game(index):
    if index < 0 or index >= len(scheduled_games):
        return
    game = scheduled_games[index]
    win = ctk.CTkToplevel(refs.get('app') if refs.get('app') else None)
    win.title("Edit Scheduled Game")
    win.geometry("420x350")
    win.transient(refs.get('app') if refs.get('app') else None)

    ctk.CTkLabel(win, text="Team 1:").pack(pady=(12,4), anchor="w", padx=12)
    team1_entry = ctk.CTkEntry(win)
    team1_entry.insert(0, game['team1'])
    team1_entry.pack(fill="x", padx=12)

    ctk.CTkLabel(win, text="Team 2:").pack(pady=(8,4), anchor="w", padx=12)
    team2_entry = ctk.CTkEntry(win)
    team2_entry.insert(0, game['team2'])
    team2_entry.pack(fill="x", padx=12)

    ctk.CTkLabel(win, text="Venue:").pack(pady=(8,4), anchor="w", padx=12)
    venue_entry = ctk.CTkEntry(win)
    venue_entry.insert(0, game['venue'])
    venue_entry.pack(fill="x", padx=12)

    ctk.CTkLabel(win, text="Date (YYYY-MM-DD):").pack(pady=(8,4), anchor="w", padx=12)
    date_entry = ctk.CTkEntry(win)
    date_entry.insert(0, game['date'])
    date_entry.pack(fill="x", padx=12)

    def save_edit():
        t1 = team1_entry.get().strip()
        t2 = team2_entry.get().strip()
        v = venue_entry.get().strip()
        d = date_entry.get().strip()
        # validate inputs
        try:
            from teamsTab import teams as _teams
            from venuesTab import venues as _venues
        except Exception:
            _teams = {}
            _venues = {}
        if not all([t1, t2, v, d]) or t1 == t2 or t1 not in _teams or t2 not in _teams or v not in _venues:
            messagebox.showwarning("Invalid", "Please fill all fields correctly and ensure teams/venue exist.")
            return
        # validate date format
        try:
            _ = datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Invalid", "Date must be in YYYY-MM-DD format.")
            return
        # Persist edit to DB if possible
        game = scheduled_games[index]
        game_id = game.get('id')
        # preserve existing times if present
        start = game.get('start', '00:00')
        end = game.get('end', '00:00')

        # Lookup IDs
        from theDB import ScheduleManager
        cur = ScheduleManager().mydb.cursor()
        try:
            cur.execute("SELECT id FROM teams WHERE teamName = ?", (t1,))
            home = cur.fetchone()
            cur.execute("SELECT id FROM teams WHERE teamName = ?", (t2,))
            away = cur.fetchone()
            cur.execute("SELECT id FROM venues WHERE venueName = ?", (v,))
            venue_row = cur.fetchone()
            if not home or not away or not venue_row:
                messagebox.showwarning("Invalid", "Selected teams or venue not found in DB.")
                return
            home_id = home['id']
            away_id = away['id']
            venue_id = venue_row['id']

            # Use the global ScheduleManager via theDB module's connection
            sm = ScheduleManager()
            if game_id:
                sm.updateGame(game_id, home_id, away_id, venue_id, d, start, end)
            else:
                # If no id, insert new record and then update times
                new_id = sm.scheduleGame(home_id, away_id, venue_id, d)
                sm.updateGame(new_id, home_id, away_id, venue_id, d, start, end)
        finally:
            try:
                cur.close()
            except Exception:
                pass

        # reload from DB and refresh UI
        try:
            from scheduleGameTab import load_scheduled_games_from_db as _load
            _load()
            from viewGamesTab import refresh_scheduled_games_table as _refresh
            _refresh(refs.get('scheduled_games_table'))
        except Exception:
            pass
        win.destroy()

    ctk.CTkButton(win, text="Save Changes", command=save_edit).pack(pady=12)

def delete_scheduled_game(index):
    if not (0 <= index < len(scheduled_games)):
        return
    if messagebox.askyesno("Delete Game", "Are you sure you want to delete this scheduled game?"):
        game = scheduled_games[index]
        game_id = game.get('id')
        if game_id:
            try:
                from theDB import ScheduleManager
                sm = ScheduleManager()
                sm.deleteGame(game_id)
            except Exception:
                messagebox.showwarning("Error", "Could not delete game from DB.")
        else:
            # fallback: remove from in-memory list
            try:
                scheduled_games.pop(index)
            except Exception:
                pass
        try:
            from scheduleGameTab import load_scheduled_games_from_db as _load
            _load()
            refresh_scheduled_games_table(refs.get('scheduled_games_table'))
        except Exception:
            pass