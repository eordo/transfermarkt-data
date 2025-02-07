"""Transfermarkt Transfer Data Scraper

This script web scrapes Transfermarkt for club transfers. The transfer data 
are written to CSVs in the `data/` directory. The script currently scrapes 
only the English Premier League for the 2024-25 season.
"""

import random
import re
import httpx
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup


URL_BASE = "https://www.transfermarkt.com"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Firefox/113.0",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/113.0.0.0"
]
DATA_DIR = "./data"


def get_fee_and_loan_status(x):
    """Parse transfer fee and impute player loan status."""
    # Unknown/missing values.
    if x in "-?":
        fee = 0
        is_loan = False
    # Free transfers.
    elif x == "free transfer":
        fee = 0
        is_loan = False
    # Loans with no fee.
    elif x == "loan transfer" or x.startswith("End of loan"):
        fee = 0
        is_loan = True
    # Loans with a fee.
    elif x.startswith("Loan fee"):
        fee = parse_currency(x.split(':')[-1])
        is_loan = True
    # Transfers with a fee.
    else:
        fee = parse_currency(x)
        is_loan = False
    
    return fee, is_loan


def parse_currency(x):
    """Convert a currency string into a numeric value."""
    # '-' denotes a missing value.
    if x == '-':
        return None
    
    # Drop the currency symbol and split the string into the numeric amount 
    # and multiplier.
    tokens = re.findall(r'[0-9.]+|[^0-9.]', x[1:])

    # If there is no multiplier, e.g., the original string was "€1000", then 
    # the only token is the numeric value.
    if len(tokens) == 1:
        value = float(tokens[0])
    else:
        multipliers = {
            "m": 1_000_000,
            "k": 1_000
        }
        amount, power = float(tokens[0]), tokens[1]
        value = amount * multipliers[power]
    
    return value


def random_user_agent():
    """Choose a random user agent for request headers."""
    return random.choice(USER_AGENTS)


# Note that some site directories are in German.
league = "premier-league"
transfers = "transfers"
competition = "wettbewerb"
level = "GB1"

# URL origin.
origin = '/'.join([URL_BASE, league, transfers, competition, level])

# URL query string.
season_id = "saison_id"
windows = "s_w"
loans = "leihe"
internal_movements = "intern"

queries = {
    season_id: "2024",
    windows: "",
    loans: "3",
    internal_movements: "0"
}

# Scrape the summer transfer window and the winter transfer window separately.
soups = []
for window in ['s', 'w']:
    queries[windows] = window
    query_string = '&'.join(f'{k}={v}' for k, v in queries.items())

    # Full URL setup.
    url = origin + "/plus/?" + query_string

    # GET the page. Try another user agent header if the request is denied.
    headers = {"User-Agent": random_user_agent()}
    response = httpx.get(url=url, headers=headers)
    while response.status_code != httpx.codes.ok:
        headers["User-Agent"] = random_user_agent()
        response = httpx.get(url=url, headers=headers)

    # Parse the HTML.
    soup = BeautifulSoup(response.text, "html.parser")
    soups.append(soup)

data = []
for soup, window in zip(soups, ["summer", "winter"]):
    # Club names are h2 headers with the "content-box-headline--logo" class.
    clubs = [
        tag.text.strip()
        for tag in soup.findAll("h2", class_="content-box-headline--logo")
    ]

    # Transfers are listed in tables nested in "responsive-table"-class divs.
    tables = [
        tag.find("table")
        for tag in soup.findAll("div", class_="responsive-table")
    ]

    # Player transfer information is nested differently depending on the cell.
    parse_player_name = lambda x: x.find("span", class_="hide-for-small").text
    parse_text = lambda x: x.text
    parse_from_img = lambda x: x.find("img").get("title")

    parse_col_index = {
        0: parse_player_name,
        1: parse_text,
        2: parse_from_img,
        3: parse_text,
        4: parse_text,
        5: parse_text,
        6: parse_from_img,
        7: parse_from_img,
        8: parse_text
    }

    # Parse the transfer data from the tables.
    dfs_in = []
    dfs_out = []
    for i, table in enumerate(tables):
        col_headers = [th.text for th in table.find_all("th")]
        col_headers.insert(-1, "Country")

        table_data = []
        for row in table.tbody.find_all("tr"):
            tds = row.findAll("td")
            
            # If there are no transfers in this window, the row has one cell.
            if len(tds) == 1: break
            
            # Otherwise, there are nine cells to parse.
            transfer = []
            for j, td in enumerate(tds):
                try:
                    info = parse_col_index[j](td)
                except:
                    info = None
                transfer.append(info)
            table_data.append(transfer)
        
        df = pd.DataFrame(table_data, columns=col_headers)
        # Tables alternate between transfers in and out.
        if i % 2 == 0:
            dfs_in.append(df)
        else:
            dfs_out.append(df)

    # Make column names consistent.
    col_names = {
        "Age": "age",
        "Nat.": "nationality",
        "Position": "position",
        "Pos": "pos",
        "Market value": "market_value",
        "Country": "dealing_country",
        "Fee": "fee"
    }

    # Merge the data.
    for club, df_in, df_out in zip(clubs, dfs_in, dfs_out):
        df_in = df_in.rename(columns={"In": "player", "Left": "dealing_club"})
        df_in = df_in.rename(columns=col_names)
        df_in.insert(loc=0, column="club", value=club)
        df_in.insert(loc=1, column="movement", value="in")
        df_in.insert(loc=2, column="window", value=window)

        df_out = df_out.rename(columns={"Out": "player", "Joined": "dealing_club"})
        df_out = df_out.rename(columns=col_names)
        df_out.insert(loc=0, column="club", value=club)
        df_out.insert(loc=1, column="movement", value="out")
        df_out.insert(loc=2, column="window", value=window)

        df = pd.concat([df_in, df_out])
        data.append(df)

data = pd.concat(data)

# Clean the market values and fees; impute loan status.
data["market_value"] = data.market_value.apply(parse_currency)
data["fee"], data["is_loan"] = zip(*data.fee.map(get_fee_and_loan_status))

# Sort the data alphabetically by club, then transfers in/out, then 
# summer/winter
data = data.sort_values(["club", "movement", "window"])

# Save the data.
output_dir = Path(DATA_DIR)
output_file = "data.csv"
output_dir.mkdir(parents=True, exist_ok=True)
data.to_csv(output_dir / output_file, index=False, encoding="utf-8")
