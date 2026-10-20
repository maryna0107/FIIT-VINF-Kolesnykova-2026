"""Interactive recipe search that keeps running until the user quits.

Usage:
    python3 -m indexer.interactive

Type a query to get a numbered list of recipes, then type the number of a
result to show the whole saved recipe. The index and the recipes are loaded
only once, at the start, so every search is immediate.

Commands:
    <text>              search, e.g.  salt pork garlic
    <number>            show the recipe with this number from the last list
    /classic, /bm25     switch the IDF method
    /minutes N          only recipes with total time up to N minutes
    /kcal N             only recipes with up to N kcal per serving
    /clear              remove the time and calorie filters
    /help               show the commands
    q                   quit
"""

from indexer.indexer import load_index, load_recipes
from indexer.search import IDF_METHODS, search
from indexer.show import format_recipe

RESULT_LIMIT = 10
QUIT_COMMANDS = {"q", "quit", "exit", "/q", "/quit", "/exit"}

HELP = """Commands:
  <text>            search, e.g.  salt pork garlic
  <number>          show the recipe with this number from the last list
  /classic, /bm25   switch the IDF method
  /minutes N        only recipes with total time up to N minutes
  /kcal N           only recipes with up to N kcal per serving
  /clear            remove the time and calorie filters
  /help             show this help
  q                 quit"""


def settings_text(settings):
    parts = [f"IDF: {settings['method']}"]
    if settings["max_minutes"] is not None:
        parts.append(f"max {settings['max_minutes']} min")
    if settings["max_calories"] is not None:
        parts.append(f"max {settings['max_calories']:g} kcal")
    return ", ".join(parts)


def print_results(index, results):
    if not results:
        print("No recipes found.")
        return

    for number, (score, doc_id) in enumerate(results, start=1):
        document = index["documents"][doc_id]
        print(
            f"{number:2}. {document['name']}  "
            f"[{document['total_minutes']} min, {document['calories']} kcal, "
            f"score {score:.2f}]"
        )
    print("Type a number to show the recipe.")


def handle_command(command, settings):
    """Apply a /command. Returns a message for the user."""

    name, _, value = command[1:].partition(" ")
    value = value.strip()

    if name in IDF_METHODS:
        settings["method"] = name
    elif name in ("minutes", "kcal"):
        key = "max_minutes" if name == "minutes" else "max_calories"
        try:
            settings[key] = int(value) if name == "minutes" else float(value)
        except ValueError:
            return f"Usage: /{name} N   (e.g. /{name} 30)"
    elif name == "clear":
        settings["max_minutes"] = None
        settings["max_calories"] = None
    elif name == "help":
        return HELP
    else:
        return f"Unknown command /{name}. Type /help."

    return f"Settings: {settings_text(settings)}"


def main():
    print("Loading index and recipes...")
    index = load_index()
    recipes = {recipe["id"]: recipe for recipe in load_recipes()}
    print(f"Ready: {index['document_count']} recipes. "
          f"Type a query, a number to show a recipe, /help, or q to quit.")

    settings = {"method": "classic", "max_minutes": None, "max_calories": None}
    last_results = []

    while True:
        try:
            line = input(f"\n[{settings_text(settings)}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line.lower() in QUIT_COMMANDS:
            break

        if line.startswith("/"):
            print(handle_command(line, settings))
        elif line.isdigit():
            number = int(line)
            if 1 <= number <= len(last_results):
                _, doc_id = last_results[number - 1]
                print()
                print(format_recipe(recipes[doc_id]))
            else:
                print("No result with this number. Search first, "
                      "then type a number from the list.")
        else:
            last_results = search(
                index, line, settings["method"], RESULT_LIMIT,
                settings["max_minutes"], settings["max_calories"]
            )
            print_results(index, last_results)

    print("Bye.")


if __name__ == "__main__":
    main()
