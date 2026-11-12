#!/usr/bin/env bash
set -e

TARGET_URL="${1:-http://localhost:5000}"
CONCURRENCY="${2:-10}"
TOTAL="${3:-1000}"

echo "Running load test against $TARGET_URL..."

for i in $(seq 1 "$CONCURRENCY"); do
    (
        for j in $(seq 1 "$((TOTAL / CONCURRENCY))"); do
            if [ $((j % 2)) -eq 0 ]; then
                curl -s -X POST -H "Content-Type: application/json" \
                     -d "{\"k\": \"test-$j\", \"v\": $j}" "$TARGET_URL/data" > /dev/null
            else
                curl -s "$TARGET_URL/data" > /dev/null
            fi
        done
    ) &
done

wait
echo "Done."
