"""Unit tests for the regex extractor.

Run from the project root:
    python3 -m unittest discover tests -v

tests/fixtures/ contains 20 real Food.com pages copied from data/html/,
so the tests do not depend on the crawler or on the network.
"""

import unittest
from pathlib import Path

from extractor.extractor import (
    extract_recipe,
    normalize_ingredient,
    parse_duration_minutes,
    unescape_json_string,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(recipe_id):
    page = (FIXTURES / f"{recipe_id}.html").read_text(encoding="utf-8")
    return extract_recipe(page)


class HelperTests(unittest.TestCase):

    def test_duration_hours_and_minutes(self):
        self.assertEqual(parse_duration_minutes("PT5H30M"), 330)

    def test_duration_minutes_only(self):
        self.assertEqual(parse_duration_minutes("PT25M"), 25)

    def test_duration_with_days(self):
        self.assertEqual(parse_duration_minutes("P1DT2H"), 26 * 60)

    def test_duration_invalid(self):
        self.assertIsNone(parse_duration_minutes("five hours"))
        self.assertIsNone(parse_duration_minutes(None))

    def test_unescape_unicode_and_quotes(self):
        self.assertEqual(
            unescape_json_string(r'Mac & Cheese \"best\"'),
            'Mac & Cheese "best"'
        )

    def test_unescape_removes_html_tags(self):
        self.assertEqual(
            unescape_json_string(r"one<br>two"),
            "one two"
        )

    def test_ingredient_amount_and_unit(self):
        self.assertEqual(normalize_ingredient("2 -3   lbs    stew meat"), "stew meat")

    def test_ingredient_size_and_note(self):
        self.assertEqual(normalize_ingredient("1   large    onion, cut up "), "onion")

    def test_ingredient_parenthesized_amount(self):
        self.assertEqual(
            normalize_ingredient("1 (250   g) package   rice noodles"),
            "rice noodles"
        )

    def test_ingredient_fraction(self):
        self.assertEqual(
            normalize_ingredient("1 1/2  cups    bean sprouts"),
            "bean sprouts"
        )

    def test_ingredient_to_taste(self):
        self.assertEqual(
            normalize_ingredient("1/2  teaspoon    Asian chili sauce, to taste "),
            "asian chili sauce"
        )

    def test_ingredient_box_and_of(self):
        self.assertEqual(
            normalize_ingredient("1 box of chopped pecans"),
            "pecans"
        )


class SyntheticPageTests(unittest.TestCase):

    def test_page_without_recipe(self):
        page = "<html><body><h1>Page not found</h1></body></html>"
        self.assertIsNone(extract_recipe(page))

    def test_review_name_is_not_recipe_name(self):
        page = (
            '<link rel="canonical" href="https://www.food.com/recipe/x-1"/>'
            '<script type="application/ld+json">'
            '{"@type":"Recipe","name":"Real Name",'
            '"recipeIngredient":["1 cup flour"],'
            '"review":[{"@type":"Review","name":"Review Title",'
            '"author":"Reviewer"}]}'
            "</script>"
        )
        recipe = extract_recipe(page)
        self.assertEqual(recipe["name"], "Real Name")
        self.assertIsNone(recipe["author"])
        self.assertEqual(recipe["ingredient_entities"], ["flour"])


class KnownValueTests(unittest.TestCase):

    def test_beef_stew(self):
        recipe = load("15541")
        self.assertEqual(recipe["id"], "15541")
        self.assertEqual(recipe["name"], "4 Hour Beef stew")
        self.assertEqual(recipe["author"], "Zaney1")
        self.assertEqual(recipe["category"], "Stew")
        self.assertEqual(recipe["total_minutes"], 330)
        self.assertEqual(len(recipe["ingredients"]), 10)
        self.assertEqual(len(recipe["instructions"]), 5)
        self.assertIn("stew meat", recipe["ingredient_entities"])
        self.assertEqual(recipe["rating"], 4.0)
        self.assertEqual(recipe["review_count"], 4)

    def test_asian_noodle_salad(self):
        recipe = load("70099")
        self.assertEqual(recipe["name"], "#1 Asian Noodle Salad")
        self.assertIn("Asian", recipe["keywords"])
        self.assertIn("< 30 Mins", recipe["keywords"])
        self.assertIn("rice noodles", recipe["ingredient_entities"])
        self.assertIn("sesame oil", recipe["ingredient_entities"])

    def test_steamed_fish(self):
        recipe = load("37841")
        self.assertEqual(recipe["category"], "Chinese")
        self.assertEqual(recipe["total_minutes"], 45)
        self.assertIn("scallions", recipe["ingredient_entities"])

    def test_quotes_in_name(self):
        self.assertEqual(load("112835")["name"], '"1956" Stuffed Onions')


class AllFixturePagesTests(unittest.TestCase):
    """Properties that must hold for every one of the 20 real pages."""

    def setUp(self):
        self.pages = sorted(FIXTURES.glob("*.html"))

    def test_there_are_20_pages(self):
        self.assertEqual(len(self.pages), 20)

    def test_every_page(self):
        for path in self.pages:
            with self.subTest(page=path.name):
                recipe = extract_recipe(path.read_text(encoding="utf-8"))

                self.assertIsNotNone(recipe)
                self.assertEqual(recipe["id"], path.stem)
                self.assertTrue(
                    recipe["url"].startswith("https://www.food.com/recipe/")
                )
                self.assertTrue(recipe["url"].endswith("-" + path.stem))
                self.assertTrue(recipe["name"])
                self.assertTrue(recipe["category"])
                self.assertGreater(len(recipe["ingredients"]), 0)
                self.assertGreater(len(recipe["ingredient_entities"]), 0)
                self.assertGreater(len(recipe["instructions"]), 0)

                for entity in recipe["ingredient_entities"]:
                    self.assertEqual(entity, entity.lower())
                    self.assertFalse(entity[0].isdigit(), entity)

                if recipe["total_minutes"] is not None:
                    self.assertGreater(recipe["total_minutes"], 0)
                if recipe["rating"] is not None:
                    self.assertTrue(0 <= recipe["rating"] <= 5)


if __name__ == "__main__":
    unittest.main()
