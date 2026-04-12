import asyncio
import random
import string
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

bot = Bot(token="YOUR_TOKEN_HERE")
dp = Dispatcher()

# Хранилище капч и авторизованных пользователей
captcha_storage = {}
authorized_users = set()

def generate_captcha():
    """Генерация случайной капчи"""
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return captcha_text

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in authorized_users:
        await message.answer("Вы уже авторизованы!")
    else:
        captcha = generate_captcha()
        captcha_storage[user_id] = captcha

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пройти капчу", callback_data=f"captcha_{captcha}")]
        ])

        await message.answer(f"Для авторизации пройдите капчу:\n\n{captcha}", reply_markup=keyboard)

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = """
    /start - начать авторизацию
    /help - показать это сообщение
    """
    await message.answer(help_text)

@dp.callback_query(F.data.startswith("captcha_"))
async def captcha_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    captcha = callback.data.split("_")[1]

    if user_id in captcha_storage and captcha_storage[user_id] == captcha:
        authorized_users.add(user_id)
        del captcha_storage[user_id]
        await callback.message.edit_text("✅ Авторизация успешна!")
        await callback.answer("Вы успешно авторизованы!")
    else:
        await callback.answer("Капча неверна! Попробуйте снова.", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
