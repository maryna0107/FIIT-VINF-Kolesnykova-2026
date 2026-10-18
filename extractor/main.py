"""Run the regex extractor over all downloaded HTML pages.

Output: data/recipes.jsonl, one extracted recipe per line.
The raw HTML is never modified, so extraction can be repeated at any time.
"""

import json
from pathlib import Path

from extractor.extractor import extract_recipe

HTML_DIRECTORY = Path("data/html")
OUTPUT_PATH = Path("data/recipes.jsonl")


def main():
    html_files = sorted(HTML_DIRECTORY.glob("*.html"))
    extracted = 0
    without_recipe = []

    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        for html_file in html_files:
            page = html_file.read_text(encoding="utf-8", errors="replace")
            recipe = extract_recipe(page)

            if recipe is None:
                without_recipe.append(html_file.name)
                continue

            recipe["file"] = str(html_file)
            output_file.write(json.dumps(recipe, ensure_ascii=False) + "\n")
            extracted += 1

    print(f"HTML files:           {len(html_files)}")
    print(f"Extracted recipes:    {extracted}")
    print(f"Pages without recipe: {len(without_recipe)}")
    for name in without_recipe[:10]:
        print(f"  {name}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
