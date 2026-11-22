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

The query can use AND, OR, NOT and parentheses (see parse_query).

Usage:
    python3 -m indexer.search "easy chicken" --idf bm25
    python3 -m indexer.search "dinner" --max-minutes 30 --max-calories 500
    python3 -m indexer.search "salt pork garlic" --details
    python3 -m indexer.search "chicken AND garlic NOT onion"
"""

import argparse
import math
import re

from indexer.indexer import load_index, load_recipes
from indexer.show import format_recipe
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


# ---------------------------------------------------------------------------
# Boolean query: AND, OR, NOT and parentheses
#
#   chicken garlic              = chicken OR garlic (as in part 1)
#   chicken AND garlic          both words
#   cake NOT nuts               cake, but not nuts
#   (cake OR pie) AND apple
#
# Operators are written in capitals, as in Lucene. NOT binds the strongest,
# then AND, then OR. Words without an operator between them are joined with
# OR, so a query without operators gives the same results as in part 1.
#
# The query becomes a tree of tuples:
#   "cake NOT nuts" -> ("or", [("term", ["cake"]), ("not", ("term", ["nuts"]))])
# ---------------------------------------------------------------------------

QUERY_TOKEN_PATTERN = re.compile(r"\(|\)|[^\s()]+")


def parse_query(query):
    """Query text -> tree, or None when no word is left (only stopwords)."""

    tokens = QUERY_TOKEN_PATTERN.findall(query)
    position = 0

    def next_token():
        return tokens[position] if position < len(tokens) else None

    def combine(kind, nodes):
        nodes = [node for node in nodes if node is not None]
        if not nodes:
            return None
        return nodes[0] if len(nodes) == 1 else (kind, nodes)

    def parse_or():
        nonlocal position
        nodes = [parse_and()]
        # OR is written, or there is just another word (implicit OR).
        while next_token() not in (None, ")"):
            if next_token() == "OR":
                position += 1
            nodes.append(parse_and())
        return combine("or", nodes)

    def parse_and():
        nonlocal position
        nodes = [parse_not()]
        while next_token() in ("AND", "NOT"):
            if next_token() == "AND":
                position += 1
            # "cake NOT nuts" means "cake AND NOT nuts".
            nodes.append(parse_not())
        return combine("and", nodes)

    def parse_not():
        nonlocal position
        token = next_token()
        if token is None:
            return None
        position += 1
        if token == "NOT":
            node = parse_not()
            return ("not", node) if node else None
        if token == "(":
            node = parse_or()
            if next_token() == ")":
                position += 1
            return node
        # The same tokenizer as for the recipes; a stopword gives no term.
        terms = tokenize(token)
        return ("term", terms) if terms else None

    return parse_or()


def matching_documents(node, index):
    """Set of doc IDs that satisfy the query tree."""

    kind, value = node
    if kind == "term":
        # "all-purpose" gives two tokens, a recipe with either one matches.
        return set().union(*(index["postings"].get(term, {}) for term in value))
    if kind == "not":
        return set(index["documents"]) - matching_documents(value, index)
    sets = [matching_documents(child, index) for child in value]
    return set.intersection(*sets) if kind == "and" else set.union(*sets)


def scored_terms(node):
    """Terms that add to the score. Terms under NOT only exclude recipes."""

    kind, value = node
    if kind == "term":
        return set(value)
    if kind == "not":
        return set()
    return set().union(*(scored_terms(child) for child in value))


def search(index, query, method="classic", limit=10,
           max_minutes=None, max_calories=None):
    """Return [(score, doc_id), ...] sorted from the best match.

    limit=None returns all matching recipes.
    """

    tree = parse_query(query)
    if tree is None:
        return []

    idf_function = IDF_METHODS[method]
    document_count = index["document_count"]
    documents = index["documents"]

    # 1. Boolean part: which recipes match at all.
    matches = {
        doc_id for doc_id in matching_documents(tree, index)
        if passes_filters(documents[doc_id], max_minutes, max_calories)
    }

    # 2. Ranking: TF x IDF summed over the query terms, as in part 1.
    scores = {doc_id: 0.0 for doc_id in matches}
    for term in scored_terms(tree):
        postings = index["postings"].get(term)
        if not postings:
            continue

        idf = idf_function(document_count, len(postings))
        for doc_id, tf in postings.items():
            if doc_id in scores:
                scores[doc_id] += tf * idf

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
    parser.add_argument("--details", action="store_true",
                        help="show the extracted data of every result")
    args = parser.parse_args()

    index = load_index()
    results = search(index, args.query, args.idf, args.limit,
                     args.max_minutes, args.max_calories)
    recipes = (
        {recipe["id"]: recipe for recipe in load_recipes()}
        if args.details else {}
    )

    filtering = args.max_minutes is not None or args.max_calories is not None
    for rank, (score, doc_id) in enumerate(results, start=1):
        document = index["documents"][doc_id]
        details = ""
        if filtering:
            details = (f"  [{document['total_minutes']} min, "
                       f"{document['calories']} kcal]")
        print(f"{rank:2}. {score:8.3f}  [ID {doc_id}]  {document['name']}"
              f"{details}  ({document['url']})")
        if args.details:
            # The first line repeats the name, which is already printed above.
            print(format_recipe(recipes[doc_id], full=False).split("\n", 1)[1])
            print()

    if results and not args.details:
        print("\nFull recipe: python3 -m indexer.show <ID>")


if __name__ == "__main__":
    main()
