#!/bin/bash
# ============================================================
# BlackBugsAI — APK Build Script
# Строит APK локально, через Docker или подсказывает GitHub Actions
# ============================================================

set -Eeuo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="$PROJECT_DIR/android_app"
OUTPUT_DIR="$PROJECT_DIR/release-apks"
DOCKER_FLUTTER_IMAGE="${DOCKER_FLUTTER_IMAGE:-ghcr.io/cirruslabs/flutter:3.24.5}"

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
fail() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

print_header() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════╗"
    echo "║     BlackBugsAI — APK Builder            ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

copy_apks() {
    local src="$1"
    cp "$src/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk" \
        "$OUTPUT_DIR/BlackBugsAI-arm64.apk" 2>/dev/null || true
    cp "$src/build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk" \
        "$OUTPUT_DIR/BlackBugsAI-arm32.apk" 2>/dev/null || true
    cp "$src/build/app/outputs/flutter-apk/app-release.apk" \
        "$OUTPUT_DIR/BlackBugsAI-universal.apk" 2>/dev/null || true
}

show_apks() {
    echo
    echo -e "${CYAN}APK файлы:${NC} $OUTPUT_DIR"
    ls -lh "$OUTPUT_DIR"/*.apk 2>/dev/null || warn "APK пока не найдены"
}

ensure_layout() {
    [[ -d "$APP_DIR" ]] || fail "Не найден каталог android_app: $APP_DIR"
    mkdir -p "$OUTPUT_DIR"
}

verify_output() {
    if ls "$OUTPUT_DIR"/*.apk >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# ── Method 1: Local Flutter ────────────────────────────────────────────────
build_local() {
    echo -e "${YELLOW}[Method 1] Сборка через локальный Flutter...${NC}"

    command -v flutter >/dev/null 2>&1 || return 1
    echo "Flutter version: $(flutter --version 2>&1 | head -1)"

    cd "$APP_DIR"
    flutter clean
    flutter pub get
    flutter build apk --release --split-per-abi

    copy_apks "$APP_DIR"
    verify_output && log "APK собран локально" || return 1
}

# ── Method 2: Docker build ─────────────────────────────────────────────────
build_docker() {
    echo -e "${YELLOW}[Method 2] Сборка через Docker...${NC}"

    command -v docker >/dev/null 2>&1 || return 1
    ensure_layout

    docker pull "$DOCKER_FLUTTER_IMAGE" >/dev/null 2>&1 || warn "Не удалось заранее подтянуть образ, продолжаю"

    docker run --rm --init \
        -v "$APP_DIR:/app" \
        -v "$OUTPUT_DIR:/output" \
        -w /app \
        "$DOCKER_FLUTTER_IMAGE" \
        bash -lc '
            set -Eeuo pipefail
            flutter --version | head -1
            flutter clean
            flutter pub get
            flutter build apk --release --split-per-abi
            cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk /output/BlackBugsAI-arm64.apk 2>/dev/null || true
            cp build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk /output/BlackBugsAI-arm32.apk 2>/dev/null || true
            cp build/app/outputs/flutter-apk/app-release.apk /output/BlackBugsAI-universal.apk 2>/dev/null || true
        '

    verify_output && log "APK собран через Docker" || return 1
}

# ── Method 3: GitHub Actions instructions ─────────────────────────────────
build_github_actions() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  Сборка через GitHub Actions (рекомендуется)             ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "1. Перейди в репозиторий:"
    echo "   https://github.com/bamper0051-cell/Black-WhiteAI"
    echo ""
    echo "2. Actions → Build Android APK → Run workflow"
    echo ""
    echo "3. После завершения скачай APK из:"
    echo "   Actions → последний запуск → Artifacts → BlackBugsAI-APKs"
    echo ""
    echo "Или создай Release:"
    echo "   Actions → Build Android APK → Run workflow → введи тег v1.0.0"
    echo "   APK появится в Releases"
}

select_method() {
    local method="${BUILD_METHOD:-}"

    # If no input and not running interactively, choose auto-fallback mode
    if [[ -z "$method" && ! -t 0 ]]; then
        method="auto"
    fi

    if [[ -z "$method" ]]; then
        echo "Выбери метод сборки:"
        echo "  1) Локальный Flutter (нужен Flutter SDK + Android SDK)"
        echo "  2) Docker (нужен Docker)"
        echo "  3) GitHub Actions (онлайн, без локального SDK)"
        echo "  Enter) Авто: локально → docker → GitHub Actions"
        echo ""
        read -r -p "Метод [1/2/3/Enter=auto]: " method || method=""
    fi

    echo "$method"
}

run_flow() {
    local choice="$1"
    local built=0

    case "${choice,,}" in
        1|"local")
            build_local && built=1 || warn "Локальная сборка недоступна, пробую Docker"
            if [[ $built -eq 0 ]]; then
                build_docker && built=1 || warn "Docker не сработал"
            fi
            ;;
        2|"docker")
            build_docker && built=1 || warn "Docker не сработал"
            ;;
        3|"actions"|"github")
            build_github_actions
            ;;
        auto|"" )
            build_local && built=1 || warn "Локально не удалось, пробую Docker"
            if [[ $built -eq 0 ]]; then
                build_docker && built=1 || warn "Docker не сработал"
            fi
            ;;
        *)
            warn "Неизвестный выбор '$choice', использую авто"
            build_local && built=1 || warn "Локально не удалось, пробую Docker"
            if [[ $built -eq 0 ]]; then
                build_docker && built=1 || warn "Docker не сработал"
            fi
            ;;
    esac

    if [[ $built -eq 0 && "${choice,,}" != "3" && "${choice,,}" != "actions" && "${choice,,}" != "github" ]]; then
        build_github_actions
        fail "Не удалось собрать APK ни локально, ни через Docker"
    fi
}

ensure_layout
print_header

METHOD_CHOSEN="$(select_method)"
run_flow "$METHOD_CHOSEN"
show_apks
