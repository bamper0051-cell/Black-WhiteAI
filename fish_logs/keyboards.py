# -*- coding: utf-8 -*-
"""
keyboards.py — Единая клавиатура для всех агентов AGENT_SMITH.

Правило: каждый агент после выполнения задачи показывает кнопки из этого модуля.
Никакой собственной клавиатуры в агентах — только через get_*_keyboard().
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── Inline-кнопки управления сессией (после выполнения задачи) ─────────────

def get_session_wait_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопки после завершения задачи:
      📎 Добавить файлы  |  🔴 Завершить сессию
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📎 Добавить файлы", callback_data="session_add_files"),
        InlineKeyboardButton(text="🔴 Завершить сессию", callback_data="session_stop"),
    )
    return builder.as_markup()


def get_session_files_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопки в режиме ожидания файлов:
      ✅ Готово (запустить задачу)  |  ❌ Отмена
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово — запустить", callback_data="session_files_ready"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="session_stop"),
    )
    return builder.as_markup()


def get_agent_running_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопка отмены во время выполнения задачи.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⛔ Остановить", callback_data="session_abort"),
    )
    return builder.as_markup()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню после завершения сессии.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Новая задача", callback_data="menu_new_task"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 История", callback_data="menu_history"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
    )
    return builder.as_markup()


def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """
    Выбор типа задачи вручную (если auto-detect не уверен).
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🐍 Скрипт", callback_data="task_type_script"),
        InlineKeyboardButton(text="📦 Проект", callback_data="task_type_project"),
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Изображение", callback_data="task_type_image"),
        InlineKeyboardButton(text="🔍 Ревью кода", callback_data="task_type_review"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Быстро", callback_data="task_type_quick"),
    )
    return builder.as_markup()


# ─── Callback data константы ────────────────────────────────────────────────

class CB:
    """Константы callback_data для надёжного сравнения."""
    SESSION_ADD_FILES   = "session_add_files"
    SESSION_STOP        = "session_stop"
    SESSION_FILES_READY = "session_files_ready"
    SESSION_ABORT       = "session_abort"
    MENU_NEW_TASK       = "menu_new_task"
    MENU_SETTINGS       = "menu_settings"
    MENU_HISTORY        = "menu_history"
    MENU_HELP           = "menu_help"
    TASK_SCRIPT         = "task_type_script"
    TASK_PROJECT        = "task_type_project"
    TASK_IMAGE          = "task_type_image"
    TASK_REVIEW         = "task_type_review"
    TASK_QUICK          = "task_type_quick"
