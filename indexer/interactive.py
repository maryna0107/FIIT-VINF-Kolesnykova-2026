"""Interactive recipe search that keeps running until the user quits.

Two indexes over the outputs of the Spark jobs:
    lucene   data/lucene/            Lucene index (consultation 4), default
    old      data/spark/index.json   own TF x IDF index (parts 1 and 3)

Both understand AND, OR, NOT and parentheses. Lucene also phrases ("olive oil"),
fuzzy (spagetti~), wildcards (choco*), fields (ingredient:garlic) and ranges
(minutes:[* TO 30]), see lucene_search/search.py.

A shown recipe also lists its Wikipedia data.

Usage (Lucene needs the Docker container):
    docker compose run --rm lucene
    python3 -m indexer.interactive          only the old index, without Docker

    <text>             search
    <number>           show the recipe with this number from the last list
    /lucene, /old      switch the index
    /classic, /bm25    switch the IDF method of the old index
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


def open_lucene():
    """The Lucene searcher, or None outside the Docker container."""

    try:
        from lucene_search.search import LuceneSearcher
    except ImportError:
        print("PyLucene is not installed here, only the old index is available.")
        return None
    return LuceneSearcher()


def search_old(index, line, method):
    """[(recipe ID, line to print), ...] from the own index."""

    results = search(index, line, method, limit=None)
    print(f"Found: {len(results)} of {index['document_count']} recipes")
    rows = []
    for score, doc_id in results[:RESULT_LIMIT]:
        document = index["documents"][doc_id]
        rows.append((doc_id, f"{document['name']}  [{document['total_minutes']} min, "
                             f"{document['calories']} kcal, score {score:.2f}]"))
    return rows


def search_lucene(searcher, line):
    """[(recipe ID, line to print), ...] from Lucene."""

    try:
        total, results = searcher.search(line, RESULT_LIMIT)
    except Exception as error:  # lucene.JavaError: ParseException from Java
        print(f"Wrong query: {error.getJavaException().getMessage().splitlines()[0]}")
        return []
    print(f"Found: {total} of {searcher.document_count} recipes")
    return [
        (result["id"], f"{result['name']}  [{result['minutes']} min, "
                       f"{result['calories']} kcal, score {result['score']:.2f}]")
        for result in results
    ]


def main():
    index = load_index(SPARK_INDEX_PATH)
    lucene_searcher = open_lucene()
    recipes = {recipe["id"]: recipe for recipe in load_recipes()}
    engine = "lucene" if lucene_searcher else "old"
    method = "classic"
    last_results = []

    while True:
        label = "lucene" if engine == "lucene" else f"old, IDF: {method}"
        try:
            line = input(f"\n[{label}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line.lower() in QUIT_COMMANDS:
            break

        if line == "/lucene" and lucene_searcher:
            engine = "lucene"
        elif line == "/old":
            engine = "old"
        elif line.startswith("/") and line[1:] in IDF_METHODS:
            method = line[1:]
        elif line.isdigit():
            number = int(line)
            if 1 <= number <= len(last_results):
                doc_id, _ = last_results[number - 1]
                print()
                print(format_recipe(recipes[doc_id]))
                print("\nWikipedia:")
                print(format_wiki(recipes[doc_id]))
        else:
            if engine == "lucene":
                last_results = search_lucene(lucene_searcher, line)
            else:
                last_results = search_old(index, line, method)
            for number, (_, text) in enumerate(last_results, start=1):
                print(f"{number:2}. {text}")


if __name__ == "__main__":
    main()
