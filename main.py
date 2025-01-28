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

dfs = []
for table in tables:
    col_headers = [th.text for th in table.find_all("th")]
    col_headers.insert(-1, "Country")

    rows = table.tbody.find_all("tr")
    data = []
    for row in rows:
        tds = row.findAll("td")
        transfer = []
        for i, td in enumerate(tds):
            try:
                info = parse_col_index[i](td)
            except:
                info = None
            transfer.append(info)
        data.append(transfer)
    
    df = pd.DataFrame(data, columns=col_headers)
    dfs.append(df)
