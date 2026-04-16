import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = 5722838040  # если хочешь запускать игру только в одном чате - поставь chat_id, иначе None

GAME_INTERVAL_SECONDS = 600   # 10 минут
BET_OPEN_BEFORE_SECONDS = 60  # за 1 минуту до старта
COUNTDOWN_SECONDS = 3

START_BALANCE = 1000
BET_AMOUNT = 100

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# DATA
# =========================
@dataclass
class Team:
    key: str
    name: str
    emoji: str
    hp: int = 100
    alive: bool = True

@dataclass
class GameState:
    game_id: int = 0
    status: str = "idle"  # idle, waiting_bets, countdown, fighting, finished
    start_time: Optional[datetime] = None
    bet_open_time: Optional[datetime] = None
    teams: Dict[str, Team] = field(default_factory=dict)
    bets: Dict[int, str] = field(default_factory=dict)       # user_id -> team_key
    balances: Dict[int, int] = field(default_factory=dict)   # user_id -> coins
    last_message_id: Optional[int] = None
    current_chat_id: Optional[int] = None

game = GameState()

TEAM_PRESETS = [
    ("red", "Красные", "🔴"),
    ("blue", "Синие", "🔵"),
    ("green", "Зелёные", "🟢"),
    ("yellow", "Жёлтые", "🟡"),
]

# =========================
# HELPERS
# =========================
def reset_teams() -> Dict[str, Team]:
    return {
        key: Team(key=key, name=name, emoji=emoji, hp=100, alive=True)
        for key, name, emoji in TEAM_PRESETS
    }

def get_alive_teams() -> list[Team]:
    return [team for team in game.teams.values() if team.alive]

def build_bet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, name, emoji in TEAM_PRESETS:
        builder.button(text=f"{emoji} {name}", callback_data=f"bet:{key}")
    builder.adjust(2)
    return builder.as_markup()

def format_teams_status() -> str:
    lines = []
    for team in game.teams.values():
        status = "живы" if team.alive else "выбиты"
        lines.append(f"{team.emoji} <b>{team.name}</b> — HP: {team.hp} ({status})")
    return "\n".join(lines)

def ensure_balance(user_id: int):
    if user_id not in game.balances:
        game.balances[user_id] = START_BALANCE

def calculate_winnings(winner_key: str):
    winners = [uid for uid, team_key in game.bets.items() if team_key == winner_key]
    losers = [uid for uid, team_key in game.bets.items() if team_key != winner_key]

    total_bank = len(game.bets) * BET_AMOUNT
    if not winners:
        return []

    payout_each = total_bank // len(winners)
    payouts = []

    for uid in winners:
        game.balances[uid] += payout_each
        payouts.append((uid, payout_each))

    return payouts

async def safe_send(bot: Bot, chat_id: int, text: str, reply_markup=None):
    try:
        msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
        return msg
    except Exception as e:
        logger.exception("Send message error: %s", e)
        return None

# =========================
# GAME FLOW
# =========================
async def prepare_new_game(bot: Bot, chat_id: int):
    game.game_id += 1
    game.status = "idle"
    game.start_time = datetime.utcnow() + timedelta(seconds=GAME_INTERVAL_SECONDS)
    game.bet_open_time = game.start_time - timedelta(seconds=BET_OPEN_BEFORE_SECONDS)
    game.teams = reset_teams()
    game.bets = {}
    game.current_chat_id = chat_id

    await safe_send(
        bot,
        chat_id,
        (
            f"🎮 <b>Новая игра #{game.game_id}</b>\n\n"
            f"Команды:\n"
            f"🔴 Красные\n"
            f"🔵 Синие\n"
            f"🟢 Зелёные\n"
            f"🟡 Жёлтые\n\n"
            f"До старта: <b>10 минут</b>\n"
            f"Кнопка <b>«Ставка»</b> откроется за <b>1 минуту</b> до начала."
        ),
    )

async def open_bets(bot: Bot):
    if not game.current_chat_id:
        return

    game.status = "waiting_bets"
    await safe_send(
        bot,
        game.current_chat_id,
        (
            f"💰 <b>Ставки открыты!</b>\n\n"
            f"До старта игры осталась <b>1 минута</b>.\n"
            f"Ставка фиксированная: <b>{BET_AMOUNT}</b> монет.\n"
            f"Выбирай, кто выживет последним."
        ),
        reply_markup=build_bet_keyboard()
    )

async def countdown(bot: Bot):
    if not game.current_chat_id:
        return

    game.status = "countdown"
    for sec in [3, 2, 1]:
        await safe_send(bot, game.current_chat_id, f"⏳ <b>{sec}</b>")
        await asyncio.sleep(1)

    await safe_send(bot, game.current_chat_id, "🔥 <b>Бой начался!</b> Ставки закрыты.")

async def battle_loop(bot: Bot):
    if not game.current_chat_id:
        return

    game.status = "fighting"

    while len(get_alive_teams()) > 1:
        alive = get_alive_teams()
        attacker = random.choice(alive)

        possible_targets = [team for team in alive if team.key != attacker.key]
        if not possible_targets:
            break

        target = random.choice(possible_targets)
        damage = random.randint(10, 35)
        target.hp -= damage

        text = (
            f"{attacker.emoji} <b>{attacker.name}</b> атакуют "
            f"{target.emoji} <b>{target.name}</b> и наносят <b>{damage}</b> урона!\n\n"
        )

        if target.hp <= 0:
            target.hp = 0
            target.alive = False
            text += f"💀 {target.emoji} <b>{target.name}</b> выбывают!\n\n"

        text += format_teams_status()

        await safe_send(bot, game.current_chat_id, text)
        await asyncio.sleep(2)

    winners = get_alive_teams()
    if not winners:
        await safe_send(bot, game.current_chat_id, "🤡 Все умерли. Красота. Победителей нет.")
        game.status = "finished"
        return

    winner = winners[0]
    payouts = calculate_winnings(winner.key)

    lines = [
        f"🏆 <b>Победили: {winner.emoji} {winner.name}</b>",
        "",
        "💸 Выплаты:"
    ]

    if payouts:
        for uid, amount in payouts:
            lines.append(f"— user_id <code>{uid}</code>: +{amount} монет")
    else:
        lines.append("— никто не угадал")

    await safe_send(bot, game.current_chat_id, "\n".join(lines))
    game.status = "finished"

async def game_scheduler(bot: Bot, chat_id: int):
    while True:
        await prepare_new_game(bot, chat_id)

        # ждём до открытия ставок
        while datetime.utcnow() < game.bet_open_time:
            await asyncio.sleep(1)

        await open_bets(bot)

        # ждём до старта
        while datetime.utcnow() < game.start_time:
            await asyncio.sleep(1)

        await countdown(bot)
        await battle_loop(bot)

# =========================
# BOT HANDLERS
# =========================
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    ensure_balance(message.from_user.id)
    await message.answer(
        (
            "👋 <b>Бот игры запущен</b>\n\n"
            "Команды:\n"
            "/balance — баланс\n"
            "/mybet — моя ставка\n"
            "/help — помощь\n\n"
            "Игра автоматически запускается каждые 10 минут."
        )
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        (
            "📜 <b>Правила</b>\n\n"
            "— Есть 4 команды\n"
            f"— Ставки открываются за {BET_OPEN_BEFORE_SECONDS // 60} минуту до старта\n"
            f"— Каждая ставка стоит {BET_AMOUNT} монет\n"
            "— Кто поставил на победителя — получает долю общего банка"
        )
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    ensure_balance(message.from_user.id)
    await message.answer(f"💳 Твой баланс: <b>{game.balances[message.from_user.id]}</b> монет")

@dp.message(Command("mybet"))
async def cmd_mybet(message: Message):
    team_key = game.bets.get(message.from_user.id)
    if not team_key:
        await message.answer("🎲 Ты пока ни на кого не поставил.")
        return

    team = game.teams.get(team_key)
    if team:
        await message.answer(f"📌 Твоя ставка: {team.emoji} <b>{team.name}</b>")
    else:
        await message.answer("📌 Ставка есть, но команда уже где-то потерялась в космосе.")

@dp.callback_query(F.data.startswith("bet:"))
async def handle_bet(callback: CallbackQuery):
    user_id = callback.from_user.id
    ensure_balance(user_id)

    if game.status != "waiting_bets":
        await callback.answer("Ставки сейчас закрыты", show_alert=True)
        return

    if user_id in game.bets:
        await callback.answer("Ты уже поставил. Харе жульничать.", show_alert=True)
        return

    if game.balances[user_id] < BET_AMOUNT:
        await callback.answer("Недостаточно монет", show_alert=True)
        return

    team_key = callback.data.split(":")[1]
    if team_key not in game.teams:
        await callback.answer("Команда не найдена", show_alert=True)
        return

    game.balances[user_id] -= BET_AMOUNT
    game.bets[user_id] = team_key
    team = game.teams[team_key]

    await callback.answer("Ставка принята ✅")
    await callback.message.answer(
        f"💰 {callback.from_user.full_name} поставил на {team.emoji} <b>{team.name}</b>"
    )

# =========================
# MAIN
# =========================
async def main():
    bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

    logger.info("Bot started")

    # Если CHAT_ID не задан, автозапуск в первом чате не заработает,
    # пока ты сам не задашь chat_id. Для теста лучше указать его явно.
    if CHAT_ID is not None:
        asyncio.create_task(game_scheduler(bot, CHAT_ID))
    else:
        logger.warning("CHAT_ID is None. Set your Telegram chat id for auto game scheduler.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
