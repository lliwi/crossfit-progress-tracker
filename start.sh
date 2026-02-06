#!/bin/bash
set -e

echo "==> Building containers..."
docker compose build

echo "==> Starting services..."
docker compose up -d

echo "==> Waiting for database to be ready..."
docker compose exec web flask db migrate -m "Auto migration" 2>/dev/null || true

echo "==> Applying migrations..."
docker compose exec web flask db upgrade

echo "==> Restarting web service..."
docker compose restart web

echo "==> Done! App running at http://localhost:5000"
docker compose logs -f
