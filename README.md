# Web-scraped Transfermarkt transfer data

This script web scrapes [Transfermarkt](https://www.transfermarkt.com) for club transfers and cleans the data.
It currently scrapes only the 2024&ndash;25 season of the English Premier League.

If you are interested in the cleaned data only, see the [releases](https://github.com/eordo/transfermarkt-data/releases).

## Using the data

Transfers are recorded as tabular data, and included in the releases is a data dictionary containing variable names, types, and descriptions.

## Using the script

Set up whatever Python 3 environment you want, install the dependencies, and run the script.

```bash
pip install -r requirements.txt
python main.py
```

The transfer data are written to CSVs in the `data/` directory.

## Releases

* `0.1.1`, 5/25/25
* `0.1.0`, 5/13/25
  * Includes all club transfers for the 2024&ndash;25 English Premier League season.
