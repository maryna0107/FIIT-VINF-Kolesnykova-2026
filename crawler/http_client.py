"""Small HTTP boundary used by both crawler stages."""

import time

import requests

from crawler.config import HEADERS, MAX_RETRIES, REQUEST_TIMEOUT, RETRY_DELAY

RequestException = requests.RequestException

# Statuses that usually mean a temporary problem on the server side.
RETRY_STATUSES = {500, 502, 503, 504}


def get(url):
    """Fetch one URL with the project's shared HTTP policy."""

    # Keeping requests in one module makes timeout, headers and retries
    # consistent in discovery and download.
    for attempt in range(MAX_RETRIES + 1):
        is_last_attempt = attempt == MAX_RETRIES

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )
        except RequestException:
            if is_last_attempt:
                raise
            print(f"Network error, retrying in {RETRY_DELAY} s")
            time.sleep(RETRY_DELAY)
            continue

        if response.status_code in RETRY_STATUSES and not is_last_attempt:
            print(
                f"Status {response.status_code}, "
                f"retrying in {RETRY_DELAY} s"
            )
            time.sleep(RETRY_DELAY)
            continue

        return response
