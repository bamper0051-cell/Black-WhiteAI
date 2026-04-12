#!/data/data/com.termux/files/usr/bin/bash
echo "🚀 АВТОМУВИ — Setup"

# Termux packages
pkg update -y && pkg install -y python ffmpeg

# Pip
pip install --upgrade pip
pip install -r requirements.txt

# .env
if [ ! -f .env ]; then
    echo "⚙️  Запускаю мастер настройки..."
    python setup_wizard.py
else
    echo "✅ .env уже существует. Пропускаю."
fi

mkdir -p output
echo ""
echo "✅ Готово! Запуск: python bot.py"
