#!/usr/bin/env bash
# ============================================================
# BlackBugsAI — APK Build Script (rebuilt)
# Методы:
#   1) local flutter
#   2) docker
#   3) github actions
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
  echo "║     BlackBugsAI — APK Builder           ║"
  echo "╚══════════════════════════════════════════╝"
  echo -e "${NC}"
}

ensure_layout() {
  [[ -d "$APP_DIR" ]] || fail "Не найден android_app: $APP_DIR"
  mkdir -p "$OUTPUT_DIR"
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
  ls -lh "$OUTPUT_DIR"/*.apk 2>/dev/null || warn "APK пока не найден"
}

build_local() {
  echo -e "${YELLOW}[1/3] Сборка через локальный Flutter${NC}"

  command -v flutter >/dev/null 2>&1 || return 1

  echo "Flutter: $(flutter --version 2>&1 | head -1)"
  cd "$APP_DIR"

  flutter clean
  flutter pub get
  flutter build apk --release --split-per-abi

  copy_apks "$APP_DIR"
  log "APK собран локально"
}

build_docker() {
  echo -e "${YELLOW}[2/3] Сборка через Docker${NC}"

  command -v docker >/dev/null 2>&1 || return 1
  ensure_layout

  docker pull "$DOCKER_FLUTTER_IMAGE" >/dev/null 2>&1 || warn "Не удалось заранее подтянуть образ, пробую сразу запуск"

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

  log "APK собран через Docker"
}

build_github_actions() {
  echo -e "${CYAN}${BOLD}"
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║         Сборка через GitHub Actions                     ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
  echo "1. Открой репозиторий:"
  echo "   https://github.com/bamper0051-cell/Black-WhiteAI"
  echo
  echo "2. Actions → Build Android APK → Run workflow"
  echo
  echo "3. После завершения скачай артефакт:"
  echo "   BlackBugsAI-APKs"
  echo
  echo "4. Для релиза укажи tag и забери APK из Releases"
}

main() {
  print_header
  ensure_layout

  echo "Выбери метод сборки:"
  echo "  1) Локальный Flutter"
  echo "  2) Docker"
  echo "  3) GitHub Actions"
  echo
  read -r -p "Метод [1/2/3]: " method

  case "${method:-}" in
    1)
      build_local || { warn "Локальная сборка недоступна, пробую Docker"; build_docker || build_github_actions; }
      ;;
    2)
      build_docker || build_github_actions
      ;;
    3)
      build_github_actions
      ;;
    *)
      warn "Неизвестный выбор, показываю GitHub Actions"
      build_github_actions
      ;;
  esac

  show_apks
}

main "$@"
