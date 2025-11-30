import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, date as _date
from theDB import *

refs = None

def show_game_details(index, game_data=None):
    game = game_data
    if not game: return
    
    if refs and isinstance(refs, dict):
        refs["selected_game"] = game
    
    s1 = int(game.get('team1_score') or 0)
    s2 = int(game.get('team2_score') or 0)
    
    is_final = bool(game.get('is_final'))
    
    winner_text = "TBD"
    if is_final:
        if game.get('winner_team_id'):
            # Determine winner name based on ID
            w_id = game.get('winner_team_id')
            if w_id == game.get('team1_id'):
                winner_text = game.get('team1')
            elif w_id == game.get('team2_id'):
                winner_text = game.get('team2')
        else:
            winner_text = "Tie"

    details = (
        f"Matchup: {game.get('team1')} vs {game.get('team2')}\n"
        f"Venue:   {game.get('venue')}\n\n"
        f"Date:    {game.get('date')}\n"
        f"Time:    {game.get('start')} - {game.get('end')}\n\n"
        f"Score:   {s1} - {s2}\n"
        f"Status:  {'Final' if is_final else 'Active'}\n"
        f"Winner:  {winner_text if is_final else 'N/A'}"
    )
    if refs.get("details_content"):
        refs["details_content"].configure(text=details)

def _season_windows_for_year(year):
    s_helper = Season()
    start, _ = s_helper.get_range("Pre-season", year)
    _, end = s_helper.get_range("Off-season", year + 1)
    return start, end

def _season_from_iso(date_iso):
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
    except Exception:
        return ""
    
    s_helper = Season()
    for season_name in s_helper.season_definitions:
        for anchor in (dt.year, dt.year - 1):
            start, end = s_helper.get_range(season_name, anchor)
            if start and start <= dt <= end:
                return season_name
    return ""

def _parse_iso(date_iso):
    try:
        if not date_iso: return None
        return datetime.strptime(date_iso, "%Y-%m-%d").date()
    except Exception:
        return None

def _fetch_games_from_db_direct():
    games = []
    try:
        cur = mydb.cursor()
        cur.execute("""
        SELECT g.id, t1.teamName AS team1, t2.teamName AS team2, v.venueName AS venue, 
               g.game_date AS date, g.start_time AS start, g.end_time AS end, g.is_final,
               g.team1_id, g.team2_id, g.team1_score, g.team2_score, g.winner_team_id
        FROM games g
        LEFT JOIN teams t1 ON g.team1_id = t1.id
        LEFT JOIN teams t2 ON g.team2_id = t2.id
        LEFT JOIN venues v ON g.venue_id = v.id
        ORDER BY g.game_date, g.start_time
        """)
        rows = cur.fetchall()
        for r in rows:
            g = dict(r)
            if not g.get('start'): g['start'] = '00:00'
            if not g.get('end'): g['end'] = '00:00'
            games.append(g)
        cur.close()
    except Exception as e:
        print(f"Direct DB fetch failed: {e}")
    return games

def _compute_season_start_years_with_games():
    cur = mydb.cursor()
    try:
        cur.execute("SELECT MIN(substr(game_date,1,4)) as miny, MAX(substr(game_date,1,4)) as maxy FROM games WHERE game_date IS NOT NULL")
        r = cur.fetchone()
        if not r or not r['miny']:
            return []
        
        miny, maxy = int(r['miny']), int(r['maxy'])
        years_with_games = []
        for y in range(max(1900, miny - 1), maxy + 1):
            s, e = _season_windows_for_year(y)
            cur.execute("SELECT 1 FROM games WHERE game_date BETWEEN ? AND ? LIMIT 1", (s.isoformat(), e.isoformat()))
            if cur.fetchone():
                years_with_games.append(y)
        years_with_games.sort(reverse=True)
        return years_with_games
    finally:
        cur.close()

def _format_season_header(year):
    s, e = _season_windows_for_year(year)
    return f"Season {e.year} — {s} → {e}"

def refresh_scheduled_games_table(table_frame):
    for widget in table_frame.winfo_children():
        widget.destroy()

    # FORCE RELOAD to see 'Ended' status immediately
    src_games = _fetch_games_from_db_direct()
    
    # Update shared list if possible
    try:
        import scheduleGameTab as sgt
        sgt.scheduled_games.clear()
        sgt.scheduled_games.extend(src_games)
    except Exception:
        pass

    years = _compute_season_start_years_with_games()

    if not years:
        ctk.CTkLabel(table_frame, text="No scheduled seasons found (DB empty or dates invalid).").pack(padx=8, pady=8)
        return

    for year in years:
        start_dt, end_dt = _season_windows_for_year(year)
        
        # Header
        h = ctk.CTkFrame(table_frame, fg_color="#1E1E1E")
        h.pack(fill="x", padx=8, pady=(12, 6))
        ctk.CTkLabel(h, text=_format_season_header(year), font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=6)

        # Columns
        cols = ctk.CTkFrame(table_frame, fg_color="#1F1F1F")
        cols.pack(fill="x", padx=8, pady=(0, 4))
        
        # REMOVED "Edit" from headers
        headers = ["Team 1", "Team 2", "Venue", "Date", "Season", "Score", "Status", "View", "Delete"]
        for i, t in enumerate(headers):
            # Adjusted weight logic for the reduced column count
            cols.grid_columnconfigure(i, weight=1 if i <= 6 else 0)
            ctk.CTkLabel(cols, text=t, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=i, padx=8, pady=4, sticky="w")

        # Filter games
        group_games = []
        for g in src_games:
            dt = _parse_iso(g.get('date'))
            if dt and start_dt <= dt <= end_dt:
                group_games.append(g)
        
        group_games.sort(key=lambda x: (x.get('date', ''), x.get('start', '')))

        if not group_games:
            ctk.CTkLabel(table_frame, text="(No games in this season window)").pack()
            continue

        for idx_in_group, game in enumerate(group_games):
            row = ctk.CTkFrame(table_frame, fg_color="#2A2A2A")
            row.pack(fill="x", padx=8, pady=2)
            
            # Adjusted range to 9 columns (since Edit was removed)
            for i in range(9): 
                row.grid_columnconfigure(i, weight=1 if i <= 6 else 0)

            ctk.CTkLabel(row, text=game.get('team1')).grid(row=0, column=0, sticky="w", padx=8)
            ctk.CTkLabel(row, text=game.get('team2')).grid(row=0, column=1, sticky="w", padx=8)
            ctk.CTkLabel(row, text=game.get('venue')).grid(row=0, column=2, sticky="w", padx=8)
            ctk.CTkLabel(row, text=game.get('date')).grid(row=0, column=3, sticky="w", padx=8)
            ctk.CTkLabel(row, text=_season_from_iso(game.get('date'))).grid(row=0, column=4, sticky="w", padx=8)
            
            s1 = int(game.get('team1_score') or 0)
            s2 = int(game.get('team2_score') or 0)
            score_txt = f"{s1} - {s2}"
            ctk.CTkLabel(row, text=score_txt).grid(row=0, column=5, sticky="w", padx=8)

            # Status
            is_fin = bool(game.get('is_final'))
            status = "Final" if is_fin else "Active"
            color = "#D9534F" if is_fin else "#7CFC00"
            ctk.CTkLabel(row, text=status, text_color=color).grid(row=0, column=6, sticky="w", padx=8)
            
            ctk.CTkButton(row, text="View", width=60, command=lambda g=game, i=idx_in_group: show_game_details(i, g)).grid(row=0, column=7, padx=4)
            
            # Edit button removed here
            
            # Delete button moved to column 8
            ctk.CTkButton(row, text="Delete", width=60, fg_color="#F44336", command=lambda i=idx_in_group: delete_scheduled_game(i)).grid(row=0, column=8, padx=4)

def delete_scheduled_game(index):
    src_games = _fetch_games_from_db_direct()
    if index < 0 or index >= len(src_games): return
    if messagebox.askyesno("Delete", "Delete this game?"):
        sm = ScheduleManager()
        sm.deleteGame(src_games[index]['id'])
        if refs.get('scheduled_games_table'):
            refresh_scheduled_games_table(refs['scheduled_games_table'])

def _get_scheduled_games_source():
    try:
        import scheduleGameTab as sgt
        if hasattr(sgt, 'scheduled_games') and sgt.scheduled_games:
            return sgt.scheduled_games
    except: pass
    return sgt.scheduled_games