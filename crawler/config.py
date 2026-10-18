"""Central configuration for the sequential requests-based crawler."""

import string
from pathlib import Path


BASE_URL = "https://www.food.com"
HEADERS = {
    "User-Agent": "VINF-STU-Student-Crawler/1.0"
}

# Ten seconds is the maximum time allowed for one HTTP request. It prevents
# one unavailable server from blocking the whole pipeline indefinitely.
REQUEST_TIMEOUT = 10

# One second is an intentional pause after each attempted request. It reduces
# request frequency and is the crawler's politeness/rate-limit mechanism.
REQUEST_DELAY = 1

# Temporary server problems (429 Too Many Requests, 5xx, network errors) are
# retried a limited number of times with a longer pause, so a short outage
# does not lose the page but the server is not hammered either.
MAX_RETRIES = 2
RETRY_DELAY = 10

# All categories of the "All Recipes by Title" listing: 123 and A-Z.
CATEGORIES = ["123"] + list(string.ascii_uppercase)

# Listing pages read per category (None = all pages). One page holds about
# 100 recipes, so one page per letter gives a varied sample of recipes
# from the whole alphabet instead of thousands of recipes from one letter.
MAX_PAGES_PER_CATEGORY = 1

# Recipes downloaded per category (None = all discovered URLs).
# With one listing page per category every category has the same number of
# URLs (100), so the dataset is balanced across the whole alphabet:
# 27 categories x 100 URLs gives about 700 MB of raw HTML.
DOWNLOAD_PER_CATEGORY = None

RECIPE_URLS_PATH = Path("metadata/recipe_urls.tsv")
DOWNLOAD_METADATA_PATH = Path("metadata/downloads.tsv")
HTML_DIRECTORY = Path("data/html")