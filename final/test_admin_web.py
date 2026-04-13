"""
test_admin_web.py — запускает только Admin Web Panel для диагностики
Запусти: python test_admin_web.py
Потом открой: http://localhost:8080/ping
"""
import os, sys
os.environ.setdefault('ADMIN_WEB_PORT', '8080')
os.environ.setdefault('ADMIN_WEB_TOKEN', 'test123')

print("🔍 Тест Admin Web Panel")
print(f"   Python: {sys.version}")
print(f"   Порт: {os.environ['ADMIN_WEB_PORT']}")

# Проверяем Flask
try:
    import flask
    print(f"   Flask: {flask.__version__} ✅")
except ImportError:
    print("   Flask: ❌ не установлен! pip install flask")
    sys.exit(1)

# Проверяем config
try:
    import config
    print(f"   Config: BASE_DIR={config.BASE_DIR} ✅")
except Exception as e:
    print(f"   Config: ❌ {e}")
    sys.exit(1)

# Запускаем
print("\n🚀 Запускаю Admin Web...")
print("   Открой: http://localhost:8080/ping")
print("   Панель: http://localhost:8080/panel")
print("   Ctrl+C для остановки\n")

from admin_web import app, ADMIN_WEB_PORT
app.run(host='0.0.0.0', port=ADMIN_WEB_PORT, debug=True, use_reloader=False)
