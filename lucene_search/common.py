"""What the indexer and the searcher share: the JVM, the index folder and
the analyzer. Both must use the same analyzer, otherwise a query word would
not match the indexed form of the same word (as with the own tokenizer).
"""

import lucene
from org.apache.lucene.analysis.en import EnglishAnalyzer

INDEX_DIR = "data/lucene"


def start_jvm():
    """PyLucene runs Lucene (Java) inside Python, the JVM is started once."""

    if not lucene.getVMEnv():
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])


def create_analyzer():
    """EnglishAnalyzer: lowercase, English stopwords and stemming.

    "Tomatoes" and "tomato" both become "tomato", so one finds the other.
    The own index of part 1 had no stemming.
    """

    return EnglishAnalyzer()
