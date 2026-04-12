@echo off
<<<<<<< HEAD
echo Создаю файлы и папки...
type nul > auth.db
type nul > automuvie.db
type nul > sessions.db
type nul > tasks.db
mkdir fish_uploads 2>nul
mkdir fish_pages 2>nul
=======
echo ==========================================
echo  АВТОМУВИ — первоначальная настройка
echo ==========================================
echo.

echo Создаю файлы БД (ФАЙЛЫ, не папки)...
type nul > auth.db
type nul > automuvie.db
echo   OK: auth.db
echo   OK: automuvie.db

echo.
echo Создаю папки...
mkdir fish_uploads 2>nul
mkdir fish_pages 2>nul  
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
mkdir fish_logs 2>nul
mkdir agent_projects 2>nul
mkdir created_bots 2>nul
mkdir artifacts 2>nul
<<<<<<< HEAD
echo Готово! Запусти: docker compose up -d
=======
echo   OK: все папки созданы

echo.
echo Готово! Теперь:
echo   1. Заполни .env (скопируй из .env.example)
echo   2. docker compose up -d
echo   3. Открой http://localhost:8080/panel
echo.
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
pause
