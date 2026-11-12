#!/usr/bin/env bash
set -e

URL="${1:-http://localhost:5000}"

echo "1. Checking GET /"
curl -fsS "$URL/"
echo ""

echo "2. Checking GET /healthz"
curl -fsS "$URL/healthz"
echo ""

echo "3. Testing POST /data"
curl -fsS -X POST -H "Content-Type: application/json" -d '{"msg":"hello"}' "$URL/data"
echo ""

echo "4. Testing GET /data"
curl -fsS "$URL/data"
echo ""

echo "All tests passed."
