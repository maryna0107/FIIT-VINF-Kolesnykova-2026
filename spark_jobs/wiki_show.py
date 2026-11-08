import argparse
import json
from pathlib import Path

from pyspark.sql.types import ArrayType

from spark_jobs.extract import RECIPE_SCHEMA

RECIPES_WIKI_PATH = Path("data/spark/recipes_wiki")


def load_recipes():
    for part in sorted(RECIPES_WIKI_PATH.glob("part-*.json")):
        with part.open(encoding="utf-8") as file:
            for line in file:
                recipe = json.loads(line)
                # Spark leaves out empty (null) fields in JSON, the recipe
                # printing of part 1 expects every field.
                for field in RECIPE_SCHEMA.fields:
                    empty = [] if isinstance(field.dataType, ArrayType) else None
                    recipe.setdefault(field.name, empty)
                yield recipe


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


def format_wiki(recipe):
    """What was joined from Wikipedia to the recipe, as text."""

    lines = []
    dish = recipe.get("wiki_dish")
    lines.append("  Dish:")
    if dish:
        lines.append(f"    {wiki_line(dish)}")
        if dish.get("abstract"):
            lines.append(f"      \"{dish['abstract'][:300]}\"")
    else:
        lines.append("    -")
    for label, field in [("Cuisines", "wiki_cuisines"), ("Ingredients", "wiki_ingredients")]:
        pages = recipe.get(field) or []
        lines.append(f"  {label} ({len(pages)}):")
        for page in pages:
            lines.append(f"    - {wiki_line(page)}")
    return "\n".join(lines)


def show(recipe):
    print(f"\n{recipe['name']}  (ID {recipe['id']}, {recipe['url']})")
    print(format_wiki(recipe))
    entities = recipe.get("ingredient_entities") or []
    print(f"  Recipe ingredients ({len(entities)}): {', '.join(entities)}")


def main():
    parser = argparse.ArgumentParser(
        description="Show what was joined from Wikipedia to a recipe")
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
