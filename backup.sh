#!/usr/bin/env bash
set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────
COMPOSE_FILE="docker-compose.yml"
DB_SERVICE="db"
BACKUP_DIR="backups"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
fi

DB_USER="${POSTGRES_USER:-crossfit}"
DB_NAME="${POSTGRES_DB:-crossfit_tracker}"

BOLD='\033[1m'
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────
ok()   { echo -e "${GREEN}[OK]${RESET} $1"; }
err()  { echo -e "${RED}[ERROR]${RESET} $1" >&2; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $1"; }

check_container() {
    if ! docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" ps --status running "$DB_SERVICE" 2>/dev/null | grep -q "$DB_SERVICE"; then
        err "El contenedor '$DB_SERVICE' no esta corriendo. Ejecuta: docker compose up -d"
        exit 1
    fi
}

# ─── Export ───────────────────────────────────────────────────────────
do_export() {
    check_container

    mkdir -p "$SCRIPT_DIR/$BACKUP_DIR"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local filename="backup_${DB_NAME}_${timestamp}.sql.gz"
    local filepath="$SCRIPT_DIR/$BACKUP_DIR/$filename"

    echo -e "${BOLD}Exportando base de datos '${DB_NAME}'...${RESET}"

    docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
        pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges \
        | gzip > "$filepath"

    if [[ -s "$filepath" ]]; then
        local size
        size=$(du -h "$filepath" | cut -f1)
        ok "Backup guardado: $BACKUP_DIR/$filename ($size)"
    else
        rm -f "$filepath"
        err "El backup esta vacio, algo fallo."
        exit 1
    fi
}

# ─── Import ───────────────────────────────────────────────────────────
do_import() {
    local file="${1:-}"

    if [[ -z "$file" ]]; then
        err "Debes especificar el archivo: $0 import <archivo.sql.gz>"
        echo ""
        list_backups
        exit 1
    fi

    # Resolve relative paths from backup dir
    if [[ ! -f "$file" && -f "$SCRIPT_DIR/$BACKUP_DIR/$file" ]]; then
        file="$SCRIPT_DIR/$BACKUP_DIR/$file"
    fi

    if [[ ! -f "$file" ]]; then
        err "Archivo no encontrado: $file"
        exit 1
    fi

    check_container

    echo -e "${BOLD}Importando '$(basename "$file")' a '${DB_NAME}'...${RESET}"
    warn "Esto sobreescribira los datos actuales de la base de datos."
    read -rp "Continuar? (s/N): " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
        echo "Cancelado."
        exit 0
    fi

    if [[ "$file" == *.gz ]]; then
        gunzip -c "$file" | docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
            psql -U "$DB_USER" -d "$DB_NAME" --quiet --single-transaction 2>&1 | tail -1
    else
        docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
            psql -U "$DB_USER" -d "$DB_NAME" --quiet --single-transaction < "$file" 2>&1 | tail -1
    fi

    ok "Importacion completada."
}

# ─── List ─────────────────────────────────────────────────────────────
list_backups() {
    local dir="$SCRIPT_DIR/$BACKUP_DIR"
    if [[ ! -d "$dir" ]] || [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]; then
        echo "No hay backups disponibles."
        return
    fi

    echo -e "${BOLD}Backups disponibles:${RESET}"
    echo ""
    ls -lhtr "$dir"/*.sql* 2>/dev/null | while read -r line; do
        echo "  $line"
    done
    echo ""
}

# ─── Main ─────────────────────────────────────────────────────────────
usage() {
    echo "Uso: $0 <comando> [opciones]"
    echo ""
    echo "Comandos:"
    echo "  export              Exporta la base de datos a backups/"
    echo "  import <archivo>    Importa un backup (acepta .sql y .sql.gz)"
    echo "  list                Lista los backups disponibles"
    echo ""
    echo "Ejemplos:"
    echo "  $0 export"
    echo "  $0 list"
    echo "  $0 import backup_crossfit_tracker_20260209_120000.sql.gz"
    exit 0
}

case "${1:-}" in
    export)  do_export ;;
    import)  do_import "${2:-}" ;;
    list)    list_backups ;;
    --help|-h) usage ;;
    "")      usage ;;
    *)       err "Comando desconocido: $1"; usage ;;
esac
