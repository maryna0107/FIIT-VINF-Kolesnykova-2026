"""Show everything the extractor saved about recipes.

Usage:
    python3 -m indexer.show 209913
    python3 -m indexer.show 209913 520375
"""

import argparse

from indexer.indexer import load_recipes


def format_recipe(recipe, full=True):
    """Readable text of one extracted recipe."""

    lines = [
        f"{recipe['name']}  (ID {recipe['id']})",
        f"  URL:          {recipe['url']}",
        f"  Category:     {recipe['category']}",
        f"  Keywords:     {', '.join(recipe['keywords'])}",
        f"  Time:         prep {recipe['prep_minutes']} min, "
        f"cook {recipe['cook_minutes']} min, total {recipe['total_minutes']} min",
        f"  Servings:     {recipe['servings']}",
        f"  Calories:     {recipe['calories']} kcal per serving",
        f"  Rating:       {recipe['rating']} ({recipe['review_count']} reviews)",
        f"  Entities:     {', '.join(recipe['ingredient_entities'])}",
    ]
    if not full:
        return "\n".join(lines)

    lines += [
        f"  Author:       {recipe['author']}",
        f"  Description:  {recipe['description']}",
        f"  Ingredients ({len(recipe['ingredients'])}):",
    ]
    lines += [f"    - {line}" for line in recipe["ingredients"]]
    lines.append(f"  Steps ({len(recipe['instructions'])}):")
    lines += [
        f"    {number}. {step}"
        for number, step in enumerate(recipe["instructions"], start=1)
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Show extracted recipes")
    parser.add_argument("ids", nargs="+", help="recipe IDs, e.g. 209913")
    args = parser.parse_args()

    recipes = {recipe["id"]: recipe for recipe in load_recipes()}
    for recipe_id in args.ids:
        recipe = recipes.get(recipe_id)
        print(format_recipe(recipe) if recipe else f"Recipe {recipe_id} not found")
        print()


if __name__ == "__main__":
    main()
