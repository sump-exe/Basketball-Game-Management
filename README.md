<h1>Basketball Game Scheduler System</h1>

<h3>About</h3>
<blockquote>
A basketball game management system, covers pre-season up to finals and off-season.
</blockquote>

<h2>Program Description</h2>
<p>
This application is a complete management solution for basketball leagues. It handles everything from roster management and venue tracking to complex game scheduling with conflict detection. It features a live point system for tracking game scores in real-time and automatically calculates league standings and tracks MVP awards based on game results.
</p>

<h2>User Manual</h2>

<h3>1. Teams & Players Tab</h3>
<ul>
<li><b>Manage Roster:</b> Add new teams using the sidebar button. Click on a team to view their player list.</li>
<li><b>Add Players:</b> Select a team, then use the bottom input fields to add a player (Name & Jersey Number).</li>
<li><b>History:</b> Click "View Games" to see a complete history of matches for the selected team.</li>
<li><b>Deletion:</b> Deleting a team also removes their associated players and offers to remove their scheduled games.</li>
</ul>

<h3>2. Venues Tab</h3>
<ul>
<li><b>Manage Venues:</b> Add venues with specific capacities and locations.</li>
<li><b>Details:</b> Click on a venue to see all upcoming and past games scheduled at that location.</li>
<li><b>Safety:</b> The system prevents deleting venues that currently have active games scheduled.</li>
</ul>

<h3>3. Schedule Game Tab</h3>
<ul>
<li><b>Scheduling Logic:</b> Select a Season and Year first. The system validates dates against standard season windows (e.g., Regular Season, Playoffs).</li>
<li><b>Conflict Detection:</b> The system automatically blocks scheduling if:
<ul>
<li>A venue is already booked for that time.</li>
<li>A team is already playing at that time.</li>
<li>A team is trying to play in two different venues on the same day.</li>
</ul>
</li>
<li><b>Smart Dropdowns:</b> In "Playoff" mode, only qualified teams appear in the selection lists.</li>
</ul>

<h3>4. View Games Tab</h3>
<ul>
<li><b>Game List:</b> Displays all scheduled games grouped by season.</li>
<li><b>Actions:</b> You can delete scheduled games here.</li>
<li><b>Point System:</b> Select a game and click <b>"Open Point System"</b> to launch the scoring interface. Here you can add points to specific players and mark the game as <b>"Final"</b> to update the league standings.</li>
</ul>

<h3>5. Standings Tab</h3>
<ul>
<li><b>Leaderboard:</b> Automatically ranks teams by Wins, then by Total Points.</li>
<li><b>MVP:</b> Use the control panel on the right to assign an MVP for a specific season. The MVP is displayed in the season header.</li>
</ul>
