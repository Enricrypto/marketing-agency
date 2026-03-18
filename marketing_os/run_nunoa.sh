#!/usr/bin/env bash
# Marketing OS — Ñuñoa Service Pages Runner
# Generates landing pages and blog posts for the 4 new Ñuñoa services.
# Logs all output to outputs/logs/nunoa_run_<timestamp>.log
#
# Usage:
#   ./run_nunoa.sh              # landing + blog for all services
#   ./run_nunoa.sh --landing    # landing pages only
#   ./run_nunoa.sh --blog       # blog posts only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Activate virtual environment ──────────────────────────────────────────────
if [[ -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

PYTHON="${SCRIPT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="$(command -v python3 || command -v python)"
fi
LOG_DIR="$SCRIPT_DIR/outputs/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/nunoa_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# ── Services and their matching blog keywords ─────────────────────────────────

declare -a SERVICES=(
    "Peluquería canina Ñuñoa"
    "Auto lavado perros Ñuñoa"
    "Peluquería gatos Ñuñoa"
    "Precio peluquería Ñuñoa"
)

declare -a BLOG_TOPICS=(
    "cuidado del pelaje y corte canino en Ñuñoa"
    "cómo lavar a tu perro en casa vs auto lavado en Ñuñoa"
    "cuidado profesional del pelaje de gatos en Ñuñoa"
    "cuánto cuesta una peluquería canina en Ñuñoa"
)

declare -a BLOG_KEYWORDS=(
    "peluquería canina Ñuñoa"
    "auto lavado perros Ñuñoa"
    "peluquería gatos Ñuñoa"
    "precio peluquería canina Ñuñoa"
)

# ── Parse flags ───────────────────────────────────────────────────────────────

RUN_LANDING=true
RUN_BLOG=true
SKIP_SYNC=false

for arg in "$@"; do
    case "$arg" in
        --landing)  RUN_BLOG=false ;;
        --blog)     RUN_LANDING=false ;;
        --no-sync)  SKIP_SYNC=true ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────

log() { echo "$1" | tee -a "$LOG_FILE"; }

run_landing() {
    local service="$1"
    log ""
    log "── LANDING: $service ─────────────────────────────────────"
    if "$PYTHON" "$SCRIPT_DIR/run_workflow.py" landing \
        --service "$service" \
        --location "Ñuñoa" \
        2>&1 | tee -a "$LOG_FILE"; then
        log "[OK] Landing generada: $service"
    else
        log "[ERROR] Falló landing: $service"
    fi
}

run_blog() {
    local topic="$1"
    local keyword="$2"
    log ""
    log "── BLOG: $keyword ────────────────────────────────────────"
    if "$PYTHON" "$SCRIPT_DIR/run_workflow.py" blog \
        --topic "$topic" \
        --keyword "$keyword" \
        --city "Ñuñoa" \
        2>&1 | tee -a "$LOG_FILE"; then
        log "[OK] Blog generado: $keyword"
    else
        log "[ERROR] Falló blog: $keyword"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────

log "======================================================"
log "Marketing OS — Ñuñoa Workflow Runner"
log "Started: $(date)"
log "Log: $LOG_FILE"
log "======================================================"

cd "$SCRIPT_DIR"

LANDING_OK=0
LANDING_FAIL=0
BLOG_OK=0
BLOG_FAIL=0

if $RUN_LANDING; then
    log ""
    log "LANDING PAGES (${#SERVICES[@]} servicios)"
    log "------------------------------------------------------"
    for service in "${SERVICES[@]}"; do
        if run_landing "$service"; then
            ((LANDING_OK++)) || true
        else
            ((LANDING_FAIL++)) || true
        fi
    done
fi

if $RUN_BLOG; then
    log ""
    log "BLOG POSTS (${#BLOG_TOPICS[@]} artículos)"
    log "------------------------------------------------------"
    for i in "${!BLOG_TOPICS[@]}"; do
        if run_blog "${BLOG_TOPICS[$i]}" "${BLOG_KEYWORDS[$i]}"; then
            ((BLOG_OK++)) || true
        else
            ((BLOG_FAIL++)) || true
        fi
    done
fi

# ── Summary ───────────────────────────────────────────────────────────────────

log ""
log "======================================================"
log "RESUMEN"
if $RUN_LANDING; then
    log "  Landings OK    : $LANDING_OK / ${#SERVICES[@]}"
    log "  Landings ERROR : $LANDING_FAIL"
fi
if $RUN_BLOG; then
    log "  Blogs OK       : $BLOG_OK / ${#BLOG_TOPICS[@]}"
    log "  Blogs ERROR    : $BLOG_FAIL"
fi
log "  Log completo   : $LOG_FILE"
log "  Finished: $(date)"
log "======================================================"

# ── Sync to Google Sheets ─────────────────────────────────────────────────────

if ! $SKIP_SYNC; then
    log ""
    log "── SYNC TO GOOGLE SHEETS ──────────────────────────────"
    SYNC_TYPES=()
    $RUN_LANDING && SYNC_TYPES+=("landing")
    $RUN_BLOG    && SYNC_TYPES+=("blog")

    for stype in "${SYNC_TYPES[@]}"; do
        log "  Syncing ${stype}s..."
        if "$PYTHON" "$SCRIPT_DIR/sync_sheets.py" --all --best-only --type "$stype" \
            2>&1 | tee -a "$LOG_FILE"; then
            log "  [OK] ${stype} sync complete"
        else
            log "  [WARN] ${stype} sync failed — check workspace/credentials.json"
        fi
    done
else
    log ""
    log "  [skipped] Sheet sync disabled via --no-sync"
fi
