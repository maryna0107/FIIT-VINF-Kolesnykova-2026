import time

# lucene first: it makes the Java packages (java.*, org.apache.*) importable.
import lucene  
from java.nio.file import Paths
from org.apache.lucene.document import (
    DoublePoint, Document, Field, IntPoint, StoredField, StringField, TextField,
)
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import FSDirectory

from lucene_search.common import INDEX_DIR, create_analyzer, start_jvm
from spark_jobs.wiki_show import load_recipes


def add_text(document, name, values, stored=False):
    """One TextField per value. A field can have several values (a list)."""

    store = Field.Store.YES if stored else Field.Store.NO
    for value in values:
        if value:
            document.add(TextField(name, value, store))


def add_number(document, name, value, whole_number):
    """A Point for range search and a StoredField to show the value."""

    if value is None:
        return
    if whole_number:
        document.add(IntPoint(name, int(value)))
        document.add(StoredField(name, int(value)))
    else:
        document.add(DoublePoint(name, float(value)))
        document.add(StoredField(name, float(value)))


def recipe_document(recipe):
    dish = recipe.get("wiki_dish") or {}
    cuisines = recipe.get("wiki_cuisines") or []
    wiki_ingredients = recipe.get("wiki_ingredients") or []

    document = Document()
    document.add(StringField("id", recipe["id"], Field.Store.YES))
    add_text(document, "name", [recipe["name"]], stored=True)
    add_text(document, "ingredient", recipe["ingredient_entities"]
             + [page["title"] for page in wiki_ingredients])
    add_text(document, "category", [recipe["category"]], stored=True)
    add_text(document, "keywords", recipe["keywords"])
    add_text(document, "description", [recipe["description"]])
    add_text(document, "instructions", recipe["instructions"])
    add_text(document, "wiki_dish", [dish.get("title"), dish.get("abstract")])
    add_text(document, "cuisine", [page["title"] for page in cuisines]
             + [dish.get("country"), dish.get("region")])
    add_number(document, "minutes", recipe["total_minutes"], whole_number=True)
    add_number(document, "calories", recipe["calories"], whole_number=False)
    add_number(document, "rating", recipe["rating"], whole_number=False)
    return document


def main():
    start_jvm()
    started = time.time()
    config = IndexWriterConfig(create_analyzer())
    # CREATE: a new index every time, old documents are not kept twice.
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    writer = IndexWriter(FSDirectory.open(Paths.get(INDEX_DIR)), config)

    count = 0
    for recipe in load_recipes():
        writer.addDocument(recipe_document(recipe))
        count += 1
    writer.commit()
    writer.close()

    print(f"Indexed recipes: {count}")
    print(f"Seconds:         {time.time() - started:.1f}")
    print(f"Saved to:        {INDEX_DIR}")


if __name__ == "__main__":
    main()
