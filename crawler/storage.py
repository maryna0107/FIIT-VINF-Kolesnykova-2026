"""File storage operations for discovered URLs, HTML, and metadata."""

import csv


def save_html(filename, content):
    """Write the server response bytes without decoding or changing them."""

    with open(filename, "wb") as html_file:
        html_file.write(content)


def load_completed_urls(metadata_path):
    """Return URLs whose previous recorded result was a successful 200."""

    completed_urls = set()

    if not metadata_path.exists():
        return completed_urls

    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        reader = csv.DictReader(metadata_file, delimiter="\t")

        for row in reader:
            if row["status_code"] == "200":
                completed_urls.add(row["url"])

    return completed_urls

def load_missing_urls(metadata_path):
    """Return URLs for which the server answered 404 (recipe was removed).

    A 404 is a permanent answer, so asking again on the next run would only
    add useless requests. The attempt stays recorded in the metadata.
    """

    missing_urls = set()

    if not metadata_path.exists():
        return missing_urls

    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        reader = csv.DictReader(metadata_file, delimiter="\t")

        for row in reader:
            if row["status_code"] == "404":
                missing_urls.add(row["url"])

    return missing_urls
