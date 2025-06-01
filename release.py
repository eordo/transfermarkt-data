"""
Archiving Transfermarkt transfer data

This script compresses the saved transfer data to TAR and ZIP files. This is a 
utility script to be used for GitHub releases and sharing the data online.
"""

import shutil
from pathlib import Path
from main import DATA_DIR


assert DATA_DIR.exists(), f"Cannot find directory {DATA_DIR}"


RELEASE_DIR = Path("./release")
RELEASE_DIR.mkdir(exist_ok=True)
ARCHIVE_NAME = "data"


release_tar = RELEASE_DIR / f"{ARCHIVE_NAME}.tar.gz"
release_zip = RELEASE_DIR / f"{ARCHIVE_NAME}.zip"
if release_tar.exists() or release_zip.exists():
    prompt_str = "Overwrite most recent release? [y/N] "
    yeses = ["yes", "y"]
    nos = ["no", "n", ""]
    acceptable_answers = yeses + nos
    answer = input(prompt_str).lower()
    while answer not in acceptable_answers:
        answer = input(prompt_str).lower()
    if answer in nos:
        quit()

for archive_format in ("gztar", "zip"):
    shutil.make_archive(
        base_name=RELEASE_DIR / ARCHIVE_NAME,
        format=archive_format,
        root_dir=DATA_DIR
    )

print(f"TAR saved as {release_tar}")
print(f"ZIP saved as {release_zip}")
