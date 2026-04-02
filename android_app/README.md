# BlackBugsAI — Android App

Flutter-приложение для управления BlackBugsAI с мобильного устройства.

## Дизайн

- **Тема:** Neon Dark — чёрный фон с неоновыми акцентами (cyan, purple, green, pink)
- **Шрифты:** Orbitron (заголовки), JetBrainsMono (код/данные)
- **Анимации:** Boot sequence, neon scanline, pulse glow, typewriter, page transitions

## Экраны

| Экран | Описание |
|-------|----------|
| Splash | Boot animation с scan-line эффектом |
| Setup | Подключение к серверу (URL + токен) |
| Dashboard | Статистика, агенты, метрики в реальном времени |
| Tasks | Управление очередью задач (создание, отмена, повтор) |
| Agents | Карточки агентов с сетевой визуализацией |
| Terminal | Live shell-терминал с историей команд |
| Settings | Конфигурация подключения |

## Запуск

### Требования
- Flutter 3.10+
- Android SDK 21+
- Dart 3.0+

### Разработка
```bash
cd android_app
flutter pub get
flutter run
```

### Сборка APK
```bash
flutter build apk --release
# APK: build/app/outputs/flutter-apk/app-release.apk
```

### Сборка AAB (Google Play)
```bash
flutter build appbundle --release
```

## Подключение к серверу

1. Запусти BlackBugsAI сервер: `docker-compose up -d`
2. Открой приложение
3. Введи URL: `http://<IP>:8080`
4. Введи ADMIN_TOKEN из `.env`
5. Нажми CONNECT

## Архитектура

```
lib/
├── main.dart              # Entry point
├── theme/
│   └── neon_theme.dart    # Цвета, тема, декорации
├── animations/
│   └── neon_animations.dart  # Boot, loading, transitions, typewriter
├── models/
│   └── models.dart        # Task, AgentInfo, SystemStats, etc.
├── services/
│   └── api_service.dart   # HTTP клиент для admin API
├── screens/
│   ├── splash_screen.dart
│   ├── setup_screen.dart
│   ├── main_shell.dart    # Bottom nav container
│   ├── dashboard_screen.dart
│   ├── tasks_screen.dart
│   ├── agents_screen.dart
│   ├── terminal_screen.dart
│   └── settings_screen.dart
└── widgets/
    ├── neon_card.dart
    ├── neon_text_field.dart
    ├── agent_status_chip.dart
    └── task_status_bar.dart
```

## Анимации

- **Boot sequence** — матричный экран загрузки с логом системы
- **Scan line** — бегущая неоновая линия на splash
- **Pulse glow** — пульсация онлайн-индикаторов агентов
- **Neon spinner** — кастомный индикатор загрузки
- **Typewriter** — посимвольное появление текста
- **Page transitions** — slide + scan line + fade при переходах
- **Agent network** — анимированная визуализация сети агентов
