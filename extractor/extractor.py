"""Regex extractor for Food.com recipe pages.

Every Food.com recipe page embeds a schema.org Recipe description inside
<script type="application/ld+json">. schema.org is a public standard shared
by recipe websites, so the extractor does not depend on Food.com's visual
layout, CSS classes or XPath. All values are extracted with regular
expressions.
"""

import html
import re

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# One JSON string literal, including escaped quotes such as \"
JSON_STRING = r'"((?:[^"\\]|\\.)*)"'

LD_JSON_PATTERN = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>',
    re.DOTALL
)
RECIPE_TYPE_PATTERN = re.compile(r'"@type"\s*:\s*"Recipe"')
CANONICAL_PATTERN = re.compile(r'<link rel="canonical" href="([^"]+)"')
RECIPE_ID_PATTERN = re.compile(r'-(\d+)/?$')

# The Recipe object lists its own fields before the nested "review" and
# "publisher" objects, so the first match of a top-level key is the
# recipe's value, not the value of a review or the publisher.
NESTED_START_PATTERN = re.compile(r',"(?:review|publisher)"\s*:')

STRING_FIELD_PATTERNS = {
    field: re.compile(rf'"{field}"\s*:\s*{JSON_STRING}')
    for field in [
        "name",
        "author",
        "description",
        "recipeCategory",
        "keywords",
        "prepTime",
        "cookTime",
        "totalTime",
        "recipeYield",
        "datePublished",
    ]
}

INGREDIENTS_PATTERN = re.compile(
    rf'"recipeIngredient"\s*:\s*\[((?:\s*{JSON_STRING}\s*,?)*)\]'
)
STEP_PATTERN = re.compile(
    rf'"@type"\s*:\s*"HowToStep"\s*,\s*"text"\s*:\s*{JSON_STRING}'
)
RATING_PATTERN = re.compile(
    r'"aggregateRating"\s*:\s*\{[^}]*?"ratingValue"\s*:\s*"?([\d.]+)"?'
    r'[^}]*?"reviewCount"\s*:\s*"?(\d+)"?'
)
CALORIES_PATTERN = re.compile(r'"calories"\s*:\s*"?([\d.]+)"?')
STRING_LITERAL_PATTERN = re.compile(JSON_STRING)

# ISO 8601 durations such as PT5H30M or P1DT2H.
DURATION_PATTERN = re.compile(
    r'^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:\d+S)?)?$'
)

UNICODE_ESCAPE_PATTERN = re.compile(r'\\u([0-9a-fA-F]{4})')
SIMPLE_ESCAPE_PATTERN = re.compile(r'\\(["\\/bfnrt])')
SIMPLE_ESCAPES = {
    '"': '"', "\\": "\\", "/": "/",
    "b": "", "f": "", "n": " ", "r": " ", "t": " ",
}
TAG_PATTERN = re.compile(r'<[^>]+>')
WHITESPACE_PATTERN = re.compile(r'\s+')

# Ingredient lines look like "1 1/2  cups    bean sprouts, chopped".
# The patterns below remove amounts, units, size words and preparation notes
# so that only the ingredient entity ("bean sprouts") remains.
AMOUNT_PATTERN = re.compile(
    r'^[\s\d/.\-–]*(?:\([^)]*\))?[\s\d/.\-–]*'
)
UNITS = (
    r'cups?|c\.|tablespoons?|tbsps?|tbs|teaspoons?|tsps?|ounces?|oz|'
    r'pounds?|lbs?|lb|grams?|g|kilograms?|kg|ml|milliliters?|liters?|l|'
    r'pints?|quarts?|gallons?|cans?|packages?|pkgs?|jars?|bottles?|'
    r'box(?:es)?|bags?|envelopes?|sticks?|cloves?|stalks?|slices?|pieces?|'
    r'heads?|bunch(?:es)?|sprigs?|dash(?:es)?|pinch(?:es)?|drops?|'
    r'containers?|loaf|loaves|fillets?|squares?|inch(?:es)?'
)
UNIT_PATTERN = re.compile(rf'^(?:(?:{UNITS})\b\.?\s*)+', re.IGNORECASE)
SIZE_PATTERN = re.compile(
    r'^(?:(?:of|small|medium|large|extra[- ]large|big|whole|fresh|'
    r'chopped|diced|minced|sliced|grated|shredded|ground|dried|'
    r'frozen|canned|cooked|finely|thinly|coarsely|lightly)\b\s*)+',
    re.IGNORECASE
)
NOTE_PATTERN = re.compile(r'\s*(?:,|\(| - | or |\bto taste\b).*$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def unescape_json_string(value):
    """Turn a raw JSON string literal into readable text."""

    value = UNICODE_ESCAPE_PATTERN.sub(
        lambda match: chr(int(match.group(1), 16)), value
    )
    value = SIMPLE_ESCAPE_PATTERN.sub(
        lambda match: SIMPLE_ESCAPES[match.group(1)], value
    )
    value = html.unescape(value)
    value = TAG_PATTERN.sub(" ", value)
    return WHITESPACE_PATTERN.sub(" ", value).strip()


def parse_duration_minutes(value):
    """Convert an ISO 8601 duration like PT5H30M to minutes (330)."""

    if not value:
        return None

    match = DURATION_PATTERN.match(value)
    if not match:
        return None

    days, hours, minutes = (int(part or 0) for part in match.groups())
    return days * 24 * 60 + hours * 60 + minutes


def normalize_ingredient(line):
    """Extract the ingredient entity from one ingredient line.

    "2 -3   lbs    stew meat"        -> "stew meat"
    "1   large    onion, cut up "    -> "onion"
    "1 (250   g) package   rice noodles" -> "rice noodles"
    """

    text = WHITESPACE_PATTERN.sub(" ", line).strip()
    text = AMOUNT_PATTERN.sub("", text)
    text = UNIT_PATTERN.sub("", text)
    text = AMOUNT_PATTERN.sub("", text)
    text = SIZE_PATTERN.sub("", text)
    text = NOTE_PATTERN.sub("", text)
    return text.strip(" .-").lower()


def find_recipe_json(page):
    """Return the text of the schema.org Recipe block, or None."""

    for match in LD_JSON_PATTERN.finditer(page):
        block = match.group(1)
        if RECIPE_TYPE_PATTERN.search(block):
            return block
    return None


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_recipe(page):
    """Extract one recipe from raw Food.com HTML.

    Returns a dictionary, or None when the page contains no recipe
    (for example an error page). Missing fields are None or empty lists.
    """

    recipe_json = find_recipe_json(page)
    if recipe_json is None:
        return None

    # Only the recipe's own top-level fields, without nested reviews.
    nested_start = NESTED_START_PATTERN.search(recipe_json)
    top_level = (
        recipe_json[:nested_start.start()] if nested_start else recipe_json
    )

    fields = {}
    for field, pattern in STRING_FIELD_PATTERNS.items():
        match = pattern.search(top_level)
        fields[field] = unescape_json_string(match.group(1)) if match else None

    canonical = CANONICAL_PATTERN.search(page)
    url = canonical.group(1) if canonical else None
    id_match = RECIPE_ID_PATTERN.search(url) if url else None

    ingredients = []
    ingredients_match = INGREDIENTS_PATTERN.search(top_level)
    if ingredients_match:
        ingredients = [
            unescape_json_string(item)
            for item in STRING_LITERAL_PATTERN.findall(
                ingredients_match.group(1)
            )
        ]

    instructions = [
        unescape_json_string(step) for step in STEP_PATTERN.findall(top_level)
    ]

    rating = RATING_PATTERN.search(top_level)
    calories = CALORIES_PATTERN.search(top_level)

    keywords = [
        keyword.strip()
        for keyword in (fields["keywords"] or "").split(",")
        if keyword.strip()
    ]

    ingredient_entities = []
    for line in ingredients:
        entity = normalize_ingredient(line)
        if entity and entity not in ingredient_entities:
            ingredient_entities.append(entity)

    return {
        "id": id_match.group(1) if id_match else None,
        "url": url,
        "name": fields["name"],
        "author": fields["author"],
        "description": fields["description"],
        "category": fields["recipeCategory"],
        "keywords": keywords,
        "ingredients": ingredients,
        "ingredient_entities": ingredient_entities,
        "instructions": instructions,
        "prep_minutes": parse_duration_minutes(fields["prepTime"]),
        "cook_minutes": parse_duration_minutes(fields["cookTime"]),
        "total_minutes": parse_duration_minutes(fields["totalTime"]),
        "servings": fields["recipeYield"],
        "date_published": fields["datePublished"],
        "rating": float(rating.group(1)) if rating else None,
        "review_count": int(rating.group(2)) if rating else 0,
        "calories": float(calories.group(1)) if calories else None,
    }
