"""Show what was joined from Wikipedia to one recipe.

Reads the output of spark_jobs.wiki_join (data/spark/recipes_wiki/), no
Spark is needed.

Usage:
    python3 -m spark_jobs.wiki_show 100327          # recipe ID
    python3 -m spark_jobs.wiki_show --examples 5    # 5 recipes with most links
"""

import argparse
import json
from pathlib import Path

RECIPES_WIKI_PATH = Path("data/spark/recipes_wiki")


def load_recipes():
    for part in sorted(RECIPES_WIKI_PATH.glob("part-*.json")):
        with part.open(encoding="utf-8") as file:
            for line in file:
                yield json.loads(line)


def link_count(recipe):
    return (bool(recipe.get("wiki_dish")) + len(recipe.get("wiki_ingredients") or [])
            + len(recipe.get("wiki_cuisines") or []))


def wiki_line(page):
    attributes = ", ".join(
        f"{name}: {value}" for name, value in page.items()
        if name not in ("title", "url", "abstract") and value
    )
    text = f"{page['title']}  <{page['url']}>"
    return text + (f"\n      {attributes}" if attributes else "")


def show(recipe):
    print(f"\n{recipe['name']}  (ID {recipe['id']}, {recipe['url']})")
    dish = recipe.get("wiki_dish")
    print("  Dish:")
    if dish:
        print(f"    {wiki_line(dish)}")
        if dish.get("abstract"):
            print(f"      \"{dish['abstract'][:300]}\"")
    else:
        print("    -")
    for label, field in [("Cuisines", "wiki_cuisines"), ("Ingredients", "wiki_ingredients")]:
        pages = recipe.get(field) or []
        print(f"  {label} ({len(pages)}):")
        for page in pages:
            print(f"    - {wiki_line(page)}")
    entities = recipe.get("ingredient_entities") or []
    print(f"  Recipe ingredients ({len(entities)}): {', '.join(entities)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("recipe_id", nargs="?")
    parser.add_argument("--examples", type=int, default=0)
    args = parser.parse_args()

    recipes = list(load_recipes())
    if args.recipe_id:
        recipes = [recipe for recipe in recipes if recipe["id"] == args.recipe_id]
        if not recipes:
            print(f"Recipe {args.recipe_id} not found.")
    else:
        recipes.sort(key=link_count, reverse=True)
        recipes = recipes[:args.examples or 3]
    for recipe in recipes:
        show(recipe)


if __name__ == "__main__":
    main()
