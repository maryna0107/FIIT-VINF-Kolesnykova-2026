"""Searcher over the own inverted index with two IDF methods.

score(recipe, query) = sum over query terms of  TF(term, recipe) * IDF(term)

N  = number of recipes in the index
df = number of recipes that contain the term

classic: log(N / df)
    Rare terms get a high weight. A term found in every recipe gets 0,
    so it is ignored, but common terms never get a negative weight.

bm25:    log((N - df + 0.5) / (df + 0.5))
    Probabilistic (Robertson-Sparck Jones) IDF used by BM25. A term found
    in more than half of the recipes gets a NEGATIVE weight, so recipes
    that repeat very common words are pushed down.

Results can be filtered by the extracted preparation time and calories
(calories per serving, as stated by Food.com):

Usage:
    python3 -m indexer.search "easy chicken" --idf bm25
    python3 -m indexer.search "dinner" --max-minutes 30 --max-calories 500
"""

import argparse
import math

from indexer.indexer import load_index
from indexer.tokenizer import tokenize


def idf_classic(document_count, df):
    return math.log10(document_count / df)


def idf_bm25(document_count, df):
    return math.log10((document_count - df + 0.5) / (df + 0.5))


IDF_METHODS = {
    "classic": idf_classic,
    "bm25": idf_bm25,
}


def passes_filters(document, max_minutes=None, max_calories=None):
    """True when the recipe meets the time and calorie limits.

    A recipe without the value cannot be shown to meet the limit,
    so it is left out when that filter is used.
    """

    minutes = document.get("total_minutes")
    calories = document.get("calories")
    if max_minutes is not None and (minutes is None or minutes > max_minutes):
        return False
    if max_calories is not None and (calories is None or calories > max_calories):
        return False
    return True


def search(index, query, method="classic", limit=10,
           max_minutes=None, max_calories=None):
    """Return [(score, doc_id), ...] sorted from the best match."""

    idf_function = IDF_METHODS[method]
    document_count = index["document_count"]
    documents = index["documents"]
    scores = {}

    for term in set(tokenize(query)):
        postings = index["postings"].get(term)
        if not postings:
            continue

        idf = idf_function(document_count, len(postings))
        for doc_id, tf in postings.items():
            if not passes_filters(documents[doc_id], max_minutes, max_calories):
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + tf * idf

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [(score, doc_id) for doc_id, score in ranked[:limit]]


def main():
    parser = argparse.ArgumentParser(description="Search recipes")
    parser.add_argument("query")
    parser.add_argument("--idf", choices=IDF_METHODS, default="classic")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-minutes", type=int,
                        help="only recipes with total time up to N minutes")
    parser.add_argument("--max-calories", type=float,
                        help="only recipes with up to N kcal per serving")
    args = parser.parse_args()

    index = load_index()
    results = search(index, args.query, args.idf, args.limit,
                     args.max_minutes, args.max_calories)

    filtering = args.max_minutes is not None or args.max_calories is not None
    for rank, (score, doc_id) in enumerate(results, start=1):
        document = index["documents"][doc_id]
        details = ""
        if filtering:
            details = (f"  [{document['total_minutes']} min, "
                       f"{document['calories']} kcal]")
        print(f"{rank:2}. {score:8.3f}  {document['name']}{details}  "
              f"({document['url']})")


if __name__ == "__main__":
    main()
