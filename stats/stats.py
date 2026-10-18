"""Statistics of the crawled and extracted data.

Writes metadata/stats.md, ready to be copied to the wiki.

Usage:
    python3 -m stats.stats
"""

import csv
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import tiktoken

from indexer.indexer import recipe_text

RECIPE_URLS_PATH = Path("metadata/recipe_urls.tsv")
DOWNLOADS_PATH = Path("metadata/downloads.tsv")
HTML_DIRECTORY = Path("data/html")
RECIPES_PATH = Path("data/recipes.jsonl")
OUTPUT_PATH = Path("metadata/stats.md")

# Tokenizer used by current OpenAI models.
ENCODING = tiktoken.get_encoding("o200k_base")


def count_tokens(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(ENCODING.encode_ordinary(text))


def megabytes(size):
    return size / (1024 * 1024)


def main():
    with open(RECIPE_URLS_PATH, encoding="utf-8") as urls_file:
        discovered = list(csv.DictReader(urls_file, delimiter="\t"))
    categories = Counter(row["category"] for row in discovered)

    # The latest attempt per URL decides its final status.
    last_status = {}
    with open(DOWNLOADS_PATH, encoding="utf-8") as downloads_file:
        for row in csv.DictReader(downloads_file, delimiter="\t"):
            last_status[row["url"]] = row["status_code"]
    statuses = Counter(last_status.values())

    html_files = sorted(HTML_DIRECTORY.glob("*.html"))
    sizes = [path.stat().st_size for path in html_files]
    total_size = sum(sizes)

    with open(RECIPES_PATH, encoding="utf-8") as recipes_file:
        recipes = [json.loads(line) for line in recipes_file if line.strip()]
    relevant = [recipe for recipe in recipes if recipe["ingredients"]]
    extracted_text = "\n".join(recipe_text(recipe) for recipe in recipes)

    print("Counting tokens in raw HTML (this can take a few minutes)...")
    with ThreadPoolExecutor() as executor:
        html_tokens = sum(executor.map(count_tokens, html_files))
    text_tokens = len(ENCODING.encode_ordinary(extracted_text))

    lines = [
        "# Štatistika dát",
        "",
        "## Crawling",
        "",
        "| Metrika | Hodnota |",
        "|---|---:|",
        f"| Objavené URL receptov | {len(discovered)} |",
    ]
    if len(set(categories.values())) == 1:
        # Balanced crawl: one summary row instead of 27 identical rows.
        lines.append(
            f"| – z každej z {len(categories)} kategórií "
            f"(`{'`, `'.join(sorted(categories))}`) | "
            f"{next(iter(categories.values()))} |"
        )
    else:
        lines += [
            f"| – z kategórie `{category}` | {count} |"
            for category, count in sorted(categories.items())
        ]
    lines += [
        f"| Vyskúšané URL (download) | {len(last_status)} |",
    ]
    lines += [
        f"| – HTTP {status} | {count} |"
        for status, count in sorted(statuses.items())
    ]
    lines += [
        "",
        "## Stiahnuté dokumenty",
        "",
        "| Metrika | Hodnota |",
        "|---|---:|",
        f"| Počet HTML dokumentov | {len(html_files)} |",
        f"| Veľkosť na disku | {megabytes(total_size):.1f} MB |",
        f"| Priemerná veľkosť dokumentu | "
        f"{total_size / max(len(sizes), 1) / 1024:.0f} KB |",
        f"| Najmenší / najväčší dokument | {min(sizes, default=0) / 1024:.0f} KB"
        f" / {max(sizes, default=0) / 1024:.0f} KB |",
        f"| Duplicitné dokumenty (rovnaký recept pod inou URL) "
        f"alebo bez receptu | {len(html_files) - len(recipes)} |",
        f"| Relevantné dokumenty (unikátny recept s ingredienciami) | "
        f"{len(relevant)} ({100 * len(relevant) / max(len(html_files), 1):.1f} %) |",
        "",
        "## Extrahované dáta",
        "",
        "| Metrika | Hodnota |",
        "|---|---:|",
        f"| Extrahované recepty | {len(recipes)} |",
        f"| Ingrediencie (riadky) | "
        f"{sum(len(r['ingredients']) for r in recipes)} |",
        f"| Unikátne ingrediencie (entity) | "
        f"{len({e for r in recipes for e in r['ingredient_entities']})} |",
        f"| Unikátne kategórie | "
        f"{len({r['category'] for r in recipes if r['category']})} |",
        f"| Veľkosť extrahovaného textu | "
        f"{megabytes(len(extracted_text.encode('utf-8'))):.1f} MB |",
        "",
        "## Tokeny (tiktoken, `o200k_base`)",
        "",
        "| Metrika | Hodnota |",
        "|---|---:|",
        f"| Tokeny v raw HTML | {html_tokens:,} |".replace(",", " "),
        f"| Tokeny v extrahovanom texte | {text_tokens:,} |".replace(",", " "),
        f"| Priemer tokenov na recept (extrahovaný text) | "
        f"{text_tokens / max(len(recipes), 1):.0f} |",
    ]

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
