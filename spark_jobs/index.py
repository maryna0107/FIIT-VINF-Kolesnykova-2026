from collections import Counter

from indexer.indexer import recipe_text, save_index
from indexer.tokenizer import tokenize
from spark_jobs.extract import RECIPE_SCHEMA
import json
from pathlib import Path

from spark_jobs.session import create_spark, data_path, is_local_path, write_text

RECIPES_PATH = data_path("spark/recipes")
INDEX_PATH = data_path("spark/index.json")


def term_counts(recipe):
    """((term, doc_id), TF) for every term of one recipe."""

    counts = Counter(tokenize(recipe_text(recipe)))
    return [((term, recipe["id"]), tf) for term, tf in counts.items()]


def main():
    spark = create_spark("recipes-index")

    recipes = (
        spark.read.schema(RECIPE_SCHEMA).json(RECIPES_PATH).rdd
        .map(lambda row: row.asDict())
        .cache()
    )

    # Same as Counter in indexer.py, but spread over all partitions:
    # each partition counts its recipes, reduceByKey adds the counts.
    tf = recipes.flatMap(term_counts).reduceByKey(lambda a, b: a + b)
    postings = (
        tf.map(lambda item: (item[0][0], (item[0][1], item[1])))
        .groupByKey()
        .mapValues(lambda docs: dict(sorted(docs)))
    )

    documents = recipes.map(lambda recipe: (recipe["id"], {
        "name": recipe["name"],
        "url": recipe["url"],
        "length": len(tokenize(recipe_text(recipe))),
        # Kept for filtering search results (not for scoring).
        "total_minutes": recipe["total_minutes"],
        "calories": recipe["calories"],
    }))

    # df of a term = number of recipes in its posting list.
    top_df = postings.mapValues(len).takeOrdered(10, key=lambda item: -item[1])

    # The index is small (2591 recipes), so it is collected to the driver
    # and saved as one JSON file that the existing searcher can load.
    index = {
        "document_count": recipes.count(),
        "documents": dict(sorted(documents.collect())),
        "postings": dict(postings.collect()),
    }
    if is_local_path(INDEX_PATH):
        save_index(index, Path(INDEX_PATH.replace("file://", "")))
    else:
        write_text(spark, INDEX_PATH, json.dumps(index))

    print(f"Indexed recipes: {index['document_count']}")
    print(f"Unique terms:    {len(index['postings'])}")
    print("Most common terms (df):")
    for term, df in top_df:
        print(f"  {term:<12} {df}")
    print(f"Saved to:        {INDEX_PATH}")

    spark.stop()


if __name__ == "__main__":
    main()
