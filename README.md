# NoSQL-Final-Project
Final project for Master's level NoSQL database systems class. Content will be a reflection of work and progress.

## Contents:
  1. Goals/Intent of Development
  2. Schema
  3. Explanation
  4. How-To Guide

## 1. Goals/Intent of Development
  1. The primary goal is to create a graph database that is a reflection of recent MLB players. The database itself with hold a range of relationships between players and their teams and players and their stats/information.
  2. There are some basic query types that would not necessarily be unique to the graph structure. For example, determining which players play for the Boston Red Sox, would not necessarily be unique to this type of database. In fact, it would be pretty trivial in a SQL database. That said, it would still be interesting to visualize this type of query.
  3. The graph structure would allow for some interesting query types. Consider the following queries:
     **a.** "How are Player A and Player B connected by teammates?"
     **b.** "Which players have shared multiple teams and seasons together?"
     **c.** "Show the ordered path of teams for a player and show other players who have followed the same development."
     **d.** “Which players are linked through a manager tree (player A played under manager X who managed player B at another time)?”

## 2. Schema
  1. Player Schema:
     ```
     Player {
      playerID: string (unique)
      name: string
      bats: string
      throws: string
      debut: date/string
      finalGame: date/string
      birthYear: int
      birthCountry: string
      ...
      }
     ```
     
