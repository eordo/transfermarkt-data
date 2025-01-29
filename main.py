"""Transfermarkt Transfer Data Scraper

This script web scrapes Transfermarkt for club transfers. The script currently 
scrapes only the English Premier League for the 2024-25 season.
"""

import httpx
import pandas as pd
from bs4 import BeautifulSoup


# URL setup. Note that some site directories are in German.
base = "https://www.transfermarkt.com/"
league = "premier-league"
transfers = "transfers"
competition = "wettbewerb"
level = "GB1"

url = base + f'{league}/{transfers}/{competition}/{level}'

# GET and parse the HTML.
response = httpx.get(url=url)
html = response.text
soup = BeautifulSoup(html, "html.parser")

# Club names are h2 headers with the "content-box-headline--logo" class.
clubs = [tag.text.strip() for tag in soup.findAll("h2", class_="content-box-headline--logo")]

# Transfers are listed in tables nested in "responsive-table"-class divs.
tables = [tag.find("table") for tag in soup.findAll("div", class_="responsive-table")]

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

    rows = table.tbody.find_all("tr")
    table_data = []
    for row in rows:
        tds = row.findAll("td")
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

for i, (club, df_in, df_out) in enumerate(zip(clubs, dfs_in, dfs_out)):
    df_in = df_in.rename(columns={"In": "player", "Left": "dealing_club"})
    df_in = df_in.rename(columns=col_names)
    df_in.insert(loc=0, column="club", value=club)
    df_in.insert(loc=1, column="movement", value="in")

    df_out = df_out.rename(columns={"Out": "player", "Joined": "dealing_club"})
    df_out = df_out.rename(columns=col_names)
    df_out.insert(loc=0, column="club", value=club)
    df_out.insert(loc=1, column="movement", value="out")

    dfs_in[i] = df_in
    dfs_out[i] = df_out

data = pd.concat([pd.concat(dfs_in), pd.concat(dfs_out)])
