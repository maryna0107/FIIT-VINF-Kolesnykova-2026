import re
import unittest

from spark_jobs.wiki_regex import (
    CATEGORY_JAVA, DISAMBIGUATION_JAVA, FOOD_CATEGORY_JAVA, FOOD_INFOBOX_JAVA,
    NOT_FOOD_CATEGORY_JAVA, NS_JAVA, REDIRECT_JAVA, TEXT_JAVA, TITLE_JAVA,
    clean_wikitext, extract_abstract, extract_categories, extract_infobox,
    ingredient_candidates, name_candidates, normalize_title,
    parse_food_article, recipe_keys, singular,
)

# A shortened page in the form it has in the dump (XML-escaped wikitext).
NAAN_PAGE = """  <page>
    <title>Naan</title>
    <ns>0</ns>
    <id>412578</id>
    <revision>
      <text bytes="5000" xml:space="preserve">{{Short description|Leavened flatbread}}
{{Infobox food
| name = Naan
| image = Naan shiva.jpg
| caption = Naan with [[butter]]
| alternate_name = Nan
| type = [[Flatbread]]
| course = Main
| country = [[India]]{{ref|a}}
| region = [[South Asia]], [[Central Asia]]
| main_ingredient = [[Flour]], [[yeast]], [[salt]], [[water]]
}}
'''Naan''' ({{lang-fa|نان}}) is a leavened, [[oven]]-baked or [[tawa]]-fried [[flatbread]]&lt;ref name="Oxford"/&gt; which is found in the cuisines mainly of [[Western Asia]], [[Central Asia]], [[Indian subcontinent]] and the [[Caribbean]].&lt;ref&gt;{{cite book|title=Oxford}}&lt;/ref&gt;

== Etymology ==
The earliest appearance of ''naan'' in English is from 1780.

[[Category:Indian breads]]
[[Category:Leavened breads|Naan]]
</text>
    </revision>
"""

REDIRECT_PAGE = """  <page>
    <title>Chickpeas</title>
    <ns>0</ns>
    <redirect title="Chickpea" />
    <revision><text bytes="22" xml:space="preserve">#REDIRECT [[Chickpea]]</text></revision>
"""


class JavaRegexTest(unittest.TestCase):
    """Regexes that run in Spark SQL on every page of the dump."""

    def test_title_ns_redirect(self):
        self.assertEqual(re.search(TITLE_JAVA, NAAN_PAGE).group(1), "Naan")
        self.assertEqual(re.search(NS_JAVA, NAAN_PAGE).group(1), "0")
        self.assertIsNone(re.search(REDIRECT_JAVA, NAAN_PAGE))
        self.assertEqual(re.search(REDIRECT_JAVA, REDIRECT_PAGE).group(1), "Chickpea")

    def test_text(self):
        text = re.search(TEXT_JAVA, NAAN_PAGE).group(1)
        self.assertTrue(text.startswith("{{Short description"))
        self.assertTrue(text.rstrip().endswith("[[Category:Leavened breads|Naan]]"))

    def test_categories(self):
        self.assertEqual(re.findall(CATEGORY_JAVA, NAAN_PAGE),
                         ["Indian breads", "Leavened breads"])

    def test_food_infobox(self):
        self.assertRegex(NAAN_PAGE, FOOD_INFOBOX_JAVA)
        self.assertRegex("{{infobox_prepared food\n| name = X", FOOD_INFOBOX_JAVA)
        self.assertRegex("{{Infobox nutritional value | kJ = 100", FOOD_INFOBOX_JAVA)
        # Other infoboxes and longer names are not food.
        self.assertNotRegex("{{Infobox country\n| name = India", FOOD_INFOBOX_JAVA)
        self.assertNotRegex("{{Infobox foodservice company\n", FOOD_INFOBOX_JAVA)

    def test_food_category(self):
        for category in ["Indian breads", "Spices", "Root vegetables",
                         "Cocktails with gin", "Italian cuisine", "Cheeses"]:
            self.assertRegex(category, FOOD_CATEGORY_JAVA, category)
        for category in ["Living people", "1990 births", "Teachers of art",
                         "Vegetation of India"]:
            self.assertNotRegex(category, FOOD_CATEGORY_JAVA, category)

    def test_not_food_category(self):
        # Categories with a food word that are about people, companies or places.
        for category in ["Food Network chefs", "American food writers",
                         "Food and drink companies established in 1862",
                         "NUTS 2 statistical regions of the European Union",
                         "Wine regions of Canada", "Fruit of the Holy Spirit",
                         "Cooking techniques", "Culinary terminology"]:
            self.assertRegex(category, NOT_FOOD_CATEGORY_JAVA, category)
        for category in ["Indian breads", "Leaf vegetables", "Herbs"]:
            self.assertNotRegex(category, NOT_FOOD_CATEGORY_JAVA, category)

    def test_disambiguation(self):
        self.assertRegex("'''Pepper''' may refer to:\n{{Disambiguation}}",
                         DISAMBIGUATION_JAVA)
        self.assertRegex("{{dab|food}}", DISAMBIGUATION_JAVA)
        self.assertNotRegex(NAAN_PAGE, DISAMBIGUATION_JAVA)


class WikitextTest(unittest.TestCase):
    """Python regexes that run only on food articles."""

    def wikitext(self):
        raw = re.search(TEXT_JAVA, NAAN_PAGE).group(1)
        return parse_food_article("Naan", raw)

    def test_infobox(self):
        article = self.wikitext()
        self.assertEqual(article["infobox_type"], "food")
        self.assertEqual(article["infobox"], {
            "name": "Naan",
            "alternate_name": "Nan",
            "type": "Flatbread",
            "course": "Main",
            "country": "India",
            "region": "South Asia, Central Asia",
            "main_ingredient": "Flour, yeast, salt, water",
        })

    def test_abstract(self):
        self.assertEqual(
            self.wikitext()["abstract"],
            "Naan is a leavened, oven-baked or tawa-fried flatbread which is "
            "found in the cuisines mainly of Western Asia, Central Asia, "
            "Indian subcontinent and the Caribbean.")

    def test_categories_and_url(self):
        article = self.wikitext()
        self.assertEqual(article["categories"], ["Indian breads", "Leavened breads"])
        self.assertEqual(article["url"], "https://en.wikipedia.org/wiki/Naan")
        self.assertEqual(article["title_norm"], "naan")

    def test_clean_wikitext(self):
        self.assertEqual(
            clean_wikitext("[[File:A.jpg|thumb|A [[cake]]]] '''Cake''' is "
                           "{{nowrap|{{lang|fr|x}}}}a [[Baking|baked]] food."),
            "Cake is a baked food.")
        self.assertEqual(clean_wikitext("see [https://x.org the site]"),
                         "see the site")

    def test_abstract_skips_short_lines(self):
        text = "{{Infobox food\n| name = X\n}}\n'''Tea'''\n\n'''Tea''' is an " \
               "aromatic beverage prepared by pouring hot water over leaves.\n== History =="
        self.assertEqual(extract_abstract(text),
                         "Tea is an aromatic beverage prepared by pouring hot "
                         "water over leaves.")

    def test_infobox_params_on_one_line(self):
        text = ("{{Infobox food\n| name = Couscous\n| creator = | course = Main "
                "course, side dish\n| served = | main_ingredient = [[Semolina|semolina]]"
                "\n| alternate_name = {{lang|ar|x}}, {{lang|ber|y}}\n| calories = 150\n}}")
        self.assertEqual(extract_infobox(text), ("food", {
            "name": "Couscous", "course": "Main course, side dish",
            "main_ingredient": "semolina", "calories": "150",
        }))

    def test_html_entities(self):
        self.assertEqual(clean_wikitext("1.8&nbsp;billion"), "1.8 billion")

    def test_no_infobox(self):
        self.assertEqual(extract_infobox("'''Salt''' is a mineral."), (None, {}))
        self.assertEqual(extract_categories("no categories"), [])


class JoinKeyTest(unittest.TestCase):
    """Normalization of titles and keys built from recipes."""

    def test_normalize_title(self):
        self.assertEqual(normalize_title("Garlic_bread#History"), "garlic bread")
        self.assertEqual(normalize_title("AT&amp;T"), "at&t")
        self.assertEqual(normalize_title("  Crème   brûlée "), "crème brûlée")

    def test_singular(self):
        for plural, word in [("tomatoes", "tomato"), ("berries", "berry"),
                             ("eggs", "egg"), ("peaches", "peach"),
                             ("molasses", "molasses"), ("peas", "pea"),
                             ("hummus", "hummus")]:
            self.assertEqual(singular(plural), word)

    def test_ingredient_candidates(self):
        self.assertEqual(ingredient_candidates("Fresh Parsley"),
                         ["fresh parsley", "parsley"])
        self.assertEqual(ingredient_candidates("chickpeas"),
                         ["chickpeas", "chickpea"])
        self.assertEqual(ingredient_candidates("all-purpose flour"),
                         ["all-purpose flour"])

    def test_name_candidates(self):
        self.assertEqual(name_candidates("Rabbit Stifado"),
                         ["rabbit stifado", "stifado", "rabbit"])
        candidates = name_candidates("Easy M&M Cookies")
        self.assertEqual(candidates[:3], ["m&m cookies", "m&m cooky", "m&m cookie"])
        self.assertNotIn("easy", candidates)
        # Words of the same length: the last word (the main noun) first.
        candidates = name_candidates("I Love Olives")
        self.assertLess(candidates.index("olives"), candidates.index("love"))

    def test_recipe_keys(self):
        keys = recipe_keys({
            "id": "100327", "name": "Naan",
            "ingredient_entities": ["salt", "salt", "warm water"],
            "keywords": ["Indian", "Easy"],
        })
        self.assertIn(("100327", "dish", "Naan", "naan", 0), keys)
        self.assertIn(("100327", "ingredient", "warm water", "water", 1), keys)
        self.assertIn(("100327", "cuisine", "Indian", "indian cuisine", 0), keys)
        # The same ingredient twice gives its keys only once.
        self.assertEqual(sum(1 for key in keys if key[2] == "salt"), 1)


if __name__ == "__main__":
    unittest.main()
