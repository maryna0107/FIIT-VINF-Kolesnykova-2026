"""Own inverted index with term frequencies (TF).

The index maps every term to the recipes that contain it and to how many
times it occurs there:

    "beef" -> {"15541": 6, "37534": 2}

It is built once from data/recipes.jsonl and saved to data/index/index.json.
The searcher only loads the saved file, so the index is rebuilt only when
the extracted data changes.
"""

import json
from collections import Counter
from pathlib import Path

from indexer.tokenizer import tokenize

RECIPES_PATH = Path("data/recipes.jsonl")
INDEX_PATH = Path("data/index/index.json")


def recipe_text(recipe):
    """All searchable text of one recipe."""

    parts = [
        recipe.get("name") or "",
        recipe.get("description") or "",
        recipe.get("category") or "",
        " ".join(recipe.get("keywords") or []),
        " ".join(recipe.get("ingredients") or []),
        " ".join(recipe.get("instructions") or []),
    ]
    return " ".join(parts)


def build_index(recipes):
    """Build the inverted index from extracted recipe dictionaries."""

    postings = {}
    documents = {}

    for recipe in recipes:
        doc_id = recipe["id"]
        term_counts = Counter(tokenize(recipe_text(recipe))) # Count the term frequencies in this recipe.

        documents[doc_id] = {
            "name": recipe.get("name"),
            "url": recipe.get("url"),
            "length": sum(term_counts.values()),
            # Kept for filtering search results (not for scoring).
            "total_minutes": recipe.get("total_minutes"),
            "calories": recipe.get("calories"),
        }

        for term, tf in term_counts.items():
            postings.setdefault(term, {})[doc_id] = tf

    return {
        "document_count": len(documents),
        "documents": documents,
        "postings": postings,
    }


def load_recipes(path=RECIPES_PATH):
    with open(path, encoding="utf-8") as recipes_file:
        return [json.loads(line) for line in recipes_file if line.strip()]


def save_index(index, path=INDEX_PATH):
    """Save the index as readable JSON: one recipe or one term per line.

    {
      "document_count": 2591,
      "documents": {
        "100327": {"name": "Naan", "url": "...", "length": 204, ...},
        ...
      },
      "postings": {
        "feta": {"108622": 1, "166744": 3, ...},
        ...
      }
    }

    Terms are sorted alphabetically so a word is easy to find.
    """

    def entries(items):
        return ",\n".join(
            f"    {json.dumps(key, ensure_ascii=False)}: "
            f"{json.dumps(value, ensure_ascii=False)}"
            for key, value in items
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as index_file:
        index_file.write("{\n")
        index_file.write(f'  "document_count": {index["document_count"]},\n')
        index_file.write('  "documents": {\n')
        index_file.write(entries(index["documents"].items()))
        index_file.write('\n  },\n  "postings": {\n')
        index_file.write(entries(sorted(index["postings"].items())))
        index_file.write("\n  }\n}\n")


def load_index(path=INDEX_PATH):
    with open(path, encoding="utf-8") as index_file:
        return json.load(index_file)


def main():
    recipes = load_recipes()
    index = build_index(recipes)
    save_index(index)

    print(f"Indexed recipes: {index['document_count']}")
    print(f"Unique terms:    {len(index['postings'])}")
    print(f"Saved to:        {INDEX_PATH}")


if __name__ == "__main__":
    main()
