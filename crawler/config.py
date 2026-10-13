"""Central configuration for the sequential requests-based crawler."""

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

# Test configuration. Set DOWNLOAD_LIMIT to None for the complete URL file.
CATEGORIES = ["123", "Z"]
DOWNLOAD_LIMIT = 30

RECIPE_URLS_PATH = Path("metadata/recipe_urls.tsv")
DOWNLOAD_METADATA_PATH = Path("metadata/downloads.tsv")
HTML_DIRECTORY = Path("data/html")