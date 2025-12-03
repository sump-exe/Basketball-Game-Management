import sqlite3
from pathlib import Path
from datetime import datetime

DB_FILE = Path(__file__).with_name('sports_schedule.db')

mydb = sqlite3.connect(str(DB_FILE))
mydb.row_factory = sqlite3.Row
cur = mydb.cursor()
cur.execute("PRAGMA foreign_keys = ON")

cur.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teamName TEXT NOT NULL UNIQUE,
    totalPoints INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    jerseyNumber INTEGER,
    points INTEGER DEFAULT 0,
    team_id INTEGER,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venueName TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL,
    capacity INTEGER NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS team_season_totals (
    team_id INTEGER,
    season_year INTEGER,
    totalPoints INTEGER DEFAULT 0,
    PRIMARY KEY (team_id, season_year),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS game_player_stats (
    game_id INTEGER,
    player_id INTEGER,
    points INTEGER DEFAULT 0,
    PRIMARY KEY (game_id, player_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
)
""")

cur_m = mydb.cursor()
existing_cols = [r[1] for r in cur_m.execute("PRAGMA table_info(games)").fetchall()]

if 'team1_id' not in existing_cols:
    cur_m.execute("""
    CREATE TABLE IF NOT EXISTS games_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1_id INTEGER,
        team2_id INTEGER,
        venue_id INTEGER,
        game_date TEXT,
        team1_score INTEGER DEFAULT 0,
        team2_score INTEGER DEFAULT 0,
        start_time TEXT DEFAULT '00:00',
        end_time TEXT DEFAULT '00:00',
        is_final INTEGER DEFAULT 0,
        winner_team_id INTEGER DEFAULT NULL,
        FOREIGN KEY (team1_id) REFERENCES teams(id),
        FOREIGN KEY (team2_id) REFERENCES teams(id),
        FOREIGN KEY (venue_id) REFERENCES venues(id)
    )
    """)
    has_home = 'home_team_id' in existing_cols
    has_away = 'away_team_id' in existing_cols
    has_home_score = 'home_score' in existing_cols
    has_away_score = 'away_score' in existing_cols
    has_start = 'start_time' in existing_cols
    has_end = 'end_time' in existing_cols
    has_is_final = 'is_final' in existing_cols
    has_winner = 'winner_team_id' in existing_cols

    select_parts = []
    if has_home: select_parts.append("home_team_id AS team1_id")
    else: select_parts.append("NULL AS team1_id")
    if has_away: select_parts.append("away_team_id AS team2_id")
    else: select_parts.append("NULL AS team2_id")
    select_parts.append("venue_id")
    select_parts.append("game_date")
    if has_home_score: select_parts.append("home_score AS team1_score")
    else: select_parts.append("0 AS team1_score")
    if has_away_score: select_parts.append("away_score AS team2_score")
    else: select_parts.append("0 AS team2_score")
    if has_start: select_parts.append("start_time")
    else: select_parts.append("'00:00' AS start_time")
    if has_end: select_parts.append("end_time")
    else: select_parts.append("'00:00' AS end_time")
    if has_is_final: select_parts.append("is_final")
    else: select_parts.append("0 AS is_final")
    if has_winner: select_parts.append("winner_team_id")
    else: select_parts.append("NULL AS winner_team_id")

    select_clause = ", ".join(select_parts)
    try:
        cur_m.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        if cur_m.fetchone():
            cur_m.execute(f"INSERT INTO games_new (team1_id, team2_id, venue_id, game_date, team1_score, team2_score, start_time, end_time, is_final, winner_team_id) SELECT {select_clause} FROM games")
            cur_m.execute("DROP TABLE IF EXISTS games")
        cur_m.execute("ALTER TABLE games_new RENAME TO games")
        mydb.commit()
    except Exception:
        try:
            cur_m.execute("DROP TABLE IF EXISTS games_new")
            mydb.commit()
        except Exception:
            pass

cur_m.close()

cur.execute("""
CREATE TABLE IF NOT EXISTS mvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    UNIQUE(player_id, year)
)
""")

mydb.commit()
cur.close()

class ScheduleManager:
    def __init__(self):
        self.mydb = mydb

    def addTeam(self, team):
        if isinstance(team, Team):
            cursor = self.mydb.cursor()
            cursor.execute("INSERT INTO teams (teamName, totalPoints) VALUES (?, ?)", (team.teamName, team.totalPoints))
            self.mydb.commit()
            team.id = cursor.lastrowid
            cursor.close()

    def addVenue(self, venue):
        if isinstance(venue, Venue):
            cursor = self.mydb.cursor()
            cursor.execute("INSERT INTO venues (venueName, location, capacity) VALUES (?, ?, ?)", (venue.venueName, venue.location, venue.capacity))
            self.mydb.commit()
            venue.venueID = cursor.lastrowid
            cursor.close()

    def gameResults(self, gameID):
        cursor = self.mydb.cursor()
        cursor.execute("""
        SELECT g.id, t1.teamName AS team1, t2.teamName AS team2, v.venueName, g.game_date, g.team1_score, g.team2_score
        FROM games g
        LEFT JOIN teams t1 ON g.team1_id = t1.id
        LEFT JOIN teams t2 ON g.team2_id = t2.id
        LEFT JOIN venues v ON g.venue_id = v.id
        WHERE g.id = ?
        """, (gameID,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return {
                'gameID': result['id'],
                'team1': result['team1'],
                'team2': result['team2'],
                'venue': result['venueName'],
                'date': result['game_date'],
                'score': f"{result['team1_score']}-{result['team2_score']}"
            }
        return None

    def scheduleGame(self, team1_id, team2_id, venue_id, game_date):
        cursor = self.mydb.cursor()
        cursor.execute("INSERT INTO games (team1_id, team2_id, venue_id, game_date, start_time, end_time, team1_score, team2_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (team1_id, team2_id, venue_id, game_date, '00:00', '00:00', 0, 0))
        self.mydb.commit()
        game_id = cursor.lastrowid
        cursor.close()
        return game_id

    def updateGame(self, game_id, team1_id, team2_id, venue_id, game_date, start_time='00:00', end_time='00:00'):
        cursor = self.mydb.cursor()
        cursor.execute("""
            UPDATE games SET team1_id = ?, team2_id = ?, venue_id = ?, game_date = ?, start_time = ?, end_time = ?
            WHERE id = ?
        """, (team1_id, team2_id, venue_id, game_date, start_time, end_time, game_id))
        self.mydb.commit()
        cursor.close()

    def deleteGame(self, game_id):
        cursor = self.mydb.cursor()
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        self.mydb.commit()
        cursor.close()

    def isGameFinal(self, game_id):
        cursor = self.mydb.cursor()
        cursor.execute("SELECT is_final FROM games WHERE id = ?", (game_id,))
        r = cursor.fetchone()
        cursor.close()
        return bool(r['is_final']) if r and 'is_final' in r.keys() else False

    def endGame(self, game_id):
        cursor = self.mydb.cursor()
        cursor.execute("SELECT team1_id, team2_id, team1_score, team2_score FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            raise ValueError("Game not found")

        t1_id = row['team1_id']
        t2_id = row['team2_id']
        t1_score = row['team1_score']
        t2_score = row['team2_score']

        winner = None
        if t1_score > t2_score:
            winner = t1_id
        elif t2_score > t1_score:
            winner = t2_id
        else:
            winner = None
            
        cursor.execute("UPDATE games SET is_final = 1, winner_team_id = ? WHERE id = ?", (winner, game_id))
        self.mydb.commit()
        cursor.close()
        return winner

class Venue:
    def __init__(self, venueName, location, capacity, venueID=None):
        self.venueName = venueName
        self.location = location
        self.capacity = capacity
        self.venueID = venueID
    def checkAvailability(self, date):
        cursor = mydb.cursor()
        cursor.execute("SELECT COUNT(*) FROM games WHERE venue_id = ? AND game_date = ?", (self.venueID, date))
        count = cursor.fetchone()[0]
        cursor.close()
        return count == 0

class Team:
    def __init__(self, teamName, teamID=None):
        self.teamName = teamName
        self.id = teamID
        self.totalPoints = 0
    def addPlayer(self, player):
        if isinstance(player, Player):
            cursor = mydb.cursor()
            cursor.execute("INSERT INTO players (name, jerseyNumber, points, team_id) VALUES (?, ?, ?, ?)",
                           (player.name, player.jerseyNumber, player.points, self.id))
            mydb.commit()
            player.id = cursor.lastrowid
            cursor.close()
            self.calcTotalPoints()
    def calcTotalPoints(self):
        cursor = mydb.cursor()
        cursor.execute("SELECT SUM(points) FROM players WHERE team_id = ?", (self.id,))
        result = cursor.fetchone()
        self.totalPoints = result[0] if result[0] else 0
        cursor.execute("UPDATE teams SET totalPoints = ? WHERE id = ?", (self.totalPoints, self.id))
        mydb.commit()
        cursor.close()

class Player:
    def __init__(self, name, jerseyNumber, playerID=None):
        self.name = name
        self.jerseyNumber = jerseyNumber
        self.points = 0
        self.id = playerID
    def addPoints(self, p):
        self.points += p
        cursor = mydb.cursor()
        cursor.execute("UPDATE players SET points = ? WHERE id = ?", (self.points, self.id))
        mydb.commit()
        cursor.close()

class MVP(Player):
    def __init__(self, name, jerseyNumber, year, playerID):
        super().__init__(name, jerseyNumber, playerID)
        self.year = year
    def addMVP(self, mvp, year):
        if isinstance(mvp, Player):
            cursor = self.mydb.cursor()
            cursor.execute("INSERT INTO mvps (player_id, team_id, year) VALUES (?, ?, ?)", (mvp.name, mvp.jerseyNumber, year))
            self.mydb.commit()
            cursor.close()

class Season:
    def __init__(self, year=None):
        self.year = year
        self.season_definitions = {
            "Pre-season": ((9, 25), (10, 16)),
            "Regular Season": ((10, 17), (4, 16)),  
            "Play-in": ((4, 17), (4, 24)),
            "Playoff": ((4, 25), (6, 8)),
            "Finals": ((6, 9), (6, 24)),
            "Off-season": ((6, 25), (9, 24)),
        }

    def get_team_points_for_season(self, team_id, season_year):
        c = mydb.cursor()
        c.execute("SELECT totalPoints FROM team_season_totals WHERE team_id = ? AND season_year = ?", (team_id, season_year))
        row = c.fetchone()
        c.close()
        return row['totalPoints'] if row else 0

    def set_team_points_for_season(self, team_id, season_year, points):
        c = mydb.cursor()
        c.execute("""INSERT INTO team_season_totals (team_id, season_year, totalPoints)
                    VALUES (?, ?, ?)
                    ON CONFLICT(team_id, season_year) DO UPDATE SET totalPoints=excluded.totalPoints
                """, (team_id, season_year, points))
        mydb.commit()
        c.close()

    def get_range(self, season_name, start_year):
        if season_name not in self.season_definitions:
            return None, None
        (sm, sd), (em, ed) = self.season_definitions[season_name]
        start = datetime(start_year, sm, sd).date()
        if (em, ed) < (sm, sd):
            end = datetime(start_year + 1, em, ed).date()
        else:
            end = datetime(start_year, em, ed).date()
        return start, end

    def get_current_season_year(self, game_date_str):
        try:
            dt = datetime.strptime(game_date_str, "%Y-%m-%d").date()
        except:
            return 2024 
        if dt.month >= 9:
            return dt.year
        else:
            return dt.year - 1