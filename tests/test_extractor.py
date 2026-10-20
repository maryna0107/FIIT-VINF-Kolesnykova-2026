"""Unit tests of the REGEX extractors.

Every test class tests one regular expression (or one group of regular
expressions that work together). Each regex is run on 20 real pages:

    tests/fixtures/listing/  20 Food.com listing pages (123, A-R)
                             -> regex that extracts recipe URLs (crawler)
    tests/fixtures/recipes/  20 Food.com recipe pages
                             -> regexes that extract recipe data (extractor)

The pages are stored with the tests, so the tests need no network.

Run from the project root:
    python3 -m unittest discover tests -v
"""

import re
import unittest
from pathlib import Path

from crawler.crawler import RECIPE_LINK_PATTERN
from extractor.extractor import (
    CALORIES_PATTERN,
    CANONICAL_PATTERN,
    INGREDIENTS_PATTERN,
    LD_JSON_PATTERN,
    NESTED_START_PATTERN,
    RATING_PATTERN,
    RECIPE_ID_PATTERN,
    RECIPE_TYPE_PATTERN,
    STEP_PATTERN,
    STRING_FIELD_PATTERNS,
    STRING_LITERAL_PATTERN,
    TEMPLATE_DESCRIPTION_PATTERN,
    find_recipe_json,
    normalize_ingredient,
    parse_duration_minutes,
    unescape_json_string,
)

FIXTURES = Path(__file__).parent / "fixtures"
LISTING_PAGES = {
    path.stem: path.read_text(encoding="utf-8")
    for path in sorted((FIXTURES / "listing").glob("*.html"))
}
RECIPE_PAGES = {
    path.stem: path.read_text(encoding="utf-8")
    for path in sorted((FIXTURES / "recipes").glob("*.html"))
}


def recipe_block(recipe_id):
    """The schema.org Recipe block of a page, without nested reviews."""

    block = find_recipe_json(RECIPE_PAGES[recipe_id])
    nested = NESTED_START_PATTERN.search(block)
    return block[:nested.start()] if nested else block


def field(recipe_id, name):
    match = STRING_FIELD_PATTERNS[name].search(recipe_block(recipe_id))
    return unescape_json_string(match.group(1)) if match else None


class FixturePagesTests(unittest.TestCase):
    """The regex tests below run on at least 20 pages of each kind."""

    def test_20_listing_pages(self):
        self.assertEqual(len(LISTING_PAGES), 20)

    def test_20_recipe_pages(self):
        self.assertEqual(len(RECIPE_PAGES), 20)


class RecipeLinkPatternTests(unittest.TestCase):
    """crawler.py: RECIPE_LINK_PATTERN finds recipe URLs on listing pages."""

    def test_every_listing_page_has_100_recipe_links(self):
        for letter, page in LISTING_PAGES.items():
            with self.subTest(page=letter):
                links = set(RECIPE_LINK_PATTERN.findall(page))
                self.assertEqual(len(links), 100)

    def test_every_link_has_recipe_format(self):
        for letter, page in LISTING_PAGES.items():
            for link in RECIPE_LINK_PATTERN.findall(page):
                with self.subTest(page=letter, link=link):
                    self.assertRegex(link, r"^/recipe/[a-z0-9-]+-\d+$")

    def test_known_first_link(self):
        links = RECIPE_LINK_PATTERN.findall(LISTING_PAGES["123"])
        self.assertEqual(links[0], "/recipe/4-hour-beef-stew-15541")

    def test_other_links_are_ignored(self):
        html = (
            '<a href="/recipe/4-hour-beef-stew-15541">stew</a>'
            '<a href="/about">about</a>'
            '<a href="/recipe/">no id</a>'
            "<a href='/recipe/zucchini-bread-123'>single quotes</a>"
        )
        self.assertEqual(
            RECIPE_LINK_PATTERN.findall(html),
            ["/recipe/4-hour-beef-stew-15541", "/recipe/zucchini-bread-123"]
        )


class RecipeBlockPatternTests(unittest.TestCase):
    """LD_JSON_PATTERN + RECIPE_TYPE_PATTERN find the schema.org block."""

    def test_every_recipe_page_has_recipe_block(self):
        for recipe_id, page in RECIPE_PAGES.items():
            with self.subTest(page=recipe_id):
                blocks = LD_JSON_PATTERN.findall(page)
                self.assertTrue(
                    any(RECIPE_TYPE_PATTERN.search(b) for b in blocks)
                )

    def test_page_without_block(self):
        page = "<html><body><h1>Page not found</h1></body></html>"
        self.assertEqual(LD_JSON_PATTERN.findall(page), [])
        self.assertIsNone(find_recipe_json(page))


class CanonicalAndIdPatternTests(unittest.TestCase):
    """CANONICAL_PATTERN + RECIPE_ID_PATTERN give the recipe URL and ID."""

    def test_every_page_id_matches_file_name(self):
        for recipe_id, page in RECIPE_PAGES.items():
            with self.subTest(page=recipe_id):
                url = CANONICAL_PATTERN.search(page).group(1)
                self.assertTrue(url.startswith("https://www.food.com/recipe/"))
                self.assertEqual(RECIPE_ID_PATTERN.search(url).group(1), recipe_id)

    def test_id_is_the_last_number(self):
        url = "https://www.food.com/recipe/4-hour-beef-stew-15541"
        self.assertEqual(RECIPE_ID_PATTERN.search(url).group(1), "15541")


class StringFieldPatternTests(unittest.TestCase):
    """STRING_FIELD_PATTERNS + NESTED_START_PATTERN extract text fields."""

    def test_every_page_has_name_category_and_time(self):
        for recipe_id in RECIPE_PAGES:
            for name in ["name", "recipeCategory", "totalTime"]:
                with self.subTest(page=recipe_id, field=name):
                    self.assertTrue(field(recipe_id, name))

    def test_known_values(self):
        self.assertEqual(field("15541", "name"), "4 Hour Beef stew")
        self.assertEqual(field("15541", "author"), "Zaney1")
        self.assertEqual(field("15541", "recipeCategory"), "Stew")
        self.assertEqual(field("37841", "recipeCategory"), "Chinese")
        self.assertEqual(
            field("15541", "keywords"), "Vegetable,Meat,Winter,Weeknight,Oven"
        )

    def test_escaped_quotes_in_name(self):
        self.assertEqual(field("112835", "name"), '"1956" Stuffed Onions')

    def test_review_name_is_not_recipe_name(self):
        block = (
            '{"@type":"Recipe","name":"Real Name",'
            '"review":[{"@type":"Review","name":"Review Title",'
            '"author":"Reviewer"}]}'
        )
        top_level = block[:NESTED_START_PATTERN.search(block).start()]
        name = STRING_FIELD_PATTERNS["name"].search(top_level).group(1)
        self.assertEqual(name, "Real Name")
        self.assertIsNone(STRING_FIELD_PATTERNS["author"].search(top_level))


class IngredientsPatternTests(unittest.TestCase):
    """INGREDIENTS_PATTERN + STRING_LITERAL_PATTERN extract ingredient lines."""

    def ingredients(self, recipe_id):
        match = INGREDIENTS_PATTERN.search(recipe_block(recipe_id))
        return [
            unescape_json_string(item)
            for item in STRING_LITERAL_PATTERN.findall(match.group(1))
        ]

    def test_every_page_has_ingredients(self):
        for recipe_id in RECIPE_PAGES:
            with self.subTest(page=recipe_id):
                self.assertGreater(len(self.ingredients(recipe_id)), 0)

    def test_known_ingredients(self):
        ingredients = self.ingredients("15541")
        self.assertEqual(len(ingredients), 10)
        self.assertEqual(ingredients[0], "2 -3 lbs stew meat")
        self.assertEqual(ingredients[-1], "1 cup DelMonte ketchup")


class StepPatternTests(unittest.TestCase):
    """STEP_PATTERN extracts the steps of the recipe."""

    def test_every_page_has_steps(self):
        for recipe_id in RECIPE_PAGES:
            with self.subTest(page=recipe_id):
                self.assertGreater(
                    len(STEP_PATTERN.findall(recipe_block(recipe_id))), 0
                )

    def test_known_steps(self):
        steps = STEP_PATTERN.findall(recipe_block("15541"))
        self.assertEqual(len(steps), 5)
        self.assertEqual(steps[0], "Place meat on bottom of 9 X 13 pan.")


class RatingAndCaloriesPatternTests(unittest.TestCase):
    """RATING_PATTERN and CALORIES_PATTERN extract numbers."""

    def test_every_page_has_valid_calories(self):
        for recipe_id in RECIPE_PAGES:
            with self.subTest(page=recipe_id):
                match = CALORIES_PATTERN.search(recipe_block(recipe_id))
                self.assertGreater(float(match.group(1)), 0)

    def test_ratings_are_between_0_and_5(self):
        for recipe_id in RECIPE_PAGES:
            match = RATING_PATTERN.search(recipe_block(recipe_id))
            if match:
                with self.subTest(page=recipe_id):
                    self.assertTrue(0 <= float(match.group(1)) <= 5)
                    self.assertGreaterEqual(int(match.group(2)), 1)

    def test_known_values(self):
        block = recipe_block("15541")
        self.assertEqual(RATING_PATTERN.search(block).groups(), ("4.0", "4"))
        self.assertEqual(CALORIES_PATTERN.search(block).group(1), "240.1")


class DurationPatternTests(unittest.TestCase):
    """DURATION_PATTERN converts ISO 8601 times to minutes."""

    def test_known_durations(self):
        self.assertEqual(parse_duration_minutes("PT5H30M"), 330)
        self.assertEqual(parse_duration_minutes("PT25M"), 25)
        self.assertEqual(parse_duration_minutes("P1DT2H"), 26 * 60)

    def test_invalid_duration(self):
        self.assertIsNone(parse_duration_minutes("five hours"))
        self.assertIsNone(parse_duration_minutes(None))

    def test_every_page_total_time_is_positive(self):
        for recipe_id in RECIPE_PAGES:
            with self.subTest(page=recipe_id):
                minutes = parse_duration_minutes(field(recipe_id, "totalTime"))
                self.assertGreater(minutes, 0)


class UnescapePatternTests(unittest.TestCase):
    """UNICODE_ESCAPE, SIMPLE_ESCAPE and TAG patterns clean JSON text."""

    def test_unicode_and_quotes(self):
        self.assertEqual(
            unescape_json_string(r'Mac & Cheese \"best\"'),
            'Mac & Cheese "best"'
        )

    def test_html_tags_are_removed(self):
        self.assertEqual(unescape_json_string(r"one<br>two"), "one two")


class TemplateDescriptionPatternTests(unittest.TestCase):
    """TEMPLATE_DESCRIPTION_PATTERN recognizes Food.com's filler text."""

    def test_template_is_recognized(self):
        self.assertTrue(TEMPLATE_DESCRIPTION_PATTERN.match(
            "Make and share this E.z. Asian Chicken recipe from Food.com."
        ))

    def test_real_description_is_kept(self):
        self.assertIsNone(
            TEMPLATE_DESCRIPTION_PATTERN.match(field("15541", "description"))
        )


class IngredientNormalizationPatternTests(unittest.TestCase):
    """AMOUNT, UNIT, SIZE and NOTE patterns turn a line into an entity."""

    def test_known_lines(self):
        examples = {
            "2 -3   lbs    stew meat": "stew meat",
            "1   large    onion, cut up ": "onion",
            "1 (250   g) package   rice noodles": "rice noodles",
            "1 1/2  cups    bean sprouts": "bean sprouts",
            "1/2  teaspoon    Asian chili sauce, to taste ": "asian chili sauce",
            "1 box of chopped pecans": "pecans",
        }
        for line, entity in examples.items():
            with self.subTest(line=line):
                self.assertEqual(normalize_ingredient(line), entity)

    def test_every_ingredient_on_every_page(self):
        unit = re.compile(r"^(cups?|tablespoons?|teaspoons?|lbs?|oz)\b")
        for recipe_id in RECIPE_PAGES:
            match = INGREDIENTS_PATTERN.search(recipe_block(recipe_id))
            for item in STRING_LITERAL_PATTERN.findall(match.group(1)):
                entity = normalize_ingredient(unescape_json_string(item))
                with self.subTest(page=recipe_id, ingredient=item):
                    self.assertTrue(entity)
                    self.assertEqual(entity, entity.lower())
                    self.assertFalse(entity[0].isdigit())
                    self.assertIsNone(unit.match(entity))


if __name__ == "__main__":
    unittest.main()
