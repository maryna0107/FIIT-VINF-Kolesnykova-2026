"""Tokenization shared by the indexer and the searcher.

The same function must be used for documents and for queries, otherwise
a query word would never match the indexed form of the same word.
"""

import re

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Very common English words that carry no meaning for recipe search.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "if", "in", "into", "is", "it", "its", "of", "on", "or", "so", "that",
    "the", "then", "this", "to", "until", "with", "you", "your", "i", "my",
    "we", "will", "can", "do", "not", "all", "about", "over", "up", "out",
}


def tokenize(text):
    """Lowercase the text and return its tokens without stopwords."""

    return [
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]
