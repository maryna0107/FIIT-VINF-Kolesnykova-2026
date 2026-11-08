"""Regex extraction of all downloaded HTML pages with Apache Spark.

Spark version of extractor/main.py. The extraction itself is the same
regex extractor (extractor/extractor.py); Spark only splits the pages
into partitions and runs the extractor on all CPU cores in parallel:

    data/html/*.html  ->  (file, recipe)  ->  without duplicates  ->  DataFrame

Output: data/spark/recipes/ (JSON lines, one file per partition).

Usage:
    python3 -m spark_jobs.extract
"""

from pyspark.sql.types import (
    ArrayType, DoubleType, IntegerType, StringType, StructField, StructType,
)

from extractor.extractor import extract_recipe
from spark_jobs.session import create_spark, data_path

HTML_PATTERN = data_path("html/*.html")
OUTPUT_PATH = data_path("spark/recipes")

RECIPE_SCHEMA = StructType([
    StructField("id", StringType()),
    StructField("url", StringType()),
    StructField("name", StringType()),
    StructField("author", StringType()),
    StructField("description", StringType()),
    StructField("category", StringType()),
    StructField("keywords", ArrayType(StringType())),
    StructField("ingredients", ArrayType(StringType())),
    StructField("ingredient_entities", ArrayType(StringType())),
    StructField("instructions", ArrayType(StringType())),
    StructField("prep_minutes", IntegerType()),
    StructField("cook_minutes", IntegerType()),
    StructField("total_minutes", IntegerType()),
    StructField("servings", StringType()),
    StructField("date_published", StringType()),
    StructField("rating", DoubleType()),
    StructField("review_count", IntegerType()),
    StructField("calories", DoubleType()),
    StructField("file", StringType()),
])


def extract_file(path_and_content):
    """Run the regex extractor on one page: (path, bytes) -> (file, recipe)."""

    path, content = path_and_content
    file = "data/html/" + path.rsplit("/", 1)[-1]
    page = content.decode("utf-8", errors="replace")
    return file, extract_recipe(page)


def main():
    spark = create_spark("recipes-extract")

    # Each element is one HTML file: (path, raw bytes).
    pages = spark.sparkContext.binaryFiles(HTML_PATTERN)
    extracted = pages.map(extract_file).cache()

    without_recipe = extracted.filter(lambda item: item[1] is None).keys()

    # Different URLs can redirect to the same recipe, so duplicates are
    # found by the recipe ID from the canonical URL. As in extractor/main.py,
    # the file that comes first alphabetically is kept.
    by_id = (
        extracted
        .filter(lambda item: item[1] is not None)
        .map(lambda item: (item[1]["id"], {**item[1], "file": item[0]}))
    )
    unique = by_id.reduceByKey(
        lambda first, second: first if first["file"] < second["file"] else second
    ).values()

    recipes = spark.createDataFrame(unique, RECIPE_SCHEMA).orderBy("file")
    recipes.write.mode("overwrite").json(OUTPUT_PATH)

    html_count = extracted.count()
    recipe_count = recipes.count()
    print(f"Spark cores:          {spark.sparkContext.defaultParallelism}")
    print(f"Partitions:           {pages.getNumPartitions()}")
    print(f"HTML files:           {html_count}")
    print(f"Extracted recipes:    {recipe_count}")
    print(f"Pages without recipe: {without_recipe.count()}")
    print(f"Duplicate recipes (same canonical URL): "
          f"{by_id.count() - recipe_count}")
    print(f"Saved to: {OUTPUT_PATH}")

    spark.stop()


if __name__ == "__main__":
    main()
