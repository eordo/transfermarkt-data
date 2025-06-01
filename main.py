"""
Web scraping Transfermarkt transfer data

This script web scrapes Transfermarkt for player transfers in the 2024-25 
English Premier League season. It cleans the parsed transfers to a tidy format 
described in the docs, then it saves the cleaned data to a CSV.
"""

import pandas as pd
from pathlib import Path
from scraper import Scraper


# Output directory where all scraped and cleaned data will be written.
DATA_DIR = Path("./data")
# Enable to print progress statements.
VERBOSE = True


tm = Scraper()

season = 2024
dfs = []
for window in ('s', 'w'):
    url = tm.create_url(season, window)
    df = tm.scrape(url, verbose=VERBOSE)
    dfs.append(df)
data = pd.concat(dfs)
data = tm.clean(data, verbose=VERBOSE)

filename = f"{season}.csv"
tm.save(data, filename=filename, destination=DATA_DIR, verbose=VERBOSE)
