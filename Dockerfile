# Spark joby projektu v Dockeri.
# Spark 3.4 je rovnaký ako na klastri UISAV, takže čo beží tu, beží aj tam.
FROM apache/spark:3.4.4-python3

WORKDIR /app

# Len kód, dáta sa pripájajú ako zväzok (docker-compose.yml).
COPY spark_jobs/ spark_jobs/
COPY extractor/ extractor/
COPY indexer/ indexer/
COPY docker/run_job.sh /usr/local/bin/run_job

# Python workery Sparku musia nájsť balík spark_jobs.
ENV PYTHONPATH=/app \
    VINF_DATA=/app/data \
    DRIVER_MEMORY=4g

ENTRYPOINT ["run_job"]
CMD ["--help"]
