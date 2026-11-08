"""Regular expressions for Wikipedia dump pages (wikitext).

Everything in the wiki part of the project is extracted with regexes, the
same way as the recipes in extractor/extractor.py. No XML or wikitext
parser is used.

Two groups of regexes are here:

* Java regexes (strings) used inside Spark SQL (regexp_extract, rlike).
  They run in the JVM on the whole dump, so the ~100 GB of XML never has
  to be copied into Python processes.
* Python regexes used only for the small number of food articles that
  survive the first filter: infobox fields, the first paragraph and
  categories.

The module also builds the join keys from recipes (ingredients, dish
name, cuisine). Keys and wiki titles are normalized by the same function,
otherwise they would never be equal.
"""

import html
import re

# ---------------------------------------------------------------------------
# Java regexes for Spark SQL (one <page>...</page> record of the dump)
# ---------------------------------------------------------------------------

TITLE_JAVA = r"<title>(.*?)</title>"
NS_JAVA = r"<ns>(\d+)</ns>"
REDIRECT_JAVA = r'<redirect title="([^"]*)"'
TEXT_JAVA = r"(?s)<text[^>]*>(.*?)</text>"
CATEGORY_JAVA = r"\[\[Category:([^\]|]+)"

# Infoboxes of food articles. "Infobox prepared food", "Infobox dish" and
# "Infobox bread" are redirects to "Infobox food" on Wikipedia, but older
# articles still use those names.
FOOD_INFOBOX_TYPES = (
    "food|prepared food|dish|bread|sauce|beverage|drink|cocktail|cheese"
    "|nutritional value"
)
FOOD_INFOBOX_JAVA = rf"(?i)\{{\{{\s*infobox[ _]+(?:{FOOD_INFOBOX_TYPES})\s*[|\n}}]"

# A category name that contains one of these words marks a food article,
# for example "Indian breads", "Spices", "Root vegetables", "Cocktails".
FOOD_CATEGORY_WORDS = (
    "foods?|dish(?:es)?|cuisines?|cooking|culinary|ingredients?|spices?"
    "|herbs?|vegetables?|fruits?|cheeses?|breads?|cakes?|cookies|biscuits"
    "|desserts?|pastr(?:y|ies)|sauces?|condiments?|beverages?|drinks?"
    "|cocktails?|soups?|stews?|salads?|pasta|noodles|meats?|seafood"
    "|confectionery|edible|nuts|legumes|grains?|cereals?|dairy|snacks?"
    "|sweeteners|staple foods|flours?|teas?|coffee|wines?|beers?|liqueurs?"
)
FOOD_CATEGORY_JAVA = rf"(?i)\b(?:{FOOD_CATEGORY_WORDS})\b"

# ...but not categories of people, companies or places that only mention
# food: "Food Network chefs", "Food and drink companies established in
# 1862", "NUTS 2 statistical regions" (NUTS is not nuts), "Wine regions".
NOT_FOOD_CATEGORY_JAVA = (
    r"(?i)\b(?:people|chefs|cooks|writers|critics|founders|businesspeople"
    r"|executives|activists|companies|organi[sz]ations|establishments"
    r"|brands|restaurants|regions|statistical|programme|deities|goddesses"
    r"|mythological|species|opponents|industry|perfume|television|films?"
    r"|books|songs|albums|births|deaths|terminology|techniques|holy"
    r"|watchlist)\b"
)

# Disambiguation pages list several meanings ("Pepper (disambiguation)"),
# they are not about one food, so they are left out.
DISAMBIGUATION_JAVA = (
    r"(?i)\{\{\s*(?:disambiguation|disambig|dab|set index article"
    r"|surname|given name)\s*[|}]"
)

# ---------------------------------------------------------------------------
# Python regexes for the food articles
# ---------------------------------------------------------------------------

INFOBOX_PATTERN = re.compile(
    rf"\{{\{{\s*infobox[ _]+({FOOD_INFOBOX_TYPES})(?=\s*[|\n}}])(.*?)\n\s*\}}\}}",
    re.IGNORECASE | re.DOTALL,
)
# One "| name = value" parameter. Parameters are usually one per line, but
# some infoboxes put several on one line ("| creator = | course = Main").
# The value therefore ends at the next "|" that is not inside a link
# [[a|b]] or a template {{a|b}} (one level of nesting inside is allowed).
INFOBOX_PARAM_PATTERN = re.compile(
    r"\|\s*([A-Za-z_][\w ]*?)\s*=\s*"
    r"((?:[^|\[{]|\[\[[^\[\]]*\]\]|\{\{(?:[^{}]|\{\{[^{}]*\}\})*\}\}|[\[{])*)"
)
WORD_CHARACTER_PATTERN = re.compile(r"\w")
CATEGORY_PATTERN = re.compile(r"\[\[Category:([^\]|]+)", re.IGNORECASE)

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
REF_SELF_CLOSING_PATTERN = re.compile(r"<ref[^>/]*/>", re.IGNORECASE)
REF_PATTERN = re.compile(r"<ref[^>]*>.*?</ref>", re.IGNORECASE | re.DOTALL)
# Innermost template {{...}} that contains no other template. Removing it
# repeatedly removes nested templates from the inside out.
TEMPLATE_PATTERN = re.compile(r"\{\{[^{}]*\}\}")
TABLE_PATTERN = re.compile(r"\{\|.*?\|\}", re.DOTALL)
# Innermost link [[...]] (File links can contain other links).
LINK_PATTERN = re.compile(r"\[\[([^\[\]]*)\]\]")
EXTERNAL_LINK_PATTERN = re.compile(r"\[https?://[^\s\]]+\s*([^\]]*)\]")
BOLD_ITALIC_PATTERN = re.compile(r"'{2,}")
TAG_PATTERN = re.compile(r"<[^>]+>")
SECTION_PATTERN = re.compile(r"\n==")
SPACES_PATTERN = re.compile(r"[ \t]+")
EMPTY_PARENTHESES_PATTERN = re.compile(r"\(\s*[;,]?\s*\)")
SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+([,.;:])")
SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?])\s")

NON_TEXT_LINK_PREFIXES = ("file:", "image:", "category:", "media:")

# Infobox fields that describe a dish or an ingredient. Other fields
# (image, caption, alt, ...) are not useful for search.
INFOBOX_FIELDS = {
    # Infobox food
    "name", "alternate_name", "country", "region", "national_cuisine",
    "creator", "course", "type", "served", "main_ingredient", "variations",
    "calories", "minor_ingredient",
    # Infobox nutritional value (per 100 g)
    "kj", "protein", "fat", "carbs", "sugars", "fiber", "fibre", "water",
    # Infobox beverage / cocktail / cheese
    "origin", "alcohol", "ingredients", "source", "pasteurized", "texture",
}

ABSTRACT_MAX_CHARS = 600


# ---------------------------------------------------------------------------
# Wikitext cleaning
# ---------------------------------------------------------------------------

def _replace_link(match):
    content = match.group(1)
    if content.lower().startswith(NON_TEXT_LINK_PREFIXES):
        return ""
    # [[Indian cuisine|Indian]] -> Indian, [[India]] -> India
    return content.rsplit("|", 1)[-1]


def _remove_innermost(pattern, text, replacement=""):
    previous = None
    while previous != text:
        previous = text
        text = pattern.sub(replacement, text)
    return text


def clean_wikitext(text):
    """Turn wikitext into plain text (links -> their label, no templates)."""

    text = COMMENT_PATTERN.sub("", text)
    text = REF_SELF_CLOSING_PATTERN.sub("", text)
    text = REF_PATTERN.sub("", text)
    text = _remove_innermost(TEMPLATE_PATTERN, text)
    text = TABLE_PATTERN.sub("", text)
    text = _remove_innermost(LINK_PATTERN, text, _replace_link)
    text = EXTERNAL_LINK_PATTERN.sub(r"\1", text)
    text = BOLD_ITALIC_PATTERN.sub("", text)
    text = TAG_PATTERN.sub("", text)
    text = EMPTY_PARENTHESES_PATTERN.sub("", text)
    text = SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1", text)
    # HTML entities written in the wikitext itself ("1.8&nbsp;billion").
    text = html.unescape(text).replace("\xa0", " ")
    return SPACES_PATTERN.sub(" ", text).strip()


def extract_abstract(wikitext):
    """First paragraph of the article lead (text before the first section)."""

    lead = SECTION_PATTERN.split(wikitext, maxsplit=1)[0]
    # Infoboxes must go before cleaning: their lines would look like text.
    lead = INFOBOX_PATTERN.sub("", lead)
    for paragraph in clean_wikitext(lead).split("\n"):
        paragraph = paragraph.strip()
        # Leftovers of lists, tables or templates are not the abstract.
        if len(paragraph) >= 40 and paragraph[0] not in "|!*#:{}=":
            return shorten(paragraph, ABSTRACT_MAX_CHARS)
    return None


def shorten(text, max_chars):
    """Cut the text after the last whole sentence that fits."""

    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    ends = [match.start() for match in SENTENCE_END_PATTERN.finditer(cut)]
    return cut[:ends[-1]] if ends else cut.rsplit(" ", 1)[0] + " ..."


def extract_infobox(wikitext):
    """(infobox type, {field: plain value}) of the first food infobox."""

    match = INFOBOX_PATTERN.search(wikitext)
    if not match:
        return None, {}
    fields = {}
    for name, value in INFOBOX_PARAM_PATTERN.findall(match.group(2)):
        name = name.strip().lower().replace(" ", "_")
        value = clean_wikitext(value).strip(" ,;")
        # Values that were only templates leave punctuation like ",,,".
        if (name in INFOBOX_FIELDS and name not in fields
                and WORD_CHARACTER_PATTERN.search(value)):
            fields[name] = value
    return match.group(1).lower(), fields


def extract_categories(wikitext):
    return [category.strip() for category in CATEGORY_PATTERN.findall(wikitext)]


def parse_food_article(title, raw_text):
    """All fields of one food article that the join needs.

    raw_text is the XML-escaped <text> of the page ("&lt;ref&gt;").
    """

    wikitext = html.unescape(raw_text or "")
    infobox_type, infobox = extract_infobox(wikitext)
    return {
        "title": title,
        "title_norm": normalize_title(title),
        "url": wiki_url(title),
        "abstract": extract_abstract(wikitext),
        "infobox_type": infobox_type,
        "infobox": infobox,
        "categories": extract_categories(wikitext),
    }


# ---------------------------------------------------------------------------
# Titles and join keys
# ---------------------------------------------------------------------------

def normalize_title(title):
    """Form used for joining: 'Garlic_bread' and 'garlic bread' are equal.

    Must give the same result as normalize_title_sql in wiki_parse.py.
    """

    title = html.unescape(title or "").split("#", 1)[0].replace("_", " ")
    return re.sub(r"\s+", " ", title).strip().lower()


def wiki_url(title):
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


WORD_PATTERN = re.compile(r"\w+(?:['&.-]\w+)*")

# Words in front of an ingredient that do not change what it is:
# "fresh parsley" -> "parsley", "unsalted butter" -> "butter".
INGREDIENT_MODIFIERS = {
    "fresh", "freshly", "dried", "dry", "ground", "chopped", "minced",
    "sliced", "diced", "grated", "shredded", "large", "medium", "small",
    "warm", "cold", "hot", "boiling", "unsalted", "salted", "light", "dark",
    "low-fat", "nonfat", "fat-free", "reduced-fat", "skim", "whole",
    "boneless", "skinless", "frozen", "canned", "cooked", "uncooked", "raw",
    "ripe", "softened", "melted", "packed", "plain", "extra", "virgin",
    "extra-virgin", "granulated", "powdered", "kosher", "sea", "crushed",
    "toasted", "roasted", "lean", "baby", "fine", "coarse",
}

# Words in recipe names that describe the recipe, not the dish.
NAME_STOPWORDS = {
    "easy", "best", "quick", "simple", "homemade", "classic", "the", "my",
    "mom's", "grandma's", "a", "an", "and", "with", "of", "in", "for",
    "or", "to", "on", "style", "recipe", "fabulous", "yummy", "delicious",
    "perfect", "ultimate", "favorite", "favourite", "famous", "awesome",
}

MAX_NAME_NGRAM = 5


def singular_forms(word):
    """Possible English singulars of a word, best first.

    Simple rules cannot decide between berries -> berry and
    cookies -> cookie, so both are returned and Wikipedia decides:
    only the form that is a real title will join.
    """

    if len(word) <= 3 or word.endswith(("ss", "sses", "us", "is")):
        return []
    if word.endswith("ies"):
        return [word[:-3] + "y", word[:-1]]
    if word.endswith(("oes", "ches", "shes", "xes")):
        return [word[:-2], word[:-1]]
    if word.endswith("s"):
        return [word[:-1]]
    return []


def singular(word):
    """The most likely singular: tomatoes -> tomato, berries -> berry."""

    return (singular_forms(word) or [word])[0]


def _with_singular(words):
    """The phrase and the phrase with its last word in singular."""

    return [" ".join(words)] + [
        " ".join(words[:-1] + [form]) for form in singular_forms(words[-1])
    ]


def ingredient_candidates(entity):
    """Wiki titles to try for one ingredient, best first."""

    words = WORD_PATTERN.findall(entity.lower())
    if not words:
        return []
    candidates = _with_singular(words)
    stripped = words
    while len(stripped) > 1 and stripped[0] in INGREDIENT_MODIFIERS:
        stripped = stripped[1:]
    if stripped != words:
        candidates += _with_singular(stripped)
    return list(dict.fromkeys(candidates))


def name_candidates(name):
    """Word n-grams of a recipe name, longest first.

    'Rabbit Stifado' -> ['rabbit stifado', 'stifado', 'rabbit'].
    The longest n-gram that is a food article becomes the recipe's dish.
    """

    words = WORD_PATTERN.findall((name or "").lower())
    candidates = []
    for size in range(min(len(words), MAX_NAME_NGRAM), 0, -1):
        # From the end: in English the main noun is last, so for
        # "I Love Olives" the word "olives" wins over "love".
        for start in range(len(words) - size, -1, -1):
            gram = words[start:start + size]
            if gram[0] in NAME_STOPWORDS or gram[-1] in NAME_STOPWORDS:
                continue
            candidates += _with_singular(gram)
    return list(dict.fromkeys(candidates))


def recipe_keys(recipe):
    """Join keys of one recipe as rows:
    (recipe_id, match_type, source, key, priority).

    Lower priority = better candidate for the same source.
    """

    rows = []
    recipe_id = recipe["id"]

    for priority, key in enumerate(name_candidates(recipe.get("name"))):
        rows.append((recipe_id, "dish", recipe.get("name"), key, priority))

    for entity in dict.fromkeys(recipe.get("ingredient_entities") or []):
        for priority, key in enumerate(ingredient_candidates(entity)):
            rows.append((recipe_id, "ingredient", entity, key, priority))

    # Food.com keywords such as "Indian" or "Mexican" -> "Indian cuisine".
    for keyword in dict.fromkeys(recipe.get("keywords") or []):
        key = normalize_title(f"{keyword} cuisine")
        rows.append((recipe_id, "cuisine", keyword, key, 0))

    return rows
