"""Shared Spark setup for all Spark jobs.

Locally (python3 -m spark_jobs.<job>) the jobs run on a local Spark
"cluster": master local[*] starts one worker thread per CPU core.

On a cluster the same code is started with spark-submit, which decides the
master itself, for example the UISAV cluster:

    spark-submit --master mesos://147.213.75.180:5050 \
        --conf spark.executor.uri=hdfs://147.213.75.180:8020/user/hadmin/spark-3.4.0-bin-hadoop3.tgz \
        --py-files code.zip spark_jobs/wiki_parse.py

Then nothing local is forced here (master, Python, memory), otherwise the
job would ignore the cluster and run only on one computer.

Data location: data/ of the project by default, or the directory in the
environment variable VINF_DATA, for example VINF_DATA=hdfs:///user/me/data.
The code works with Spark 3.4 (UISAV cluster) and newer.
"""

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


def create_spark(app_name):
    builder = (
        SparkSession.builder
        .appName(app_name)
        # Files are read in partitions of at most 32 MB, so the 837 MB of
        # HTML is split into ~30 tasks and every core gets work.
        .config("spark.files.maxPartitionBytes", "32m")
        # The same for DataFrame readers: the bz2 Wikipedia dump is split
        # into 32 MB parts (bz2 is splittable), so all cores read it.
        .config("spark.sql.files.maxPartitionBytes", "32m")
        .config("spark.ui.showConsoleProgress", "false")
    )

    if not submitted_by_spark_submit():
        # Spark starts separate Python worker processes. They must use the
        # same Python and must be able to import the project's own modules
        # (extractor, indexer). On a cluster --py-files does this instead.
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(PROJECT_ROOT), os.environ.get("PYTHONPATH")])
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
