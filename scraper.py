"""Transfermarkt Transfer Scraper"""

import random
import re
import httpx
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup


class Scraper:
    _URL_BASE = "https://www.transfermarkt.com"
    _USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Firefox/113.0",
        "Mozilla/5.0 (X11; Linux x86_64) Chrome/113.0.0.0"
    ]
    _QUERY_SEASON_ID = "saison_id"
    _QUERY_WINDOWS = "s_w"
    _QUERY_LOANS = "leihe"
    _QUERY_INTERNAL_MOVEMENTS = "intern"

    def __init__(self, league="premier-league", level="GB1"):
        self.origin = '/'.join([
            self._URL_BASE,
            league,
            "transfers",
            "wettbewerb",
            level
        ])
        self.queries = {
            self._QUERY_SEASON_ID: 2024,
            self._QUERY_WINDOWS: 's',
            self._QUERY_LOANS: 3,
            self._QUERY_INTERNAL_MOVEMENTS: 0
        }

    def create_url(self, season, window):
        self.queries[self._QUERY_SEASON_ID] = season
        self.queries[self._QUERY_WINDOWS] = window
        query_string = '&'.join(f'{k}={v}' for k, v in self.queries.items())
        url = self.origin + "/plus/?" + query_string
        return url

    def scrape(self, url, verbose=False):
        """Scrape a Transfermarkt URL and return a data frame."""
        def _is_winter(url):
            """Return whether the URL is for a winter transfer window."""
            window_query = "s_w="
            window = url[url.find(window_query) + len(window_query)]
            return window == 'w'
            
        soup = self._scrape_transfer_window(url, verbose=verbose)
        is_winter = _is_winter(url)
        df = self._soup_to_df(soup, is_winter=is_winter, verbose=verbose)
        return df

    def clean(self, df, verbose=False):
        """Clean a data frame of club transfers."""
        def _get_fee_and_loan_status(x):
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
                fee = _parse_currency(x.split(':')[-1])
                is_loan = True
            # Transfers with a fee.
            else:
                fee = _parse_currency(x)
                is_loan = False
            
            return fee, is_loan

        def _parse_currency(x):
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
        df["market_value"] = df.market_value.apply(_parse_currency)
        df["fee"], df["is_loan"] = zip(*df.fee.map(_get_fee_and_loan_status))

        # Convert ID and age from strings to ints.
        for col in ("player_id", "age"):
            df[col] = df[col].astype(int)
        # Convert bools to ints.
        for col in df.select_dtypes(include='bool').columns:
            df[col] = df[col].astype(int)

        # Sort the data alphabetically by club, then transfers in/out, then 
        # summer/winter window.
        df.sort_values([
            "club",
            "is_transfer_out",
            "is_winter_window"
        ], inplace=True)

        if verbose:
            print("Cleaned data.")

        return df

    def save(self, df, filename, destination=".", verbose=False):
        """Save the data as a CSV in the destination directory."""
        output_dir = Path(destination)
        output_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_dir / filename, index=False, encoding="utf-8")
        if verbose:
            print(f"Saved {output_dir / filename}.")

    def _scrape_transfer_window(self, url, verbose=False):
        """Scrape all transfers in the given URL."""
        # GET the page. Try another user agent header if the request is denied.
        headers = {"User-Agent": self._random_user_agent()}
        response = httpx.get(url=url, headers=headers, timeout=30.0)
        while response.status_code != httpx.codes.ok:
            headers["User-Agent"] = self._random_user_agent()
            response = httpx.get(url=url, headers=headers, timeout=30.0)
        if verbose:
            print(f"Status code {response.status_code}.")

        # Parse the HTML.
        soup = BeautifulSoup(response.text, "html.parser")
        if verbose:
            print("Soup parsed successfully.")

        return soup

    def _soup_to_df(self, soup, is_winter=False, verbose=False):
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
        def _parse_player_name_and_id(x):
            player_span = x.find("span", class_="hide-for-small")
            player_name = player_span.a.text
            player_id = player_span.a['href'].split('/')[-1]
            return player_name, player_id
        
        def _parse_text(x):
            return x.text
        
        def _parse_from_img(x):
            return x.find("img").get("title")

        parse_col_index = {
            0: _parse_player_name_and_id,
            1: _parse_text,
            2: _parse_from_img,
            3: _parse_text,
            4: _parse_text,
            5: _parse_text,
            6: _parse_from_img,
            7: _parse_from_img,
            8: _parse_text
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
            df_in.rename(columns=col_names, inplace=True)
            df_in.insert(loc=0, column="club", value=club)
            df_in.insert(loc=1, column="is_transfer_out", value=False)
            df_in.insert(loc=2, column="is_winter_window", value=is_winter)
            dfs.append(df_in)

            df_out.rename(columns=col_names, inplace=True)
            df_out.insert(loc=0, column="club", value=club)
            df_out.insert(loc=1, column="is_transfer_out", value=True)
            df_out.insert(loc=2, column="is_winter_window", value=is_winter)
            dfs.append(df_out)

        if verbose:
            current_window = "winter window" if is_winter else "summer window"
            print(f"Done with {current_window}.")

        return pd.concat(dfs)

    def _random_user_agent(self):
        """Choose a random user agent for request headers."""
        return random.choice(self._USER_AGENTS)
