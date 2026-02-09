#!/usr/bin/env bash
set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────
COMPOSE_FILE="docker-compose.yml"
DB_SERVICE="db"

# Read DB credentials from .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
fi

DB_USER="${POSTGRES_USER:-crossfit}"
DB_NAME="${POSTGRES_DB:-crossfit_tracker}"

BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RESET='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────
run_sql() {
    docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" exec -T "$DB_SERVICE" \
        psql -U "$DB_USER" -d "$DB_NAME" -t -A -F '|' -c "$1" 2>/dev/null
}

header() {
    echo -e "\n${BOLD}${CYAN}── $1 ──${RESET}"
}

row() {
    printf "  %-30s %s\n" "$1" "$2"
}

# ─── Summary (default) ───────────────────────────────────────────────
show_summary() {
    header "Resumen del sistema"

    local users lifts skills benchmarks results
    users=$(run_sql "SELECT COUNT(*) FROM users")
    lifts=$(run_sql "SELECT COUNT(*) FROM lifts")
    skills=$(run_sql "SELECT COUNT(*) FROM user_skills")
    benchmarks=$(run_sql "SELECT COUNT(*) FROM benchmarks")
    results=$(run_sql "SELECT COUNT(*) FROM benchmark_results")

    row "Usuarios"            "$users"
    row "Marcas registradas"  "$lifts"
    row "Skills desbloqueados" "$skills"
    row "Benchmarks"           "$benchmarks"
    row "Resultados benchmark" "$results"

    header "Marcas por ejercicio"
    run_sql "
        SELECT e.name, COUNT(l.id)
        FROM exercises e
        LEFT JOIN lifts l ON l.exercise_id = e.id
        GROUP BY e.name
        ORDER BY COUNT(l.id) DESC
    " | while IFS='|' read -r name count; do
        row "$name" "$count"
    done

    header "Top benchmarks (mas resultados)"
    run_sql "
        SELECT b.name, COUNT(r.id)
        FROM benchmarks b
        LEFT JOIN benchmark_results r ON r.benchmark_id = b.id
        GROUP BY b.name
        HAVING COUNT(r.id) > 0
        ORDER BY COUNT(r.id) DESC
        LIMIT 10
    " | while IFS='|' read -r name count; do
        row "$name" "$count"
    done

    header "Ultimo registro"
    local last
    last=$(run_sql "
        SELECT u.username, e.name, l.weight, l.reps_type, l.date
        FROM lifts l
        JOIN users u ON u.id = l.user_id
        JOIN exercises e ON e.id = l.exercise_id
        ORDER BY l.created_at DESC
        LIMIT 1
    ")
    if [[ -n "$last" ]]; then
        IFS='|' read -r user ex weight reps dt <<< "$last"
        row "Usuario"   "$user"
        row "Ejercicio" "$ex"
        row "Peso"      "${weight}kg (${reps}RM)"
        row "Fecha"     "$dt"
    else
        echo -e "  ${DIM}Sin registros${RESET}"
    fi
}

# ─── Detail (--detail) ───────────────────────────────────────────────
show_detail() {
    show_summary

    header "Detalle por usuario"

    run_sql "SELECT id, username, email, created_at FROM users ORDER BY id" |
    while IFS='|' read -r uid uname email created; do
        echo ""
        echo -e "  ${BOLD}${GREEN}$uname${RESET} ${DIM}($email - desde $created)${RESET}"

        # Lifts
        local lift_count
        lift_count=$(run_sql "SELECT COUNT(*) FROM lifts WHERE user_id = $uid")
        echo -e "    ${YELLOW}Marcas:${RESET} $lift_count"
        if [[ "$lift_count" -gt 0 ]]; then
            run_sql "
                SELECT e.name, l.weight, l.reps_type, l.date
                FROM lifts l
                JOIN exercises e ON e.id = l.exercise_id
                WHERE l.user_id = $uid
                ORDER BY l.date DESC
                LIMIT 10
            " | while IFS='|' read -r ex weight reps dt; do
                printf "      %-22s %skg  %sRM  (%s)\n" "$ex" "$weight" "$reps" "$dt"
            done
            if [[ "$lift_count" -gt 10 ]]; then
                echo -e "      ${DIM}... y $((lift_count - 10)) mas${RESET}"
            fi
        fi

        # Skills
        local skill_count
        skill_count=$(run_sql "SELECT COUNT(*) FROM user_skills WHERE user_id = $uid")
        echo -e "    ${YELLOW}Skills desbloqueados:${RESET} $skill_count"
        if [[ "$skill_count" -gt 0 ]]; then
            run_sql "
                SELECT s.name, us.unlocked_date
                FROM user_skills us
                JOIN skills s ON s.id = us.skill_id
                WHERE us.user_id = $uid
                ORDER BY us.unlocked_date DESC
            " | while IFS='|' read -r sname sdate; do
                printf "      %-22s (%s)\n" "$sname" "$sdate"
            done
        fi

        # Benchmark results
        local bench_count
        bench_count=$(run_sql "SELECT COUNT(*) FROM benchmark_results WHERE user_id = $uid")
        echo -e "    ${YELLOW}Benchmarks:${RESET} $bench_count"
        if [[ "$bench_count" -gt 0 ]]; then
            run_sql "
                SELECT b.name, b.benchmark_type,
                       br.time_seconds, br.rounds, br.reps,
                       CASE WHEN br.rx THEN 'Rx' ELSE 'Scaled' END,
                       br.date
                FROM benchmark_results br
                JOIN benchmarks b ON b.id = br.benchmark_id
                WHERE br.user_id = $uid
                ORDER BY br.date DESC
                LIMIT 10
            " | while IFS='|' read -r bname btype tsec rounds reps rx bdate; do
                local result=""
                if [[ "$btype" == "for_time" && -n "$tsec" ]]; then
                    local mins=$((tsec / 60))
                    local secs=$((tsec % 60))
                    result=$(printf "%d:%02d" "$mins" "$secs")
                elif [[ "$btype" == "amrap" ]]; then
                    result="${rounds}r+${reps}reps"
                fi
                printf "      %-15s %-8s %-6s (%s)\n" "$bname" "$result" "$rx" "$bdate"
            done
            if [[ "$bench_count" -gt 10 ]]; then
                echo -e "      ${DIM}... y $((bench_count - 10)) mas${RESET}"
            fi
        fi
    done
}

# ─── Main ─────────────────────────────────────────────────────────────
usage() {
    echo "Uso: $0 [--detail]"
    echo ""
    echo "  (sin args)   Resumen general del sistema"
    echo "  --detail     Resumen + listado por usuario con sus registros"
    exit 0
}

case "${1:-}" in
    --detail) show_detail ;;
    --help|-h) usage ;;
    "") show_summary ;;
    *) echo "Opcion desconocida: $1"; usage ;;
esac

echo ""
