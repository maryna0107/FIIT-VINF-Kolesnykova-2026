"""Interactive recipe search that keeps running until the user quits.

Works on the outputs of the Spark jobs (consultation 3):
    data/spark/index.json      own TF index built by spark_jobs.index
    data/spark/recipes_wiki/   recipes joined with Wikipedia (spark_jobs.wiki_join)

The search itself (TF x classic / BM25 IDF) is the same as in part 1, so the
results are the same. A shown recipe also lists its Wikipedia data.

Usage:
    python3 -m indexer.interactive

    <text>             search
    <number>           show the recipe with this number from the last list
    /classic, /bm25    switch the IDF method
    q                  quit
"""

from pathlib import Path

from indexer.indexer import load_index
from indexer.search import IDF_METHODS, search
from indexer.show import format_recipe
from spark_jobs.wiki_show import format_wiki, load_recipes

SPARK_INDEX_PATH = Path("data/spark/index.json")

RESULT_LIMIT = 10
QUIT_COMMANDS = {"q", "quit", "exit"}


def print_results(index, results):
    for number, (score, doc_id) in enumerate(results, start=1):
        document = index["documents"][doc_id]
        print(
            f"{number:2}. {document['name']}  "
            f"[{document['total_minutes']} min, {document['calories']} kcal, "
            f"score {score:.2f}]"
        )


def main():
    index = load_index(SPARK_INDEX_PATH)
    recipes = {recipe["id"]: recipe for recipe in load_recipes()}
    method = "classic"
    last_results = []

    while True:
        try:
            line = input(f"\n[IDF: {method}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line.lower() in QUIT_COMMANDS:
            break

        if line.startswith("/") and line[1:] in IDF_METHODS:
            method = line[1:]
        elif line.isdigit():
            number = int(line)
            if 1 <= number <= len(last_results):
                _, doc_id = last_results[number - 1]
                print()
                print(format_recipe(recipes[doc_id]))
                print("\nWikipedia:")
                print(format_wiki(recipes[doc_id]))
        else:
            last_results = search(index, line, method, RESULT_LIMIT)
            print_results(index, last_results)


if __name__ == "__main__":
    main()
