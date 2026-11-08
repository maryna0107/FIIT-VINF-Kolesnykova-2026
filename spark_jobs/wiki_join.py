import io
import json
from contextlib import redirect_stdout

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from spark_jobs.extract import RECIPE_SCHEMA
from spark_jobs.session import create_spark, data_path, write_text
from spark_jobs.wiki_regex import recipe_keys

RECIPES_PATH = data_path("spark/recipes")
WIKI_DIR = data_path("spark/wiki")
OUTPUT_DIR = data_path("spark")

KEY_SCHEMA = StructType([
    StructField("recipe_id", StringType()),
    StructField("match_type", StringType()),
    StructField("source", StringType()),
    StructField("key", StringType()),
    StructField("priority", IntegerType()),
])

WIKI_ATTRIBUTES = [
    "country", "region", "course", "type", "main_ingredient", "served",
    "kj", "protein", "fat", "carbs",
]


def wiki_struct():
    return F.struct(
        F.col("wiki_title").alias("title"),
        F.col("url"),
        F.col("abstract"),
        *[F.col("infobox")[name].alias(name) for name in WIKI_ATTRIBUTES],
    )


def main():
    spark = create_spark("wiki-join")

    recipes = spark.read.schema(RECIPE_SCHEMA).json(RECIPES_PATH).cache()
    keys = spark.createDataFrame(
        recipes.rdd.flatMap(lambda row: recipe_keys(row.asDict())), KEY_SCHEMA
    ).cache()

    food = spark.read.parquet(f"{WIKI_DIR}/food")
    redirects = spark.read.parquet(f"{WIKI_DIR}/redirects")

    titles = (
        food.select(F.col("title_norm").alias("key"),
                    F.col("title_norm").alias("target_norm"),
                    F.lit(False).alias("via_redirect"))
        .unionByName(
            redirects.select(F.col("title_norm").alias("key"), "target_norm",
                             F.lit(True).alias("via_redirect")))
    )

    # Join 1: recipe keys x wiki titles. The keys are small (tens of
    # thousands of rows), so they are broadcast to every partition of the
    # big title table (millions of redirects) - no shuffle of the titles.
    candidates = F.broadcast(keys).join(titles, on="key")

    # Join 2: the target must be a food article. This also resolves the
    # redirects and drops non-food meanings ("Salt" the treaty, ...).
    joined = candidates.join(
        food.withColumnRenamed("title", "wiki_title"),
        candidates.target_norm == food.title_norm,
    )

    # Best key per recipe and source: the dish is the longest n-gram,
    # an ingredient its exact form before modifiers were removed.
    best = Window.partitionBy("recipe_id", "match_type", "source") \
                 .orderBy("priority", "via_redirect")
    links = (
        joined.withColumn("rank", F.row_number().over(best))
        .filter("rank = 1")
        .drop("rank")
        .dropDuplicates(["recipe_id", "match_type", "wiki_title"])
        .cache()
    )

    plan = io.StringIO()
    with redirect_stdout(plan):
        joined.explain(mode="formatted")
    write_text(spark, f"{OUTPUT_DIR}/wiki_join_plan.txt", plan.getvalue())

    links.select(
        "recipe_id", "match_type", "source", "key", "via_redirect",
        "wiki_title", "url",
    ).orderBy("recipe_id", "match_type", "wiki_title") \
     .write.mode("overwrite").json(f"{OUTPUT_DIR}/wiki_links")

    matched = (
        # A map column cannot be grouped by, the other fields are the same
        # for one title, so the first value is taken.
        links.groupBy("wiki_title")
        .agg(*[F.first(name).alias(name) for name in
               ["url", "abstract", "infobox_type", "infobox", "categories"]],
             F.countDistinct("recipe_id").alias("recipe_count"),
             F.collect_set("match_type").alias("match_types"))
        .orderBy(F.desc("recipe_count"), "wiki_title")
        .cache()
    )
    matched.write.mode("overwrite").json(f"{OUTPUT_DIR}/wiki_matched")

    # Recipes with their wiki data, the input for the new (Lucene) index.
    per_recipe = links.groupBy("recipe_id").agg(
        F.first(F.when(F.col("match_type") == "dish", wiki_struct()),
                ignorenulls=True).alias("wiki_dish"),
        F.collect_list(F.when(F.col("match_type") == "ingredient", wiki_struct()))
         .alias("wiki_ingredients"),
        F.collect_list(F.when(F.col("match_type") == "cuisine", wiki_struct()))
         .alias("wiki_cuisines"),
    )
    enriched = recipes.join(
        per_recipe, recipes.id == per_recipe.recipe_id, "left"
    ).drop("recipe_id")
    enriched.orderBy("file").write.mode("overwrite").json(
        f"{OUTPUT_DIR}/recipes_wiki")

    stats = collect_stats(recipes, keys, links, matched)
    write_text(spark, f"{OUTPUT_DIR}/wiki_join_stats.json",
               json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
    print_stats(stats)

    spark.stop()


def collect_stats(recipes, keys, links, matched):
    recipe_count = recipes.count()
    per_type = {
        row["match_type"]: row.asDict()
        for row in links.groupBy("match_type").agg(
            F.count("*").alias("links"),
            F.countDistinct("recipe_id").alias("recipes"),
            F.countDistinct("wiki_title").alias("unique_wiki_pages"),
            F.sum(F.col("via_redirect").cast("int")).alias("via_redirect"),
        ).collect()
    }
    entities = keys.filter("match_type = 'ingredient'").select("source").distinct().count()
    matched_entities = links.filter("match_type = 'ingredient'") \
                            .select("source").distinct().count()

    filled = matched.select(
        F.count("*").alias("pages"),
        F.count("abstract").alias("abstract"),
        F.sum(F.col("infobox_type").isNotNull().cast("int")).alias("infobox"),
        *[F.count(F.col("infobox")[name]).alias(name) for name in WIKI_ATTRIBUTES],
    ).first().asDict()

    return {
        "recipes": recipe_count,
        "recipes_with_wiki": links.select("recipe_id").distinct().count(),
        "links": links.count(),
        "unique_wiki_pages": matched.count(),
        "per_type": per_type,
        "ingredient_entities": entities,
        "ingredient_entities_matched": matched_entities,
        "attributes_filled": filled,
        "top_pages": [
            {"title": row["wiki_title"], "recipes": row["recipe_count"]}
            for row in matched.limit(15).collect()
        ],
    }


def print_stats(stats):
    print(f"Recipes:                 {stats['recipes']}")
    print(f"Recipes with wiki data:  {stats['recipes_with_wiki']}")
    print(f"Links recipe -> wiki:    {stats['links']}")
    print(f"Unique wiki pages:       {stats['unique_wiki_pages']}")
    print(f"Ingredient entities:     {stats['ingredient_entities_matched']} of "
          f"{stats['ingredient_entities']} matched")
    for match_type, row in sorted(stats["per_type"].items()):
        print(f"  {match_type:<11} links {row['links']:>6}, recipes "
              f"{row['recipes']:>5}, unique pages {row['unique_wiki_pages']:>5}, "
              f"via redirect {row['via_redirect']:>5}")
    print("Attributes filled (of matched pages):")
    for name, value in stats["attributes_filled"].items():
        print(f"  {name:<16} {value}")
    print("Most linked wiki pages:")
    for page in stats["top_pages"]:
        print(f"  {page['title']:<30} {page['recipes']}")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
