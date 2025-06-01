"""Transfermarkt Transfer Data"""

import pandas as pd
from pathlib import Path
from scraper import Scraper


# Output directory where all scraped and cleaned data will be written.
DATA_DIR = Path("./data")
# Enable to print progress statements.
VERBOSE = True


tm = Scraper()
for season in range(2024, 2024 + 1):
    urls = [tm.create_url(season, window) for window in ('s', 'w')]
    data = pd.concat([tm.scrape(url, verbose=VERBOSE) for url in urls])
    data = tm.clean(data, verbose=VERBOSE)
    filename = f"{season}.csv"
    tm.save(data, filename=filename, destination=DATA_DIR, verbose=VERBOSE)
