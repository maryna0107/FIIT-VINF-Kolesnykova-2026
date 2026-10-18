import csv
import re
import time

from crawler.config import (
    BASE_URL,
    CATEGORIES,
    MAX_PAGES_PER_CATEGORY,
    RECIPE_URLS_PATH,
    REQUEST_DELAY,
)
from crawler.http_client import RequestException, get

OUTPUT_PATH = RECIPE_URLS_PATH


def load_existing_recipe_links():
    """Load previously saved URLs so later discovery runs remain append-only."""

    if not OUTPUT_PATH.exists():
        return set()

    existing_links = set()

    with open(OUTPUT_PATH, "r", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file, delimiter="\t")

        for row in reader:
            url = row.get("url", "")
            if url.startswith(BASE_URL):
                existing_links.add(url[len(BASE_URL):])

    return existing_links


def discover_recipes():
    """
    Crawl Food.com listing pages and discover unique recipe URLs.
    Save discovered URLs to metadata/recipe_urls.tsv.
    """

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Start with existing URLs so a second run cannot create duplicate rows.
    seen_recipe_links = load_existing_recipe_links()

   
    output_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0

    with open(
        OUTPUT_PATH,
        "a",
        encoding="utf-8",
        newline=""
    ) as output_file:

        writer = csv.writer(output_file, delimiter="\t")

        if not output_exists:
            writer.writerow(["url", "category"])

        for category in CATEGORIES:

            print(
                f"\n========== CATEGORY {category} =========="
            )

            page = 1

            seen_category_links = set()

            while True:

                listing_url = (
                    f"{BASE_URL}/browse/allrecipes/"
                    f"?page={page}&letter={category}"
                )

                print(
                    f"\nCrawling page {page}: {listing_url}"
                )

                try:
                    response = get(listing_url)

                except RequestException as error:
                    print(f"Request failed: {error}")
                    print(
                        f"Skipping category {category}."
                    )
                    break

                print("Status:", response.status_code)

                if response.status_code != 200:
                    print(
                        "Could not download listing page."
                    )
                    break

                # Extract recipe URLs.
                recipe_links = re.findall(
                    r'href=["\'](/recipe/[^"\']+-\d+)["\']',
                    response.text
                )

                # Remove duplicates on the same page
                # while preserving their order.
                unique_page_links = list(
                    dict.fromkeys(recipe_links)
                )

                # Determine which URLs are new
                # inside this category.
                new_category_links = [
                    link
                    for link in unique_page_links
                    if link not in seen_category_links
                ]

                print(
                    "Recipes on page:",
                    len(unique_page_links)
                )

                print(
                    "New recipes in category:",
                    len(new_category_links)
                )

                # Food.com repeats its final listing page.
                # No new category URLs means pagination ended.
                if not new_category_links:
                    print(
                        f"Category {category} finished."
                    )
                    break

                seen_category_links.update(
                    new_category_links
                )

                # Store only globally unique recipe URLs.
                for link in new_category_links:

                    if link in seen_recipe_links:
                        continue

                    seen_recipe_links.add(link)

                    full_url = BASE_URL + link

                    writer.writerow([
                        full_url,
                        category
                    ])

                # Make sure discovered URLs are written
                # to disk continuously.
                output_file.flush()

                print(
                    "Total unique recipes discovered:",
                    len(seen_recipe_links)
                )

                if (
                    MAX_PAGES_PER_CATEGORY is not None
                    and page >= MAX_PAGES_PER_CATEGORY
                ):
                    print(
                        f"Category {category}: page limit "
                        f"{MAX_PAGES_PER_CATEGORY} reached."
                    )
                    # The next request goes to another category, so the
                    # politeness delay is still needed here.
                    time.sleep(REQUEST_DELAY)
                    break

                page += 1
                # Delay only after a processed page: there is no next request
                # after the repeated terminal page, so no delay is needed.
                time.sleep(REQUEST_DELAY)

    print(
        "\n========== DISCOVERY COMPLETE =========="
    )

    print(
        "Total unique recipe URLs:",
        len(seen_recipe_links)
    )

    print(
        f"Saved to: {OUTPUT_PATH}"
    )

    return len(seen_recipe_links)


if __name__ == "__main__":
    discover_recipes()