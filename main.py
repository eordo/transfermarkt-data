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
# Output directory where all scraped and cleaned data will be written.
DATA_DIR = Path("./data")
# Enable to print progress statements.
VERBOSE = True


def scrape_transfer_window(url, verbose=False):
    """Scrape all transfers in the given URL."""
    # GET the page. Try another user agent header if the request is denied.
    headers = {"User-Agent": random_user_agent()}
    response = httpx.get(url=url, headers=headers, timeout=10.0)
    while response.status_code != httpx.codes.ok:
        headers["User-Agent"] = random_user_agent()
        response = httpx.get(url=url, headers=headers, timeout=10.0)
    if verbose:
        print(f"Status code {response.status_code}.")

    # Parse the HTML.
    soup = BeautifulSoup(response.text, "html.parser")
    if verbose:
        print("Soup parsed successfully.")

    return soup


def soup_to_df(soup, window, verbose=False):
    """Create a data frame from the soup of a scraped transfer window."""
    # Club names are h2 headers with the "content-box-headline--logo" class.
    clubs = [
        tag.text.strip()
        for tag in soup.find_all("h2", class_="content-box-headline--logo")
    ]

    # Transfers are listed in tables nested in "responsive-table"-class divs.
    tables = [
        tag.find("table")
        for tag in soup.find_all("div", class_="responsive-table")
    ]

    # Player transfer information is nested differently depending on the cell.
    def parse_player_name_and_id(x):
        player_span = x.find("span", class_="hide-for-small")
        player_name = player_span.a.text
        player_id = player_span.a['href'].split('/')[-1]
        return player_name, player_id
    
    def parse_text(x):
        return x.text
    
    def parse_from_img(x):
        return x.find("img").get("title")

    parse_col_index = {
        0: parse_player_name_and_id,
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
            tds = row.find_all("td")
            
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
        "In": "player",
        "Out": "player",
        "Age": "age",
        "Nat.": "nationality",
        "Position": "position",
        "Pos": "pos",
        "Market value": "market_value",
        "Left": "dealing_club",
        "Joined": "dealing_club",
        "Country": "dealing_country",
        "Fee": "fee"
    }

    # Merge the data.
    dfs = []
    for club, df_in, df_out in zip(clubs, dfs_in, dfs_out):
        df_in = df_in.rename(columns=col_names)
        df_in.insert(loc=0, column="club", value=club)
        df_in.insert(loc=1, column="movement", value="in")
        df_in.insert(loc=2, column="window", value=window)

        df_out = df_out.rename(columns=col_names)
        df_out.insert(loc=0, column="club", value=club)
        df_out.insert(loc=1, column="movement", value="out")
        df_out.insert(loc=2, column="window", value=window)

        df = pd.concat([df_in, df_out])
        dfs.append(df)
    
    if verbose:
        print(f"Done with {window} window.")

    return pd.concat(dfs)


def clean(df, verbose=False):
    """Clean a data frame of club transfers."""
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

        # If there is no multiplier, e.g., the original string was "€1000",
        # then the only token is the numeric value.
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

    # Separate player names and IDs.
    player_name, player_id = zip(*df.player)
    df["player"] = player_name
    df = df.rename(columns={"player": "player_name"})
    df.insert(loc=4, column="player_id", value=player_id)

    # Clean the market values and fees; impute loan status.
    df["market_value"] = df.market_value.apply(parse_currency)
    df["fee"], df["is_loan"] = zip(*df.fee.map(get_fee_and_loan_status))

    # Convert ID and age from strings to ints.
    for col in ("player_id", "age"):
        df[col] = df[col].astype(int)

    # Sort the data alphabetically by club, then transfers in/out, then 
    # summer/winter window.
    df.sort_values(["club", "movement", "window"], inplace=True)

    if verbose:
        print("Cleaned data.")

    return df


def save(df, filename, destination=DATA_DIR, verbose=False):
    """Save the data as a CSV in the destination directory."""
    output_dir = Path(destination)
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / filename, index=False, encoding="utf-8")
    if verbose:
        print(f"Saved {output_dir / filename}.")


def random_user_agent():
    """Choose a random user agent for request headers."""
    return random.choice(USER_AGENTS)


if __name__ == "__main__":
    # URL setup. Note that site directories and parameters are in German.
    # URL origin.
    league = "premier-league"
    transfers = "transfers"
    competition = "wettbewerb"
    level = "GB1"

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

    # Scrape the summer and winter transfer windows separately.
    urls = []
    for window in ('s', 'w'):
        queries[windows] = window
        query_string = '&'.join(f'{k}={v}' for k, v in queries.items())
        url = origin + "/plus/?" + query_string
        urls.append(url)

    # Read, parse, clean, and save the data.
    soups = [scrape_transfer_window(url, verbose=VERBOSE) for url in urls]
    data = pd.concat([
        soup_to_df(soup, window, verbose=VERBOSE)
        for soup, window in zip(soups, ("summer", "winter"))
    ])
    data = clean(data, verbose=VERBOSE)
    save(data, "transfers.csv", destination=DATA_DIR, verbose=VERBOSE)
