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

Usage:
    python3 -m indexer.search "easy chicken" --idf bm25
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


def search(index, query, method="classic", limit=10):
    """Return [(score, doc_id), ...] sorted from the best match."""

    idf_function = IDF_METHODS[method]
    document_count = index["document_count"]
    scores = {}

    for term in set(tokenize(query)):
        postings = index["postings"].get(term)
        if not postings:
            continue

        idf = idf_function(document_count, len(postings))
        for doc_id, tf in postings.items():
            scores[doc_id] = scores.get(doc_id, 0.0) + tf * idf

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [(score, doc_id) for doc_id, score in ranked[:limit]]


def main():
    parser = argparse.ArgumentParser(description="Search recipes")
    parser.add_argument("query")
    parser.add_argument("--idf", choices=IDF_METHODS, default="classic")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    index = load_index()
    results = search(index, args.query, args.idf, args.limit)

    for rank, (score, doc_id) in enumerate(results, start=1):
        document = index["documents"][doc_id]
        print(f"{rank:2}. {score:8.3f}  {document['name']}  ({document['url']})")


if __name__ == "__main__":
    main()
