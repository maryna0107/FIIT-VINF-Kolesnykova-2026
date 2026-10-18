import csv
import time

from crawler.config import (
    DOWNLOAD_PER_CATEGORY,
    DOWNLOAD_METADATA_PATH,
    HTML_DIRECTORY,
    RECIPE_URLS_PATH,
    REQUEST_DELAY,
)
from crawler.http_client import RequestException, get
from crawler.storage import load_completed_urls, load_missing_urls, save_html

INPUT_PATH = RECIPE_URLS_PATH
METADATA_PATH = DOWNLOAD_METADATA_PATH


def download_recipes():
    """
    Download recipe HTML pages based on recipe_urls.tsv.
    Save raw HTML files and download metadata.
    """

    HTML_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    METADATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not INPUT_PATH.exists():
        print(
            f"ERROR: {INPUT_PATH} does not exist."
        )
        print("Run the discovery crawler first.")
        return False

    # Read discovered recipes.
    with open(
        INPUT_PATH,
        "r",
        encoding="utf-8"
    ) as input_file:

        reader = csv.DictReader(
            input_file,
            delimiter="\t"
        )

        recipes = list(reader)

    if DOWNLOAD_PER_CATEGORY is not None:
        # Keep the first N URLs of every category, in file order, so the
        # dataset contains recipes from the whole alphabet.
        per_category = {}
        selected = []
        for recipe in recipes:
            category = recipe["category"]
            if per_category.get(category, 0) < DOWNLOAD_PER_CATEGORY:
                per_category[category] = per_category.get(category, 0) + 1
                selected.append(recipe)
        recipes = selected

    completed_urls = load_completed_urls(METADATA_PATH)
    missing_urls = load_missing_urls(METADATA_PATH)

    # Create metadata file header only if
    # the file does not already exist.
    metadata_exists = METADATA_PATH.exists()

    with open(
        METADATA_PATH,
        "a",
        encoding="utf-8",
        newline=""
    ) as metadata_file:

        writer = csv.writer(
            metadata_file,
            delimiter="\t"
        )

        if not metadata_exists:
            writer.writerow([
                "recipe_id",
                "url",
                "filename",
                "status_code",
                "size_bytes"
            ])

        total = len(recipes)

        for index, recipe in enumerate(
            recipes,
            start=1
        ):

            url = recipe["url"]

            # Example:
            # .../4-hour-beef-stew-15541
            # becomes 15541.
            recipe_id = url.rsplit("-", 1)[-1]

            filename = (
                HTML_DIRECTORY /
                f"{recipe_id}.html"
            )

            # Skip only when both the file and
            # successful metadata already exist.
            if (
                url in completed_urls
                and filename.exists()
            ):
                print(
                    f"Already downloaded, skipping: "
                    f"{filename}"
                )
                continue

            if url in missing_urls:
                print(f"Previously 404, skipping: {url}")
                continue

            print(
                f"\nDownloading {index}/{total}: {url}"
            )

            try:
                response = get(url)

                status_code = response.status_code
                content = response.content

            except RequestException as error:

                print(
                    f"Request failed: {error}"
                )

                # -1 represents a network-level failure
                # where no HTTP status was received.
                status_code = -1
                content = b""

            if status_code == 200:

                # Save exactly the bytes returned
                # by the server.
                save_html(filename, content)

                saved_filename = str(filename)

                print(f"Saved: {filename}")

                completed_urls.add(url)

            else:

                saved_filename = ""

                print(
                    f"Page not saved. "
                    f"Status: {status_code}"
                )

            # Record every attempted request.
            writer.writerow([
                recipe_id,
                url,
                saved_filename,
                status_code,
                len(content)
            ])

            # Write metadata continuously.
            metadata_file.flush()

            # The delay follows every attempted request, including failures,
            # so errors cannot cause a rapid burst of retries on the server.
            time.sleep(REQUEST_DELAY)

    print("\n========== DOWNLOAD COMPLETE ==========")
    print(f"Metadata saved to: {METADATA_PATH}")

    return True


if __name__ == "__main__":
    download_recipes()