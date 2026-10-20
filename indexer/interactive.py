"""Interactive recipe search that keeps running until the user quits.

Usage:
    python3 -m indexer.interactive

    <text>             search
    <number>           show the recipe with this number from the last list
    /classic, /bm25    switch the IDF method
    q                  quit
"""

from indexer.indexer import load_index, load_recipes
from indexer.search import IDF_METHODS, search
from indexer.show import format_recipe

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
    index = load_index()
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
        else:
            last_results = search(index, line, method, RESULT_LIMIT)
            print_results(index, last_results)


if __name__ == "__main__":
    main()
