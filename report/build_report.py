"""Build the DokuWiki report from the template and the real project outputs.

Code snippets, examples, statistics and the IDF comparison are taken from
the actual files, so the wiki always matches the code and the data.

Usage (from the project root, after extractor, indexer, compare and stats):
    python3 -m report.build_report
Output:
    report/wiki_report.txt  – paste into the wiki page
"""

import csv
import inspect
import json
import re
import subprocess
from collections import Counter
import sys
from datetime import datetime
from pathlib import Path

from extractor import extractor
from indexer import search

REPORT_DIR = Path("report")
TEMPLATE_PATH = REPORT_DIR / "wiki_template.txt"
SUMMARY_PATH = REPORT_DIR / "idf_summary.txt"
OUTPUT_PATH = REPORT_DIR / "wiki_report.txt"
MAIN_TEMPLATE_PATH = REPORT_DIR / "wiki_main_page_template.txt"
MAIN_OUTPUT_PATH = REPORT_DIR / "wiki_main_page.txt"
COMBINED_OUTPUT_PATH = REPORT_DIR / "wiki_complete.txt"
PLAN_LINK_PATH = REPORT_DIR / "architecture_plan_link.txt"
ZIP_NAME = "vinf_kolesnykova_kod.zip"

# One example recipe from each of these listing categories, so the examples
# show the variety of the balanced dataset.
EXAMPLE_CATEGORIES = ["123", "C", "M", "S", "V"]


def markdown_to_dokuwiki(markdown):
    """Convert the simple Markdown written by compare.py and stats.py."""

    converted = []
    source_lines = markdown.splitlines()
    for position, line in enumerate(source_lines):
        if line.startswith("# "):
            continue
        if re.fullmatch(r"\|[-:| ]+\|", line):
            continue
        line = re.sub(r"`([^`]*)`", r"''\1''", line)
        if line.startswith("## "):
            converted.append(f"==== {line[3:]} ====")
            continue
        is_header = (
            line.startswith("|")
            and position + 1 < len(source_lines)
            and re.fullmatch(r"\|[-:| ]+\|", source_lines[position + 1])
        )
        if is_header:
            line = "^" + line[1:-1].replace("|", "^") + "^"
        converted.append(line)
    return "\n".join(converted).strip()


def cell(value):
    return str(value).replace("|", "/").replace("^", "")


def examples():
    with open("metadata/recipe_urls.tsv", encoding="utf-8") as urls_file:
        url_categories = {row["url"]: row["category"] for row in
                          csv.DictReader(urls_file, delimiter="\t")}

    # The first complete recipe (rating, 5+ ingredients) of each category.
    chosen = {}
    with open("data/recipes.jsonl", encoding="utf-8") as recipes_file:
        for line in recipes_file:
            recipe = json.loads(line)
            category = url_categories.get(recipe["url"])
            if (
                category in EXAMPLE_CATEGORIES
                and category not in chosen
                and recipe["rating"] is not None
                and len(recipe["ingredients"]) >= 5
                and recipe["instructions"]
            ):
                chosen[category] = recipe
    selected = [chosen[c] for c in EXAMPLE_CATEGORIES if c in chosen]

    blocks = []
    for number, recipe in enumerate(selected, start=1):
        rows = [
            ("id", recipe["id"]),
            ("url", recipe["url"]),
            ("name", recipe["name"]),
            ("author", recipe["author"]),
            ("category", recipe["category"]),
            ("keywords", ", ".join(recipe["keywords"])),
            ("ingredient_entities", ", ".join(recipe["ingredient_entities"])),
            ("ingredients (1. riadok)", recipe["ingredients"][0]),
            ("instructions", f"{len(recipe['instructions'])} krokov, 1.: "
                             f"{recipe['instructions'][0]}"),
            ("prep / cook / total", f"{recipe['prep_minutes']} / "
                                    f"{recipe['cook_minutes']} / "
                                    f"{recipe['total_minutes']} min"),
            ("servings", recipe["servings"]),
            ("rating / review_count", f"{recipe['rating']} / "
                                      f"{recipe['review_count']}"),
            ("calories", recipe["calories"]),
        ]
        block = [f"**Ukážka {number}: {cell(recipe['name'])}**", "",
                 "^ pole ^ extrahovaná hodnota ^"]
        block += [f"| ''{name}'' | {cell(value)} |" for name, value in rows]
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def metadata_sample():
    with open("metadata/downloads.tsv", encoding="utf-8") as metadata_file:
        rows = list(csv.reader(metadata_file, delimiter="\t"))
    header, body = rows[0], rows[1:]
    sample = [row for row in body if row[3] == "200"][:5]
    sample += [row for row in body if row[3] != "200"][:2]
    lines = ["^ " + " ^ ".join(header) + " ^"]
    lines += ["| " + " | ".join(cell(v) or " " for v in row) + " |"
              for row in sample]
    return "\n".join(lines)


def lines_between(path, start_marker, end_marker):
    """Return source lines from start_marker to end_marker (inclusive)."""

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if start_marker in line)
    end = next(i for i in range(start, len(lines)) if end_marker in lines[i])
    snippet = lines[start:end + 1]
    indent = min(len(l) - len(l.lstrip()) for l in snippet if l.strip())
    return "\n".join(l[indent:] for l in snippet), start + 1


def download_hours():
    files = [p.stat().st_mtime for p in Path("data/html").glob("*.html")]
    recent = sorted(t for t in files if t > datetime(2026, 10, 18).timestamp())
    if len(recent) < 2:
        return "?"
    return f"{(recent[-1] - recent[0]) / 3600:.1f}"


def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "tests", "-v"],
        capture_output=True, text=True
    )
    output = result.stderr.strip()
    count = re.search(r"Ran (\d+) tests", output)
    return output, count.group(1) if count else "?"


def main():
    url_code, url_line = lines_between(
        "crawler/crawler.py", "# Extract recipe URLs.", "dict.fromkeys"
    )
    url_code += "\n    )"
    patterns_code, _ = lines_between(
        "extractor/extractor.py", "# One JSON string literal",
        "STRING_LITERAL_PATTERN ="
    )
    idf_code = "\n\n\n".join(
        inspect.getsource(function)
        for function in [search.idf_classic, search.idf_bm25, search.search]
    )

    with open("metadata/downloads.tsv", encoding="utf-8") as metadata_file:
        attempted = {row["url"] for row in
                     csv.DictReader(metadata_file, delimiter="\t")}
    with open("metadata/recipe_urls.tsv", encoding="utf-8") as urls_file:
        url_categories = {row["url"]: row["category"] for row in
                          csv.DictReader(urls_file, delimiter="\t")}
    attempted_categories = Counter(url_categories.get(url) for url in attempted)
    by_count = {}
    for category, count in sorted(attempted_categories.items()):
        by_count.setdefault(count, []).append(category)
    download_scope = ", ".join(
        f"''{categories[0]}'': {count}" if len(categories) == 1
        else f"{len(categories)} kategórií po {count}"
        for count, categories in sorted(by_count.items(), reverse=True)
    )
    html_size = sum(p.stat().st_size for p in Path("data/html").glob("*.html"))

    test_output, test_count = run_tests()
    summary = (
        SUMMARY_PATH.read_text(encoding="utf-8").strip()
        if SUMMARY_PATH.exists() else "//(doplniť)//"
    )

    values = {
        "ZIP_LINK": f"{{{{:user:maryna.kolesnykova:{ZIP_NAME}|ZIP s kódom}}}}",
        "TEST_COUNT": test_count,
        "TEST_OUTPUT": test_output,
        "EXAMPLES": examples(),
        "METADATA": metadata_sample(),
        "DOWNLOAD_COUNT": str(len(attempted)),
        "DISCOVERED_COUNT": str(len(url_categories)),
        "DOWNLOAD_SCOPE": download_scope,
        "HTML_SIZE": f"{html_size / (1024 * 1024):.0f} MB",
        "DOWNLOAD_HOURS": download_hours(),
        "URL_CODE": url_code,
        "URL_CODE_LINE": str(url_line),
        "PATTERNS_CODE": patterns_code,
        "NORMALIZE_CODE": inspect.getsource(extractor.normalize_ingredient),
        "EXTRACT_CODE": inspect.getsource(extractor.extract_recipe),
        "IDF_CODE": idf_code,
        "IDF_COMPARISON": markdown_to_dokuwiki(
            Path("metadata/idf_comparison.md").read_text(encoding="utf-8")
        ),
        "IDF_SUMMARY": summary,
        "STATS": markdown_to_dokuwiki(
            Path("metadata/stats.md").read_text(encoding="utf-8")
        ),
    }

    report = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in values.items():
        report = report.replace("{{" + key + "}}", value.strip("\n"))

    missing = re.findall(r"\{\{([A-Z_]+)\}\}", report)
    if missing:
        print(f"WARNING: unfilled placeholders: {missing}")

    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Saved to: {OUTPUT_PATH}")

    # The project's main wiki page shares the crawl numbers.
    statuses = Counter()
    with open("metadata/downloads.tsv", encoding="utf-8") as metadata_file:
        for row in csv.DictReader(metadata_file, delimiter="\t"):
            statuses[row["status_code"]] = statuses[row["status_code"]] + 1
    with open("data/recipes.jsonl", encoding="utf-8") as recipes_file:
        recipe_count = sum(1 for line in recipes_file if line.strip())
    main_values = {
        "PLAN_LINK": PLAN_LINK_PATH.read_text(encoding="utf-8").strip(),
        "DISCOVERED": str(len(url_categories)),
        "OK": str(statuses["200"]),
        "NOT_FOUND": str(statuses["404"]),
        "SIZE": f"{html_size / (1024 * 1024):.1f} MB",
        "RECIPES": str(recipe_count),
    }
    main_page = MAIN_TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in main_values.items():
        main_page = main_page.replace("{{" + key + "}}", value)
    MAIN_OUTPUT_PATH.write_text(main_page, encoding="utf-8")
    print(f"Saved to: {MAIN_OUTPUT_PATH}")

    # One page: the project proposal followed by the part 1 submission.
    # Links between the two separate pages become references within the page.
    submission_link = "[[:user:maryna.kolesnykova:odovzdanie1|"
    proposal = "\n".join(
        line for line in main_page.splitlines()
        if submission_link + "Odovzdanie 1. časti –" not in line
    )
    proposal = proposal.replace(
        submission_link + "odovzdaní 1. časti]]",
        "časti //Odovzdanie 1. časti projektu// nižšie"
    )
    submission = report.replace(
        "====== Vyhľadávač receptov z Food.com – 1. časť projektu ======",
        "====== Odovzdanie 1. časti projektu (28. 10. 2026) ======"
    ).replace(
        " Podrobná motivácia a návrh projektu sú na stránke "
        "[[:user:maryna.kolesnykova|Recipe Search System]].",
        " Podrobná motivácia, zdroje dát a návrh projektu sú opísané vyššie."
    )
    leftover = [line for line in (proposal + submission).splitlines()
                if "odovzdanie1" in line or "|Recipe Search System]]" in line]
    if leftover:
        print(f"WARNING: links between pages left: {leftover}")
    COMBINED_OUTPUT_PATH.write_text(
        proposal.rstrip() + "\n\n----\n\n" + submission, encoding="utf-8"
    )
    print(f"Saved to: {COMBINED_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
