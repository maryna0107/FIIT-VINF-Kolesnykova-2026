"""Check that the Spark jobs give the same result as the part 1 code.

Compares data/spark/recipes/ with data/recipes.jsonl and
data/spark/index.json with data/index/index.json.

Usage (after extractor.main, indexer.indexer and both Spark jobs):
    python3 -m spark_jobs.verify
"""

import json
from pathlib import Path

from indexer.indexer import load_index, load_recipes

SPARK_RECIPES_PATH = Path("data/spark/recipes")


def load_spark_recipes():
    recipes = []
    for part in sorted(SPARK_RECIPES_PATH.glob("part-*.json")):
        recipes += load_recipes(part)
    return recipes


def same_recipe(spark_recipe, recipe):
    # Spark leaves out fields that are null, part 1 writes them as null.
    return all(spark_recipe.get(key) == value for key, value in recipe.items())


def main():
    recipes = {recipe["id"]: recipe for recipe in load_recipes()}
    spark_recipes = {recipe["id"]: recipe for recipe in load_spark_recipes()}
    different = [
        doc_id for doc_id, recipe in recipes.items()
        if doc_id not in spark_recipes
        or not same_recipe(spark_recipes[doc_id], recipe)
    ]
    print(f"Recipes:  part 1 {len(recipes)}, Spark {len(spark_recipes)}, "
          f"different {len(different)}")

    index = load_index()
    spark_index = load_index(Path("data/spark/index.json"))
    print(f"Terms:    part 1 {len(index['postings'])}, "
          f"Spark {len(spark_index['postings'])}")
    print(f"Postings identical:  {index['postings'] == spark_index['postings']}")
    print(f"Documents identical: {index['documents'] == spark_index['documents']}")


if __name__ == "__main__":
    main()
