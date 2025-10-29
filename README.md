# Transfermarkt transfer data

This repository hosts football (soccer) league transfer data that was web scraped from [Transfermarkt](https://www.transfermarkt.com/).

If you'd like to use this data, simply clone the repository or download whatever you're interested in.
(Cloning ensures you can always pull the latest changes and uploads).

## Leagues

I have scraped data for the following leagues so far.
All league data span the 1992&ndash;93 season through the current season unless otherwise noted.

- Premier League (England)
- La Liga (Spain)
- Bundesliga (Germany)
- Serie A (Italy)

More leagues and seasons are to come!

## Data

The data are grouped by league and saved in CSVs by season.
For example, `premier_league/2025.csv` is all player transfers for the 2025&ndash;26 Premier League season.

Each CSV is formatted like so:

| season 	| league         	| club       	| window 	| movement 	| player_name        	| player_id 	| age 	| nationality 	| position           	| pos 	| market_value 	| dealing_club   	| dealing_country 	| fee      	| is_loan 	|
|--------	|----------------	|------------	|--------	|----------	|--------------------	|-----------	|-----	|-------------	|--------------------	|-----	|--------------	|----------------	|-----------------	|----------	|---------	|
| 2025   	| Premier League 	| Arsenal FC 	| summer 	| in       	| Martín Zubimendi   	| 423440    	| 26  	| Spain       	| Defensive Midfield 	| DM  	| 60000000     	| Real Sociedad  	| Spain           	| 70000000 	| 0       	|
| 2025   	| Premier League 	| Arsenal FC 	| summer 	| in       	| Eberechi Eze       	| 479999    	| 27  	| England     	| Attacking Midfield 	| AM  	| 55000000     	| Crystal Palace 	| England         	| 69300000 	| 0       	|
| 2025   	| Premier League 	| Arsenal FC 	| summer 	| in       	| Viktor Gyökeres    	| 325443    	| 27  	| Sweden      	| Centre-Forward     	| CF  	| 75000000     	| Sporting CP    	| Portugal        	| 65800000 	| 0       	|
| 2025   	| Premier League 	| Arsenal FC 	| summer 	| in       	| Noni Madueke       	| 503987    	| 23  	| England     	| Right Winger       	| RW  	| 40000000     	| Chelsea FC     	| England         	| 56000000 	| 0       	|
| 2025   	| Premier League 	| Arsenal FC 	| summer 	| in       	| Cristhian Mosquera 	| 646750    	| 21  	| Spain       	| Centre-Back        	| CB  	| 30000000     	| Valencia CF    	| Spain           	| 15000000 	| 0       	|

Each row is a player transfer record.
Note that records are not necessarily "unique," as a player can appear twice in one table if he transferred from one club to another in the same league.

Empty fields denote missing values.

Column types and descriptions are as follows:

| Name              	| Type  	| Description                                                                 	|
|-------------------	|-------	|-----------------------------------------------------------------------------	|
| `season`          	| int   	| The year in which the league season begins                                  	|
| `league`          	| str   	| The league in which this transfer occurs                                    	|
| `club`            	| str   	| The club making this transfer                                               	|
| `window`          	| str   	| If the transfer occurs in the "summer" or "winter" window                   	|
| `movement`        	| str   	| If the player is moving "in" or "out" of `club`                             	|
| `player_name`     	| str   	| The player's name                                                           	|
| `player_id`       	| int   	| The player's unique Transfermarkt ID                                        	|
| `age`             	| int   	| The player's age, in years, at the date of this transfer                    	|
| `nationality`     	| str   	| The player's first nationality according to FIFA eligibility                	|
| `position`        	| str   	| The player's primary position                                               	|
| `pos`             	| str   	| An abbreviated form of `position`                                           	|
| `market_value`    	| float 	| The player's estimated market value, in euros, at the date of this transfer 	|
| `dealing_club`    	| str   	| The club with which `club` negotiated the transfer                          	|
| `dealing_country` 	| str   	| The country of the league in which `dealing_club` competes                  	|
| `fee`             	| float 	| The reported transfer fee, in euros                                         	|
| `is_loan`         	| bool  	| Whether this is a loan transfer                                             	|

## Source

My web-scraping script is [available here](https://github.com/eordo/transfermarkt-scraper).
All credit for the data collection and curation goes to Transfermarkt.
The fault for any discrepancies with the original data and for general inaccuracies is my own.
