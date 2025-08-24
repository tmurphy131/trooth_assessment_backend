#!/usr/bin/env bash
set -euo pipefail

# Build image for local smoke test
IMAGE_TAG=trooth-backend:smoke
docker build -t "$IMAGE_TAG" .

# Run container (use a random free port)
PORT=8001
CONTAINER_ID=$(docker run -d -p ${PORT}:8000 -e ENV=test -e DATABASE_URL="sqlite+pysqlite:///:memory:" "$IMAGE_TAG")

echo "Waiting for container to start..."
for i in {1..12}; do
  if curl -s "http://localhost:${PORT}/health" >/dev/null; then
    echo "health OK"
    docker kill "$CONTAINER_ID" >/dev/null || true
    exit 0
  fi
  sleep 1
done

echo "Smoke test failed: /health did not respond"
docker logs "$CONTAINER_ID" || true
docker kill "$CONTAINER_ID" >/dev/null || true
exit 1
