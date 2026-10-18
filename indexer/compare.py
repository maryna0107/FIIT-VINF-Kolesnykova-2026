"""Compare the classic and BM25 IDF methods on several queries.

Writes metadata/idf_comparison.md, ready to be copied to the wiki.

Usage:
    python3 -m indexer.compare
"""

from pathlib import Path

from indexer.indexer import load_index
from indexer.search import IDF_METHODS, search
from indexer.tokenizer import tokenize

OUTPUT_PATH = Path("metadata/idf_comparison.md")
TOP = 5

# The first two queries contain only rarer terms (both methods should agree),
# the others mix in very common terms (df > N/2), where the methods differ.
QUERIES = [
    "chocolate cake",
    "garlic spinach",
    "easy chicken dinner",
    "quick easy dinner",
    "easy dessert",
    "salt pepper chicken",
]


def term_table(index, query):
    document_count = index["document_count"]
    lines = [
        "| term | df | classic IDF | bm25 IDF |",
        "|---|---:|---:|---:|",
    ]
    for term in dict.fromkeys(tokenize(query)):
        df = len(index["postings"].get(term, {}))
        if df == 0:
            lines.append(f"| {term} | 0 | – | – |")
            continue
        values = [
            IDF_METHODS[method](document_count, df) for method in IDF_METHODS
        ]
        lines.append(
            f"| {term} | {df} | " + " | ".join(f"{v:.3f}" for v in values) + " |"
        )
    return lines


def results_table(index, query):
    results = {
        method: search(index, query, method, TOP) for method in IDF_METHODS
    }
    lines = [
        "| # | classic | score | bm25 | score |",
        "|---:|---|---:|---|---:|",
    ]
    for rank in range(TOP):
        cells = [str(rank + 1)]
        for method in IDF_METHODS:
            if rank < len(results[method]):
                score, doc_id = results[method][rank]
                name = index["documents"][doc_id]["name"].replace("|", "/")
                cells += [name, f"{score:.2f}"]
            else:
                cells += ["", ""]
        lines.append("| " + " | ".join(cells) + " |")

    classic_ids = {doc_id for _, doc_id in search(index, query, "classic", 10)}
    bm25_ids = {doc_id for _, doc_id in search(index, query, "bm25", 10)}
    overlap = len(classic_ids & bm25_ids)
    return lines, overlap


def main():
    index = load_index()
    output = [
        "# Porovnanie IDF metód",
        "",
        f"Index: {index['document_count']} receptov, "
        f"{len(index['postings'])} unikátnych termov.",
        "",
    ]

    for query in QUERIES:
        table, overlap = results_table(index, query)
        output += [f"## Dopyt: `{query}`", ""]
        output += term_table(index, query)
        output += [""]
        output += table
        output += ["", f"Zhoda top 10 výsledkov: {overlap}/10", ""]

    OUTPUT_PATH.write_text("\n".join(output), encoding="utf-8")
    print("\n".join(output))
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
