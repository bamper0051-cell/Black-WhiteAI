@echo off
echo Создаю файлы и папки...
type nul > auth.db
type nul > automuvie.db
type nul > sessions.db
type nul > tasks.db
mkdir fish_uploads 2>nul
mkdir fish_pages 2>nul
mkdir fish_logs 2>nul
mkdir agent_projects 2>nul
mkdir created_bots 2>nul
mkdir artifacts 2>nul
echo Готово! Запусти: docker compose up -d
pause
