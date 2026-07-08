#!/bin/bash
# ============================================================
# BlackBugsAI — APK Build Script
# Строит APK локально или через Docker
# ============================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="$PROJECT_DIR/android_app"
OUTPUT_DIR="$PROJECT_DIR/release-apks"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║     BlackBugsAI — APK Builder            ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

mkdir -p "$OUTPUT_DIR"

# ── Method 1: Local Flutter ────────────────────────────────────────────────
build_local() {
    echo -e "${YELLOW}[Method 1] Сборка через локальный Flutter...${NC}"

    if ! command -v flutter &> /dev/null; then
        echo -e "${RED}Flutter не найден!${NC}"
        return 1
    fi

    echo "Flutter version: $(flutter --version 2>&1 | head -1)"

    cd "$APP_DIR"
    flutter pub get
    flutter build apk --release --split-per-abi

    cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk \
       "$OUTPUT_DIR/BlackBugsAI-arm64.apk" 2>/dev/null || true
    cp build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk \
       "$OUTPUT_DIR/BlackBugsAI-arm32.apk" 2>/dev/null || true
    cp build/app/outputs/flutter-apk/app-release.apk \
       "$OUTPUT_DIR/BlackBugsAI-universal.apk" 2>/dev/null || true

    echo -e "${GREEN}✅ APK собран!${NC}"
    ls -lh "$OUTPUT_DIR"/*.apk
}

# ── Method 2: Docker build ─────────────────────────────────────────────────
build_docker() {
    echo -e "${YELLOW}[Method 2] Сборка через Docker...${NC}"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker не найден!${NC}"
        return 1
    fi

    # Use a pre-built Flutter + Android image
    docker run --rm \
        -v "$APP_DIR:/app" \
        -v "$OUTPUT_DIR:/output" \
        -w /app \
        ghcr.io/cirruslabs/flutter:3.24.5 \
        bash -c "
            flutter pub get &&
            flutter build apk --release --split-per-abi &&
            cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk /output/BlackBugsAI-arm64.apk 2>/dev/null || true &&
            cp build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk /output/BlackBugsAI-arm32.apk 2>/dev/null || true &&
            cp build/app/outputs/flutter-apk/app-release.apk /output/BlackBugsAI-universal.apk 2>/dev/null || true &&
            echo 'Build complete!'
        "

    echo -e "${GREEN}✅ APK собран через Docker!${NC}"
    ls -lh "$OUTPUT_DIR"/*.apk
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



# ── Method 4: GitHub Spark UI design workflow ─────────────────────────────
build_spark_ui() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  GitHub Spark: дизайн интерфейса APK/WebUI              ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "1. Открой GitHub Spark: https://github.com/features/spark"
    echo "2. Сгенерируй дизайн по промпту из deploy/spark_ui_prompt.md"
    echo "3. Экспортируй UI-assets в android_app/assets и web шаблоны"
    echo "4. Запусти пункт 3 (GitHub Actions) для сборки APK"
}

# ── Select build method ────────────────────────────────────────────────────
echo "Выбери метод сборки:"
echo "  1) Локальный Flutter (нужен Flutter SDK + Android SDK)"
echo "  2) Docker (нужен Docker)"
echo "  3) GitHub Actions (онлайн, без локального SDK)"
echo "  4) GitHub Spark (генерация UI/дизайна)"
echo ""
read -p "Метод [1/2/3/4]: " method

case $method in
    1) build_local || build_docker || build_github_actions ;;
    2) build_docker || build_github_actions ;;
    3) build_github_actions ;;
    4) build_spark_ui ;;
    *) build_github_actions ;;
esac

echo ""
echo -e "${CYAN}APK файлы:${NC} $OUTPUT_DIR"
