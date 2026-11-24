from pathlib import Path

from indexer.indexer import load_index
from indexer.search import search as search_old
from lucene_search.search import LuceneSearcher

OUTPUT_PATH = Path("metadata/old_vs_lucene.md")
SPARK_INDEX_PATH = Path("data/spark/index.json")
TOP = 5

# (query, what it tests, old query, filters of the old index)
# The old index has no ranges in the query, it gets the same limits
# as filters (--max-minutes, --max-calories).
QUERIES = [
    ("chocolate cake", "bežný dopyt (OR)", None, {}),
    ("easy chicken dinner", "časté slová", None, {}),
    ("chicken AND garlic NOT onion", "Boolean AND, NOT", None, {}),
    ("(cake OR pie) AND apple", "Boolean OR, zátvorky", None, {}),
    ('"olive oil"', "fráza", None, {}),
    ("tomatoes", "stemming (tomatoes = tomato)", None, {}),
    ("spagetti~", "fuzzy (preklep)", None, {}),
    ("choco*", "wildcard", None, {}),
    ("flatbread", "Wikipédia: abstrakt jedla", None, {}),
    ("cuisine:mexican", "Wikipédia: pole cuisine", None, {}),
    ("cake NOT chocolate", "Boolean NOT", None, {}),
    ("chicken minutes:[* TO 30] calories:[* TO 500]", "range",
     "chicken", {"max_minutes": 30, "max_calories": 500}),
]


def main():
    index = load_index(SPARK_INDEX_PATH)
    lucene = LuceneSearcher()
    names = {doc_id: doc["name"] for doc_id, doc in index["documents"].items()}

    output = [
        "# Porovnanie: starý index vs. Lucene",
        "",
        f"Recepty: {index['document_count']} (starý), "
        f"{lucene.document_count} (Lucene). Top {TOP} výsledkov, "
        "zhoda = koľko z top 10 je v oboch.",
        "",
    ]

    for query, purpose, old_query, filters in QUERIES:
        old_results = search_old(index, old_query or query, limit=None, **filters)
        lucene_total, lucene_results = lucene.search(query, 10)
        old_ids = [doc_id for _, doc_id in old_results[:10]]
        lucene_ids = [result["id"] for result in lucene_results]

        output += [
            f"## `{query}` – {purpose}",
            "",
            f"Lucene dopyt: `{lucene.explain_query(query)}`",
            "",
            f"Nájdené: starý {len(old_results)}, Lucene {lucene_total}. "
            f"Zhoda top 10: {len(set(old_ids) & set(lucene_ids))}/10",
            "",
            "| # | starý index | Lucene |",
            "|---:|---|---|",
        ]
        for rank in range(TOP):
            old_name = names[old_ids[rank]] if rank < len(old_ids) else ""
            new_name = lucene_results[rank]["name"] if rank < len(lucene_results) else ""
            # "|" in a recipe name would split the Markdown table cell.
            cells = [str(rank + 1), old_name.replace("|", "/"), new_name.replace("|", "/")]
            output.append("| " + " | ".join(cells) + " |")
        output.append("")

    OUTPUT_PATH.write_text("\n".join(output), encoding="utf-8")
    print("\n".join(output))
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
