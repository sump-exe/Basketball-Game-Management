import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).with_name('sports_schedule.db')

mydb = sqlite3.connect(str(DB_FILE))
mydb.row_factory = sqlite3.Row
cur = mydb.cursor()
cur.execute("PRAGMA foreign_keys = ON")

cur.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teamName TEXT NOT NULL UNIQUE,
    totalPoints INTEGER DEFAULT 0
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
    if has_home:
        select_parts.append("home_team_id AS team1_id")
    else:
        select_parts.append("NULL AS team1_id")
    if has_away:
        select_parts.append("away_team_id AS team2_id")
    else:
        select_parts.append("NULL AS team2_id")
    select_parts.append("venue_id")
    select_parts.append("game_date")
    if has_home_score:
        select_parts.append("home_score AS team1_score")
    else:
        select_parts.append("0 AS team1_score")
    if has_away_score:
        select_parts.append("away_score AS team2_score")
    else:
        select_parts.append("0 AS team2_score")
    if has_start:
        select_parts.append("start_time")
    else:
        select_parts.append("'00:00' AS start_time")
    if has_end:
        select_parts.append("end_time")
    else:
        select_parts.append("'00:00' AS end_time")
    if has_is_final:
        select_parts.append("is_final")
    else:
        select_parts.append("0 AS is_final")
    if has_winner:
        select_parts.append("winner_team_id")
    else:
        select_parts.append("NULL AS winner_team_id")

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

    def displaySchedule(self):
        cursor = self.mydb.cursor()
        cursor.execute("""
        SELECT g.id, t1.teamName AS team1, t2.teamName AS team2, v.venueName, g.game_date, g.team1_score, g.team2_score
        FROM games g
        LEFT JOIN teams t1 ON g.team1_id = t1.id
        LEFT JOIN teams t2 ON g.team2_id = t2.id
        LEFT JOIN venues v ON g.venue_id = v.id
        ORDER BY g.game_date
        """)
        results = cursor.fetchall()
        cursor.close()
        print("Schedule:")
        for row in results:
            print(f"Game ID: {row[0]}, {row[1]} vs {row[2]} at {row[3]} on {row[4]}, Score: {row[5]}-{row[6]}")

    def displayStandings(self):
        cursor = self.mydb.cursor()
        cursor.execute("""
        SELECT t.teamName,
               COALESCE(t.totalPoints, 0) AS totalPoints,
               COALESCE((SELECT COUNT(*) FROM games g WHERE g.is_final = 1 AND g.winner_team_id = t.id), 0) AS wins,
               COALESCE((SELECT COUNT(*) FROM games g
                         WHERE g.is_final = 1
                           AND (g.team1_id = t.id OR g.team2_id = t.id)
                           AND (g.winner_team_id IS NOT NULL AND g.winner_team_id != t.id)
                        ), 0) AS losses
        FROM teams t
        LEFT JOIN games g2 ON (g2.team1_id = t.id OR g2.team2_id = t.id)
        GROUP BY t.id, t.teamName, t.totalPoints
        ORDER BY wins DESC, totalPoints DESC
        """)
        results = cursor.fetchall()
        cursor.close()
        print("Standings:")
        for row in results:
            print(f"Team: {row[0]}, Wins: {row[2]}, Losses: {row[3]}, Total Points: {row[1]}")

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
        cursor.execute("SELECT team1_id, team2_id FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            raise ValueError("Game not found")

        t1_id = row['team1_id']
        t2_id = row['team2_id']

        cursor.execute("SELECT SUM(points) as s FROM players WHERE team_id = ?", (t1_id,))
        hrow = cursor.fetchone()
        t1_sum = hrow['s'] if hrow and hrow['s'] is not None else 0

        cursor.execute("SELECT SUM(points) as s FROM players WHERE team_id = ?", (t2_id,))
        arow = cursor.fetchone()
        t2_sum = arow['s'] if arow and arow['s'] is not None else 0

        winner = None
        if t1_sum > t2_sum:
            winner = t1_id
        elif t2_sum > t1_sum:
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
    def getRoster(self):
        cursor = mydb.cursor()
        cursor.execute("SELECT name, jerseyNumber, points FROM players WHERE team_id = ?", (self.id,))
        results = cursor.fetchall()
        cursor.close()
        roster = []
        for row in results:
            roster.append({'name': row[0], 'jerseyNumber': row[1], 'points': row[2]})
        return roster
    def getRecord(self):
        cursor = mydb.cursor()
        cursor.execute("""
        SELECT 
            SUM(CASE WHEN team1_id = ? AND team1_score > team2_score THEN 1
                     WHEN team2_id = ? AND team2_score > team1_score THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN team1_id = ? AND team1_score < team2_score THEN 1
                     WHEN team2_id = ? AND team2_score < team1_score THEN 1 ELSE 0 END) AS losses
        FROM games
        WHERE team1_id = ? OR team2_id = ?
        """, (self.id, self.id, self.id, self.id, self.id, self.id))
        result = cursor.fetchone()
        cursor.close()
        wins = result[0] if result[0] else 0
        losses = result[1] if result[1] else 0
        return {'wins': wins, 'losses': losses}

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
        else:
            pass
