#!/bin/sh
# Priebeh bežiaceho Spark jobu v Dockeri, obnovuje sa každých 5 s (Ctrl+C koniec).
# Číta Spark UI (port 4040) vnútri kontajnera, preto port netreba zverejňovať.
while true; do
    CONTAINER=$(docker ps --filter "ancestor=vinf-recipes-spark" --format '{{.Names}}' | head -1)
    if [ -z "$CONTAINER" ]; then
        echo "Žiadny Spark job nebeží."
        exit 0
    fi
    docker exec "$CONTAINER" python3 -c '
import json, urllib.request
api = "http://localhost:4040/api/v1/applications"
try:
    app = json.load(urllib.request.urlopen(api))[0]["id"]
    stages = json.load(urllib.request.urlopen(f"{api}/{app}/stages?status=active"))
except Exception:
    print("Spark sa ešte spúšťa...")
    raise SystemExit
for s in stages:
    done, total = s["numCompleteTasks"], s["numTasks"]
    bar = "#" * (30 * done // total) + "." * (30 - 30 * done // total)
    stage, name = s["stageId"], s["name"][:40]
    print(f"stage {stage}: [{bar}] {done}/{total} úloh  {name}")
if not stages:
    print("Medzi fázami...")
'
    sleep 5
done
