# je spoločné nastavenie Sparku pre všetky joby. Robí tri veci:

# 1. Spustenie. Keď job spustím lokálne, nastaví local[*], teda všetky jadrá môjho počítača, a 4 GB pamäte. Keď ho spustí spark-submit na klastri, nič z toho nenastaví a nechá to na klaster, inak by všetko bežalo len na jednom stroji.

# 2. Partície po 32 MB. Predvolených 128 MB by dalo len ~7 partícií, takže by časť jadier stála. Takto ich je ~27 pre HTML a 22 pre dump, 2–3 na jadro.

# 3. Cesta k dátam. Predvolene je to priečinok data/, na klastri sa cez premennú VINF_DATA nastaví HDFS. Kód sa nemení, mení sa len cesta.

import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = os.environ.get("VINF_DATA", str(PROJECT_ROOT / "data")).rstrip("/")


def data_path(relative):
    """Path inside the data directory: data_path("spark/wiki")."""

    return f"{DATA_DIR}/{relative}"


def is_local_path(path):
    return "://" not in path or path.startswith("file://")


def submitted_by_spark_submit():
    # spark-submit starts the Python driver with these variables set.
    return "PYSPARK_GATEWAY_PORT" in os.environ


def create_spark(app_name): # rozdeli data na particii, max 128mb/jadro. pri 32 mb = 27 particii +- 2-3 na jadro
    builder = (
        SparkSession.builder
        .appName(app_name)
       
        .config("spark.files.maxPartitionBytes", "32m") # data stiahnute
 
        .config("spark.sql.files.maxPartitionBytes", "32m") # wikipedia 
        .config("spark.ui.showConsoleProgress", "false")
    )

    if not submitted_by_spark_submit(): # ak bezi na mojom pocitaci 
        
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(PROJECT_ROOT), os.environ.get("PYTHONPATH")]) # prida priecinok projektu do zoznamu kde python hlada moduly
        )
        builder = builder.master("local[*]").config("spark.driver.memory", "4g")

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def write_text(spark, path, text):
    """Save a small text result (stats, plan) locally or to HDFS."""

    if is_local_path(path):
        local = Path(path.replace("file://", ""))
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
    else:
        # On HDFS the result is a directory with one part file.
        spark.createDataFrame([(text,)], ["value"]).coalesce(1) \
             .write.mode("overwrite").text(path)
