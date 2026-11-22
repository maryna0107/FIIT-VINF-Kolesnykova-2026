"""Boolean queries (AND, OR, NOT) of the own index, on a tiny index."""

import unittest

from indexer.indexer import build_index
from indexer.search import parse_query, search

RECIPES = [
    {"id": "1", "name": "Chicken with garlic"},
    {"id": "2", "name": "Chicken with onion and garlic"},
    {"id": "3", "name": "Apple cake"},
    {"id": "4", "name": "Apple pie"},
    {"id": "5", "name": "Chocolate cake with nuts"},
]


def found(query):
    return sorted(doc_id for _, doc_id in search(INDEX, query, limit=None))


INDEX = build_index(RECIPES)


class ParseQueryTest(unittest.TestCase):
    def test_words_without_operator_are_or(self):
        self.assertEqual(parse_query("apple cake"),
                         ("or", [("term", ["apple"]), ("term", ["cake"])]))

    def test_not_binds_stronger_than_and(self):
        self.assertEqual(
            parse_query("chicken AND NOT onion"),
            ("and", [("term", ["chicken"]), ("not", ("term", ["onion"]))]))

    def test_only_stopwords_give_no_query(self):
        self.assertIsNone(parse_query("the and of"))


class BooleanSearchTest(unittest.TestCase):
    def test_or(self):
        self.assertEqual(found("cake OR pie"), ["3", "4", "5"])

    def test_and(self):
        self.assertEqual(found("chicken AND garlic"), ["1", "2"])

    def test_not(self):
        self.assertEqual(found("chicken AND garlic NOT onion"), ["1"])
        self.assertEqual(found("cake NOT nuts"), ["3"])

    def test_not_alone_is_everything_else(self):
        self.assertEqual(found("NOT apple"), ["1", "2", "5"])

    def test_parentheses(self):
        self.assertEqual(found("(cake OR pie) AND apple"), ["3", "4"])

    def test_excluded_words_do_not_add_to_score(self):
        with_not = search(INDEX, "cake NOT nuts")
        without_not = search(INDEX, "cake")
        self.assertEqual(with_not[0][0], dict(
            (doc_id, score) for score, doc_id in without_not)["3"])


if __name__ == "__main__":
    unittest.main()
