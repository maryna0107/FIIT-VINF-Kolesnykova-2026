import lucene
from org.apache.lucene.analysis.en import EnglishAnalyzer

INDEX_DIR = "data/lucene"


def start_jvm():
    """PyLucene runs Lucene (Java) inside Python, the JVM is started once."""

    if not lucene.getVMEnv():
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])


def create_analyzer():
 

    return EnglishAnalyzer()
