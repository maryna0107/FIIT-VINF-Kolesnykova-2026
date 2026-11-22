"""Search in the Lucene index (consultation 4).

Query types (Lucene QueryParser syntax):

  chicken garlic                 OR, ranked by BM25 (more matching words = higher)
  chicken AND garlic             Boolean AND, also: +chicken +garlic
  cake NOT nuts                  Boolean NOT, also: cake -nuts
  (cake OR pie) AND apple        parentheses
  "olive oil"                    phrase: the words next to each other
  spagetti~                      fuzzy: up to 2 typos ("spaghetti")
  choco*                         wildcard: chocolate, chocolatey, ...
  ingredient:garlic              one field only
  name:soup^2 cream              boost: a word in a field counts more
  minutes:[* TO 30]              range over a number (* = no limit)
  calories:[200 TO 500] rating:[4.5 TO *]

A word without a field is searched in all text fields of SEARCH_FIELDS, with
their boosts. Ranges are not words, so they are taken out of the query text
and added as a filter: they only remove recipes, they do not change the score.

Usage (in Docker):
    docker compose run --rm lucene python -m lucene_search.search "chicken AND garlic"
"""

import argparse
import re

# lucene first: it makes the Java packages (java.*, org.apache.*) importable.
import lucene  # noqa: F401
from java.nio.file import Paths
from java.util import HashMap
from java.lang import Float
from org.apache.lucene.document import DoublePoint, IntPoint
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser
from org.apache.lucene.search import (
    BooleanClause, BooleanQuery, IndexSearcher, MatchAllDocsQuery,
)
from org.apache.lucene.store import FSDirectory

from lucene_search.common import INDEX_DIR, create_analyzer, start_jvm

# Text fields searched when the query word has no field, with their weight.
SEARCH_FIELDS = {
    "name": 3.0,
    "ingredient": 2.0,
    "category": 1.5,
    "keywords": 1.5,
    "wiki_dish": 1.0,
    "cuisine": 1.0,
    "description": 1.0,
    "instructions": 0.5,
}

# minutes:[* TO 30]  ->  ("minutes", "*", "30")
RANGE_PATTERN = re.compile(r"\b(minutes|calories|rating):\[(\S+) TO (\S+)\]")


def range_query(field, low, high):
    """Lucene range query over a number field. "*" means no limit."""

    if field == "minutes":
        low = -2**31 if low == "*" else int(low)
        high = 2**31 - 1 if high == "*" else int(high)
        return IntPoint.newRangeQuery(field, low, high)
    low = float("-inf") if low == "*" else float(low)
    high = float("inf") if high == "*" else float(high)
    return DoublePoint.newRangeQuery(field, low, high)


def text_parser():
    boosts = HashMap()
    for field, boost in SEARCH_FIELDS.items():
        boosts.put(field, Float(boost))
    return MultiFieldQueryParser(list(SEARCH_FIELDS), create_analyzer(), boosts)


def negative_clauses(query):
    """Clauses of a query that only excludes ("NOT nuts"), else None."""

    if not BooleanQuery.instance_(query):
        return None
    clauses = list(BooleanQuery.cast_(query).clauses())
    if clauses and all(c.occur() == BooleanClause.Occur.MUST_NOT for c in clauses):
        return clauses
    return None


def build_query(text):
    """Query text -> Lucene query: text part (scored) + ranges (filter)."""

    ranges = [range_query(*match) for match in RANGE_PATTERN.findall(text)]
    text = RANGE_PATTERN.sub(" ", text).strip()

    builder = BooleanQuery.Builder()
    if not text:
        # Only a range, e.g. "minutes:[* TO 10]": all recipes, then filtered.
        builder.add(MatchAllDocsQuery(), BooleanClause.Occur.MUST)
    else:
        # Java has several parse methods, PyLucene needs the parser given
        # explicitly to pick the one that parses the text.
        query = MultiFieldQueryParser.parse(text_parser(), text)
        excluded = negative_clauses(query)
        if excluded:
            # "NOT nuts" alone: Lucene needs something to remove the recipes
            # from, so it is "all recipes, but not nuts".
            builder.add(MatchAllDocsQuery(), BooleanClause.Occur.MUST)
            for clause in excluded:
                builder.add(clause)
        else:
            builder.add(query, BooleanClause.Occur.MUST)
    for query in ranges:
        builder.add(query, BooleanClause.Occur.FILTER)
    return builder.build()


class LuceneSearcher:
    def __init__(self, index_dir=INDEX_DIR):
        start_jvm()
        reader = DirectoryReader.open(FSDirectory.open(Paths.get(index_dir)))
        self.searcher = IndexSearcher(reader)
        self.document_count = reader.numDocs()

    def search(self, text, limit=10):
        """Return (total hits, [result dict, ...]) sorted from the best match."""

        query = build_query(text)
        top = self.searcher.search(query, limit)
        stored = self.searcher.storedFields()
        results = []
        for hit in top.scoreDocs:
            document = stored.document(hit.doc)
            results.append({
                "id": document.get("id"),
                "name": document.get("name"),
                "category": document.get("category"),
                "minutes": document.get("minutes"),
                "calories": document.get("calories"),
                "rating": document.get("rating"),
                "score": hit.score,
            })
        # totalHits is exact only up to 1000 hits (Lucene stops counting
        # to be faster), count() gives the exact number.
        return self.searcher.count(query), results

    def explain_query(self, text):
        """The query as Lucene understood it, e.g. +(name:chicken^3.0 ...)."""

        return build_query(text).toString()


def main():
    parser = argparse.ArgumentParser(description="Search recipes in Lucene")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--explain", action="store_true",
                        help="print the query as Lucene parsed it")
    args = parser.parse_args()

    searcher = LuceneSearcher()
    try:
        total, results = searcher.search(args.query, args.limit)
    except lucene.JavaError as error:  # ParseException from Java
        print(f"Wrong query: {error.getJavaException().getMessage().splitlines()[0]}")
        return

    if args.explain:
        print(f"Lucene query: {searcher.explain_query(args.query)}\n")
    print(f"Found: {total} of {searcher.document_count} recipes\n")
    for rank, result in enumerate(results, start=1):
        print(f"{rank:2}. {result['score']:7.3f}  [ID {result['id']}]  "
              f"{result['name']}  [{result['minutes']} min, "
              f"{result['calories']} kcal, rating {result['rating']}]")


if __name__ == "__main__":
    main()
