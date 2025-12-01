# mlb_app.py
#
# Simple CLI application to query MLB graph database in Neo4j
# This application demonstrates how a graph data model can answer interesting baseball questions
# using traversal heavy Cypher queries

from neo4j import GraphDatabase

# Use your actual DB name
DB_NAME = "mlb"   # <-- keep or change if your database name is different

class MLBApp:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()
    
    # Low-level helper
    def _run_query(self, query: str, **parameters):
        """Run a Cypher query and return the list of resulting records"""
        with self.driver.session(database=DB_NAME) as session:
            result = session.run(query, **parameters)
            return list(result)
        
    # QUERY 1:
    # Players on a given team in a given season
    def players_on_team_in_year(self, team_id: str, year: int):
        """
        List players who played for a given team in a given year

        Uses the following structure in *your* DB:
        (t:Team {teamID})-[:PLAYED_IN_SEASON]->(ts:TeamSeason {year})
        (p:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts)
        """

        query = """
        MATCH (t:Team {teamID: $team_id})-[:PLAYED_IN_SEASON]->(ts:TeamSeason)
        WHERE ts.year = $year
        MATCH (p:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts)
        RETURN DISTINCT p.playerID AS playerID,
               p.name AS name,
               t.name AS team,
               ts.year AS year
        ORDER BY name
        """

        records = self._run_query(query, team_id=team_id, year=year)
        if not records:
            print(f"\nNo players found for team {team_id} in {year}.\n")
            return
        
        print(f"\nPlayers for team {team_id} in {year}:\n")
        for r in records:
            print(f"    {r['name']} ({r['playerID']})")
        print()
    
    # QUERY 2:
    # Team season summary (wins, losses, HR, etc.)
    def team_season_summary(self, team_id: str, year: int):
        """
        Show season summary stats for a team in a given year.

        TeamSeason node has:
        {wins, losses, division, rank, runs, homeRuns, attendance, year}
        """

        query = """
        MATCH (t:Team {teamID: $team_id})-[:PLAYED_IN_SEASON]->(ts:TeamSeason)
        WHERE ts.year = $year
        RETURN t.name          AS team,
               t.teamID        AS teamID,
               ts.year         AS year,
               ts.division     AS division,
               ts.rank         AS rank,
               ts.wins         AS wins,
               ts.losses       AS losses,
               ts.runs         AS runs,
               ts.homeRuns     AS homeRuns,
               ts.attendance   AS attendance
        """

        records = self._run_query(query, team_id=team_id, year=year)
        if not records:
            print(f"\nNo season summary found for team {team_id} in {year}.\n")
            return

        r = records[0]
        print(f"\nSeason summary for {r['team']} ({r['teamID']}) in {r['year']}:")
        print(f"  Division:   {r['division']}")
        print(f"  Rank:       {r['rank']}")
        print(f"  Wins:       {r['wins']}")
        print(f"  Losses:     {r['losses']}")
        print(f"  Runs:       {r['runs']}")
        print(f"  Home Runs:  {r['homeRuns']}")
        print(f"  Attendance: {r['attendance']}")
        print()

    # QUERY 3:
    # Players who have played for multiple teams (database includes data from 2020-2024)
    def multi_team_players(self, start_year: int = 2020, end_year: int = 2024, min_team_seasons: int = 2):
        """
        Find the players who appeared for multiple TeamSeasons in the given year range.

        Graph pattern in your DB:
        (p:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason {year})
        """

        query = """
        MATCH (p:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason)
        WHERE ts.year >= $start_year AND ts.year <= $end_year
        WITH p, collect(DISTINCT ts) AS teamSeasons
        WHERE size(teamSeasons) >= $min_team_seasons
        RETURN p.name AS player,
               p.playerID AS playerID,
               size(teamSeasons) AS numTeamSeasons
        ORDER BY numTeamSeasons DESC, player
        LIMIT 50
        """

        records = self._run_query(
            query,
            start_year=start_year,
            end_year=end_year,
            min_team_seasons=min_team_seasons
        )

        if not records:
            print(f"\nNo players found with at least {min_team_seasons} team-seasons between {start_year}-{end_year}.\n")
            return

        print(f"\nPlayers with ≥ {min_team_seasons} team-seasons between {start_year}-{end_year}:\n")
        for r in records:
            print(f"  {r['player']} ({r['playerID']}) — {r['numTeamSeasons']} team-seasons")
        print()

    # QUERY 4:
    # Managers and the parks they managed in for a given team & year
    def managers_and_parks_for_team_year(self, team_id: str, year: int):
        """
        Shows managers and home parks for a team in a specific season.

        Uses your structure:
        (t:Team)-[:PLAYED_IN_SEASON]->(ts:TeamSeason {year})
        (m:Manager)-[:MANAGED]->(ts)
        (ts)-[:PLAYED_HOME_GAMES_AT]->(pk:Park)
        """

        query = """
        MATCH (t:Team {teamID: $team_id})-[:PLAYED_IN_SEASON]->(ts:TeamSeason)
        WHERE ts.year = $year
        OPTIONAL MATCH (m:Manager)-[:MANAGED]->(ts)
        OPTIONAL MATCH (ts)-[:PLAYED_HOME_GAMES_AT]->(pk:Park)
        RETURN t.name AS team,
               ts.year AS year,
               collect(DISTINCT coalesce(m.name, m.managerID)) AS managers,
               collect(DISTINCT pk.name) AS parks
        """

        records = self._run_query(query, team_id=team_id, year=year)
        if not records:
            print(f"\nNo data found for team {team_id} in {year}.\n")
            return
        
        r = records[0]
        print(f"\nManagers and parks for {r['team']} in {r['year']}:\n")

        managers = [m for m in r["managers"] if m is not None]
        parks = [p for p in r["parks"] if p is not None]

        print("  Managers:")
        if managers:
            for m in managers:
                print(f"    - {m}")
        else:
            print("    (none recorded)")

        print("\n  Home Parks:")
        if parks:
            for p in parks:
                print(f"    - {p}")
        else:
            print("    (none recorded)")
        print()

    # QUERY 5:
    # Shortest teammate path between two players (2020-2024)
    # (How are Player A and Player B connected by teammates?)
    def shortest_teammate_path(self, player_id_1: str, player_id_2: str):
        """
        Find the shortest "teammate" path between two players.

        Your DB already has TEAMMATE_WITH relationships between players:
        (p1:Player)-[:TEAMMATE_WITH]-(p2:Player)
        """

        query = """
        MATCH (p1:Player {playerID: $p1}), (p2:Player {playerID: $p2})
        MATCH path = shortestPath(
            (p1)-[:TEAMMATE_WITH*..6]-(p2)
        )
        RETURN path
        """

        records = self._run_query(query, p1=player_id_1, p2=player_id_2)
        if not records:
            print(f"\nNo path found between {player_id_1} and {player_id_2}.\n")
            return

        path = records[0]["path"]
        nodes = list(path.nodes)
        rels = list(path.relationships)

        print(f"\nShortest teammate path between {player_id_1} and {player_id_2}:\n")
        for i, node in enumerate(nodes):
            label_list = list(node.labels)
            label_str = ",".join(label_list)
            name = node.get("name", node.get("playerID", node.get("teamID", "(no name)")))
            print(f"  Node {i}: {label_str} — {name}")

            if i < len(rels):
                print("    |")
                print(f"    +--[{rels[i].type}]-->")
        print()

    # QUERY 6:
    # Which players have shared multiple teams and seasons together?
    def players_with_shared_team_seasons(self, start_year: int = 2020, end_year: int = 2024, min_shared: int = 2):
        """
        Find pairs of players who have shared multiple TeamSeasons together.

        Graph pattern:
        (p1:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason)<-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]-(p2:Player)
        """

        query = """
        MATCH (p1:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason)
              <-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]-(p2:Player)
        WHERE ts.year >= $start_year AND ts.year <= $end_year
          AND p1.playerID < p2.playerID
        WITH p1, p2, collect(DISTINCT ts) AS shared_ts
        WHERE size(shared_ts) >= $min_shared
        RETURN p1.name AS player1,
               p1.playerID AS playerID1,
               p2.name AS player2,
               p2.playerID AS playerID2,
               size(shared_ts) AS numSharedSeasons,
               [ts IN shared_ts | ts.teamID + ' ' + toString(ts.year)] AS sharedTeamSeasons
        ORDER BY numSharedSeasons DESC, player1, player2
        LIMIT 50
        """

        records = self._run_query(
            query,
            start_year=start_year,
            end_year=end_year,
            min_shared=min_shared
        )

        if not records:
            print(f"\nNo player pairs found with at least {min_shared} shared team-seasons between {start_year}-{end_year}.\n")
            return

        print(f"\nPlayer pairs with ≥ {min_shared} shared team-seasons between {start_year}-{end_year}:\n")
        for r in records:
            shared_desc = ", ".join(r["sharedTeamSeasons"])
            print(f"  {r['player1']} ({r['playerID1']})  &  {r['player2']} ({r['playerID2']})")
            print(f"    - Shared seasons: {r['numSharedSeasons']} [{shared_desc}]")
        print()

    # QUERY 7:
    # Show the ordered path of teams for a player, and other players who followed the same path.
    def player_team_path_and_followers(self, player_id: str, start_year: int = 2020, end_year: int = 2024):
        """
        For a given player, show the ordered sequence of teams they played for,
        and list other players who followed the exact same path over the year range.

        Uses:
        (p:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason)
        """

        query = """
        // Get the target player's ordered team sequence
        MATCH (p:Player {playerID: $player_id})-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts:TeamSeason)
        WHERE ts.year >= $start_year AND ts.year <= $end_year
        WITH p, ts
        ORDER BY ts.year, ts.teamID
        WITH p, collect(DISTINCT ts) AS ts_list
        WITH p,
             [ts IN ts_list | ts.teamID] AS team_seq,
             [ts IN ts_list | ts.year]   AS year_seq

        // Get other players' ordered team sequences over the same window
        MATCH (other:Player)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ots:TeamSeason)
        WHERE other <> p AND ots.year >= $start_year AND ots.year <= $end_year
        WITH p, team_seq, year_seq, other, ots
        ORDER BY other.playerID, ots.year, ots.teamID
        WITH p, team_seq, year_seq, other, collect(DISTINCT ots) AS other_ts_list
        WITH p, team_seq, year_seq, other,
             [ts IN other_ts_list | ts.teamID] AS other_team_seq
        WHERE other_team_seq = team_seq
        RETURN p.name AS player,
               p.playerID AS playerID,
               team_seq AS teamSequence,
               year_seq AS yearSequence,
               collect(DISTINCT {name: other.name, playerID: other.playerID}) AS followers
        """

        records = self._run_query(
            query,
            player_id=player_id,
            start_year=start_year,
            end_year=end_year
        )

        if not records:
            print(f"\nNo matching team path found for player {player_id} between {start_year}-{end_year}.\n")
            return

        r = records[0]
        team_seq = r["teamSequence"]
        year_seq = r["yearSequence"]
        followers = r["followers"]

        if not team_seq:
            print(f"\nPlayer {player_id} has no team history between {start_year}-{end_year}.\n")
            return

        print(f"\nOrdered team path for {r['player']} ({r['playerID']}) between {start_year}-{end_year}:\n")
        steps = []
        for team, year in zip(team_seq, year_seq):
            steps.append(f"{year}:{team}")
        print("  Path: " + "  ->  ".join(steps))

        print("\nPlayers who followed the same development path:")
        if followers:
            for f in followers:
                print(f"  - {f['name']} ({f['playerID']})")
        else:
            print("  (no other players with the exact same path)")
        print()

    # QUERY 8:
    # Manager tree: which players are linked through a manager?
    # (Player A played under manager X who also managed Player B at another time)
    def manager_tree_connection(self, player_id_1: str, player_id_2: str):
        """
        Show manager-based links between two players:
        Player A played for TeamSeason T1 managed by M,
        and M also managed TeamSeason T2 where Player B played.

        Pattern:
        (p1)-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts1)<-[:MANAGED]-(m)-[:MANAGED]->(ts2)<-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]-(p2)
        """

        query = """
        MATCH (p1:Player {playerID: $p1})-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]->(ts1:TeamSeason)
              <-[:MANAGED]-(m:Manager)-[:MANAGED]->(ts2:TeamSeason)
              <-[:BATTED_FOR|PITCHED_FOR|FIELDED_FOR]-(p2:Player {playerID: $p2})
        WHERE ts1 <> ts2
        RETURN DISTINCT
               p1.name AS player1,
               p1.playerID AS playerID1,
               p2.name AS player2,
               p2.playerID AS playerID2,
               coalesce(m.name, m.managerID) AS manager,
               ts1.teamID AS team1, ts1.year AS year1,
               ts2.teamID AS team2, ts2.year AS year2
        ORDER BY manager, year1, year2
        """

        records = self._run_query(query, p1=player_id_1, p2=player_id_2)
        if not records:
            print(f"\nNo manager-tree connection found between {player_id_1} and {player_id_2}.\n")
            return

        print(f"\nManager tree connections between {player_id_1} and {player_id_2}:\n")
        for r in records:
            print(f"  Manager: {r['manager']}")
            print(f"    - {r['player1']} ({r['playerID1']}) with {r['team1']} in {r['year1']}")
            print(f"    - {r['player2']} ({r['playerID2']}) with {r['team2']} in {r['year2']}")
            print()
        print()

    # CLI tool
    def run(self):
        """
        Simple command line menu to demonstrate queries.
        """

        while True:
            print("-=-=-=-=-= MLB Graph Demo =-=-=-=-=-")
            print("1. List players on a team for a given year")
            print("2. Show team season summary")
            print("3. Find players who played for multiple teams (2020–2024)")
            print("4. Show managers and parks for a team & year")
            print("5. How are two players connected by teammates? (shortest teammate path)")
            print("6. Which player pairs shared multiple teams and seasons?")
            print("7. Show a player's ordered team path and others with the same path")
            print("8. Show manager-tree connections between two players")
            print("q. Quit")
            choice = input("Select an option: ").strip().lower()

            if choice == "1":
                team_id = input("Enter teamID (e.g. 'BOS'): ").strip().upper()
                year = int(input("Enter year (e.g. 2023): ").strip())
                self.players_on_team_in_year(team_id, year)
            elif choice == "2":
                team_id = input("Enter teamID (e.g. 'BOS'): ").strip().upper()
                year = int(input("Enter year (e.g. 2023): ").strip())
                self.team_season_summary(team_id, year)
            elif choice == "3":
                start = 2020
                end = 2024
                min_ts = int(input("Minimum number of team-seasons (default 2): ") or "2")
                self.multi_team_players(start_year=start, end_year=end, min_team_seasons=min_ts)
            elif choice == "4":
                team_id = input("Enter teamID (e.g. 'BOS'): ").strip().upper()
                year = int(input("Enter year (e.g. 2023): ").strip())
                self.managers_and_parks_for_team_year(team_id, year)
            elif choice == "5":
                p1 = input("Enter first playerID: ").strip()
                p2 = input("Enter second playerID: ").strip()
                self.shortest_teammate_path(p1, p2)
            elif choice == "6":
                start = 2020
                end = 2024
                min_shared = int(input("Minimum shared team-seasons (default 2): ") or "2")
                self.players_with_shared_team_seasons(start_year=start, end_year=end, min_shared=min_shared)
            elif choice == "7":
                pid = input("Enter playerID: ").strip()
                # Keeping 2020–2024 window consistent with the dataset you built
                self.player_team_path_and_followers(pid, start_year=2020, end_year=2024)
            elif choice == "8":
                p1 = input("Enter first playerID: ").strip()
                p2 = input("Enter second playerID: ").strip()
                self.manager_tree_connection(p1, p2)
            elif choice == "q":
                print("Goodbye!")
                break
            else:
                print("Invalid option. Please try again.\n")

if __name__ == "__main__":
    # CHANGE THESE TO MATCH YOUR PERSONAL ENVIRONMENT
    URI = "neo4j://127.0.0.1:7687"
    USER = "neo4j"
    PASSWORD = "password"   # <-- your real password here

    app = MLBApp(URI, USER, PASSWORD)
    try:
        app.run()
    finally:
        app.close()




