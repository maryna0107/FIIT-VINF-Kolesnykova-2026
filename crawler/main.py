import sys

from crawler.crawler import discover_recipes
from crawler.downloader import download_recipes


def main():

    print(
        "\n======================================"
    )
    print("FOOD.COM RECIPE CRAWLER")
    print(
        "======================================"
    )

    print(
        "\n========== PHASE 1: DISCOVERY =========="
    )

    try:
        discovered_count = discover_recipes()

    except Exception as error:
        print(
            f"\nDiscovery failed: {error}"
        )
        print("Pipeline stopped.")
        sys.exit(1)

    print(
        f"\nDiscovery finished: "
        f"{discovered_count} unique recipes."
    )

    print(
        "\n========== PHASE 2: DOWNLOAD =========="
    )

    try:
        success = download_recipes()

    except Exception as error:
        print(
            f"\nDownload phase failed: {error}"
        )
        print("Pipeline stopped.")
        sys.exit(1)

    if not success:
        print("\nPipeline stopped.")
        sys.exit(1)

    print(
        "\n======================================"
    )
    print("PIPELINE FINISHED SUCCESSFULLY")
    print(
        "======================================"
    )


if __name__ == "__main__":
    main()