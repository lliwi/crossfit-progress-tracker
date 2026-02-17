#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
DB_SERVICE="db"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
fi

DB_USER="${POSTGRES_USER:-crossfit}"
DB_NAME="${POSTGRES_DB:-crossfit_tracker}"
BASE="${BASE_URL:-http://localhost:5000}"

run_sql() {
    docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
        psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "$1" 2>/dev/null
}

# Generate a random token (44 chars, url-safe base64)
TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Insert as a system invitation (created_by = NULL)
run_sql "INSERT INTO invitations (token, created_by, created_at) VALUES ('${TOKEN}', NULL, NOW())"

echo ""
echo "Invitacion generada. Comparte este link:"
echo ""
echo "  ${BASE}/auth/register?token=${TOKEN}"
echo ""
