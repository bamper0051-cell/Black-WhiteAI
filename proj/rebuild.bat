@echo off
echo ==========================================
echo  АВТОМУВИ — полная пересборка Docker
echo ==========================================

echo.
echo [1/5] Останавливаю контейнер...
docker stop automuvie 2>nul
docker rm automuvie 2>nul

echo.
echo [2/5] Удаляю старый образ...
docker rmi automuvie 2>nul
docker rmi automuvie:latest 2>nul

echo.
echo [3/5] Удаляю кэш сборки...
docker builder prune -f

echo.
echo [4/5] Собираю заново (без кэша)...
docker build --no-cache --progress=plain -t automuvie .
if errorlevel 1 (
    echo.
    echo ОШИБКА сборки! Смотри вывод выше.
    pause
    exit /b 1
)

echo.
echo [5/5] Запускаю...
docker compose up -d

echo.
echo Готово! Логи:
docker logs -f automuvie
