import customtkinter as ctk
from theDB import mydb

# This module provides standings UI helper. mainGui will set refs when wiring.
refs = {}

def refresh_standings_table(container):
    """
    Refresh the standings display inside the provided scrollable container/frame.
    Uses games.winner_team_id (only for games where is_final = 1) to compute wins/losses.
    Displays: Rank | Team | Wins | Losses | Total Points
    Sorted by wins DESC, then totalPoints DESC, then teamName.
    """
    # Clear existing widgets
    for w in container.winfo_children():
        try:
            w.destroy()
        except Exception:
            pass

    # Header
    header = ctk.CTkFrame(container, fg_color="#1F1F1F")
    header.pack(fill="x", padx=8, pady=6)
    header.grid_columnconfigure(0, weight=1)
    header.grid_columnconfigure(1, weight=3)
    header.grid_columnconfigure(2, weight=1)
    header.grid_columnconfigure(3, weight=1)

    ctk.CTkLabel(header, text="Rank", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=8, pady=6, sticky="w")
    ctk.CTkLabel(header, text="Team", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=8, pady=6, sticky="w")
    ctk.CTkLabel(header, text="Wins", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=2, padx=8, pady=6, sticky="w")
    ctk.CTkLabel(header, text="Losses", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=3, padx=8, pady=6, sticky="w")
    ctk.CTkLabel(header, text="Total Points", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=4, padx=8, pady=6, sticky="w")

    # Query teams and compute wins/losses via subqueries (considers only is_final=1 games)
    cursor = mydb.cursor()
    try:
        cursor.execute("""
            SELECT
                t.id,
                t.teamName,
                COALESCE(t.totalPoints, 0) as totalPoints,
                COALESCE((
                    SELECT COUNT(*) FROM games g
                    WHERE g.is_final = 1 AND g.winner_team_id = t.id
                ), 0) AS wins,
                COALESCE((
                    SELECT COUNT(*) FROM games g
                    WHERE g.is_final = 1
                      AND (g.home_team_id = t.id OR g.away_team_id = t.id)
                      AND (g.winner_team_id IS NOT NULL AND g.winner_team_id != t.id)
                ), 0) AS losses
            FROM teams t
            ORDER BY wins DESC, totalPoints DESC, t.teamName COLLATE NOCASE
        """)
        teams = cursor.fetchall()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if not teams:
        ctk.CTkLabel(container, text="No teams found.", anchor="w").pack(padx=8, pady=8)
        # expose ref even when empty
        try:
            if isinstance(refs, dict):
                refs['standings_table'] = container
        except Exception:
            pass
        return

    # Data rows
    for idx, row in enumerate(teams, start=1):
        row_frame = ctk.CTkFrame(container, fg_color="#2A2A2A")
        row_frame.pack(fill="x", padx=8, pady=2)
        # configure columns for consistent layout
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=3)
        row_frame.grid_columnconfigure(2, weight=1)
        row_frame.grid_columnconfigure(3, weight=1)
        row_frame.grid_columnconfigure(4, weight=1)

        team_name = row["teamName"]
        wins = row["wins"]
        losses = row["losses"]
        total_points = row["totalPoints"] if row["totalPoints"] is not None else 0

        ctk.CTkLabel(row_frame, text=str(idx)).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        ctk.CTkLabel(row_frame, text=team_name).grid(row=0, column=1, padx=8, pady=6, sticky="w")
        ctk.CTkLabel(row_frame, text=str(wins)).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkLabel(row_frame, text=str(losses)).grid(row=0, column=3, padx=8, pady=6, sticky="w")
        ctk.CTkLabel(row_frame, text=str(total_points)).grid(row=0, column=4, padx=8, pady=6, sticky="w")

    # Let callers (mainGui) know where the standings are displayed
    try:
        if isinstance(refs, dict):
            refs['standings_table'] = container
    except Exception:
        pass