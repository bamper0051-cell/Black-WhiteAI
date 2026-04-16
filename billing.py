"""
BlackBugsAI — Billing
Тарифы, кредиты, лимиты задач.
Хранит данные в auth.db (рядом с ботом).
"""
import os, sqlite3, time, json
import config
from core.db_manager import BLACKBUGS_DB

# ─── DB ───────────────────────────────────────────────────────────────────────

_DB = str(BLACKBUGS_DB)

def _db():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_billing():
    with _db() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS billing (
                user_id     TEXT PRIMARY KEY,
                plan        TEXT DEFAULT 'free',
                credits     REAL DEFAULT 0,
                tasks_today INTEGER DEFAULT 0,
                reset_date  TEXT DEFAULT '',
                expires_at  REAL DEFAULT 0,
                updated_at  REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT,
                type        TEXT,
                amount      REAL,
                tool        TEXT,
                note        TEXT,
                created_at  REAL
            );
        ''')

try:
    init_billing()
except Exception:
    pass


# ─── BillingManager ────────────────────────────────────────────────────────────

class BillingManager:
    def __init__(self, user_id: str):
        self.user_id = str(user_id)

    def _get(self) -> dict:
        try:
            with _db() as c:
                r = c.execute('SELECT * FROM billing WHERE user_id=?',
                              (self.user_id,)).fetchone()
                if not r:
                    now = time.time()
                    today = time.strftime('%Y-%m-%d')
                    c.execute(
                        'INSERT INTO billing (user_id, plan, credits, tasks_today, reset_date, updated_at) '
                        'VALUES (?,?,?,?,?,?)',
                        (self.user_id, 'free', 0, 0, today, now)
                    )
                    return {'user_id': self.user_id, 'plan': 'free',
                            'credits': 0.0, 'tasks_today': 0,
                            'reset_date': today, 'expires_at': 0}
                return dict(r)
        except Exception:
            return {'user_id': self.user_id, 'plan': 'free',
                    'credits': 0.0, 'tasks_today': 0,
                    'reset_date': '', 'expires_at': 0}

    @property
    def plan(self) -> str:
        return self._get().get('plan', 'free')

    @property
    def credits(self) -> float:
        return float(self._get().get('credits', 0))

    def can_run_task(self) -> tuple:
        """Проверяет лимит задач. Возвращает (ok, error_text)."""
        row    = self._get()
        plan   = row.get('plan', 'free')
        pcfg   = config.get_plan(plan)
        limit  = pcfg.get('tasks_per_day', 10)
        today  = time.strftime('%Y-%m-%d')

        # Сбрасываем счётчик при новом дне
        tasks_today = row.get('tasks_today', 0)
        if row.get('reset_date') != today:
            tasks_today = 0
            try:
                with _db() as c:
                    c.execute('UPDATE billing SET tasks_today=0, reset_date=? WHERE user_id=?',
                              (today, self.user_id))
            except Exception:
                pass

        if limit != -1 and tasks_today >= limit:
            pcfg_pro = config.get_plan('pro')
            return False, (
                f"❌ Лимит <b>{limit}</b> задач/день исчерпан.\n"
                f"Тариф: <b>{pcfg.get('name', plan)}</b>\n\n"
                f"⭐ Upgrade до Pro — {pcfg_pro.get('price', 9.99)}$/мес → /billing"
            )
        return True, ""

    def charge_task(self, tool: str = '', cost: float = 0.0) -> bool:
        """Списывает кредиты и инкрементирует счётчик задач."""
        try:
            row = self._get()
            if cost > 0 and float(row.get('credits', 0)) < cost:
                return False
            today = time.strftime('%Y-%m-%d')
            with _db() as c:
                if cost > 0:
                    c.execute(
                        'UPDATE billing SET credits=credits-?, updated_at=? WHERE user_id=?',
                        (cost, time.time(), self.user_id)
                    )
                    c.execute(
                        'INSERT INTO transactions (user_id, type, amount, tool, created_at) VALUES (?,?,?,?,?)',
                        (self.user_id, 'spend', cost, tool, time.time())
                    )
                # Сбрасываем счётчик если новый день
                if row.get('reset_date') != today:
                    c.execute('UPDATE billing SET tasks_today=1, reset_date=? WHERE user_id=?',
                              (today, self.user_id))
                else:
                    c.execute('UPDATE billing SET tasks_today=tasks_today+1 WHERE user_id=?',
                              (self.user_id,))
            return True
        except Exception:
            return True  # при ошибке БД не блокируем пользователя

    def add_credits(self, amount: float, note: str = ''):
        try:
            with _db() as c:
                c.execute('UPDATE billing SET credits=credits+?, updated_at=? WHERE user_id=?',
                          (amount, time.time(), self.user_id))
                c.execute(
                    'INSERT INTO transactions (user_id, type, amount, note, created_at) VALUES (?,?,?,?,?)',
                    (self.user_id, 'purchase', amount, note, time.time())
                )
        except Exception:
            pass

    def upgrade_plan(self, plan: str, months: int = 1):
        expires = time.time() + months * 30 * 86400
        try:
            with _db() as c:
                c.execute('UPDATE billing SET plan=?, expires_at=?, updated_at=? WHERE user_id=?',
                          (plan, expires, time.time(), self.user_id))
        except Exception:
            pass

    def format_status(self) -> str:
        row   = self._get()
        plan  = row.get('plan', 'free')
        pcfg  = config.get_plan(plan)
        today = time.strftime('%Y-%m-%d')
        used  = row.get('tasks_today', 0) if row.get('reset_date') == today else 0
        limit = pcfg.get('tasks_per_day', 10)
        cred  = float(row.get('credits', 0))

        if limit == -1:
            bar = "∞"
        else:
            filled = int(10 * used / max(limit, 1))
            bar = "█" * filled + "░" * (10 - filled)

        lines = [
            f"💳 <b>BlackBugsAI Billing</b>\n",
            f"Тариф: <b>{pcfg.get('name', plan)}</b>",
            f"Кредиты: <b>{cred:.1f}</b>",
            f"Задач сегодня: <b>{used}</b> / {'∞' if limit==-1 else limit}",
            f"[{bar}]",
        ]
        if row.get('expires_at', 0) > time.time():
            exp = time.strftime('%d.%m.%Y', time.localtime(row['expires_at']))
            lines.append(f"Действует до: {exp}")
        return "\n".join(lines)

    def billing_keyboard(self) -> dict:
        return {"inline_keyboard": [
            [{"text": "⭐ Pro — $9.99/мес",       "callback_data": "billing:upgrade:pro"}],
            [{"text": "🚀 Business — $49.99/мес",  "callback_data": "billing:upgrade:business"}],
            [{"text": "💰 Купить кредиты",          "callback_data": "billing:buy_credits"}],
            [{"text": "📊 История",                 "callback_data": "billing:history"}],
            [{"text": "◀️ Меню",                    "callback_data": "menu"}],
        ]}

    def history(self, n: int = 10) -> str:
        try:
            with _db() as c:
                rows = c.execute(
                    'SELECT type, amount, tool, created_at FROM transactions '
                    'WHERE user_id=? ORDER BY created_at DESC LIMIT ?',
                    (self.user_id, n)
                ).fetchall()
            if not rows:
                return "📊 Транзакций нет."
            lines = ["📊 <b>История транзакций</b>\n"]
            for r in rows:
                ts   = time.strftime('%d.%m %H:%M', time.localtime(r['created_at']))
                icon = {'spend':'💸','purchase':'💰','bonus':'🎁'}.get(r['type'], '•')
                tool = f" ({r['tool']})" if r['tool'] else ""
                lines.append(f"{icon} {ts}: {r['type']}{tool} — {r['amount']:.1f}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Ошибка: {e}"
