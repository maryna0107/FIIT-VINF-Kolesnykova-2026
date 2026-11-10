#!/bin/sh
# Spustí jeden Spark job: run_job <job> [argumenty]
# Príklad: run_job wiki_parse "/app/data/wiki_full/*.bz2"
set -e

if [ -z "$1" ] || [ "$1" = "--help" ]; then
    echo "Použitie: run_job <job> [argumenty]"
    echo "Joby:" $(ls /app/spark_jobs | grep -E '\.py$' | grep -vE '^(__init__|session|wiki_regex)\.py$' | sed 's/\.py$//')
    exit 0
fi

JOB="$1"
shift

# spark-submit nastaví PYSPARK_GATEWAY_PORT, preto session.py master nenastaví.
# V kontajneri ho treba dať tu: local[*] = všetky jadrá pridelené Dockeru.
exec /opt/spark/bin/spark-submit \
    --master "local[*]" \
    --driver-memory "$DRIVER_MEMORY" \
    "/app/spark_jobs/$JOB.py" "$@"
