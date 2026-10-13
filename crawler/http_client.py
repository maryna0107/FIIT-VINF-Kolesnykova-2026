"""Small HTTP boundary used by both crawler stages."""

import requests

from crawler.config import HEADERS, REQUEST_TIMEOUT

RequestException = requests.RequestException


def get(url):
    """Fetch one URL with the project's shared HTTP policy."""

    # Keeping requests in one module makes timeout and headers consistent in
    # discovery and download, and makes this boundary easy to test or replace.
    return requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )