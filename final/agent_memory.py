"""
BlackBugsAI — Agent Memory
UserMemory | TaskHistory | AgentLearning | AgentMemory
"""
import os, json, sqlite3, time
from pathlib import Path
from typing import List, Dict, Optional, Any

DB_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / 'memory.db'

def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_memory_db():
    with _db() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT,
                source TEXT DEFAULT 'user', created_at REAL, updated_at REAL,
                UNIQUE(user_id, key)
            );
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, task TEXT, plan_json TEXT,
                result TEXT, tools_used TEXT, status TEXT DEFAULT 'done',
                duration_s REAL, created_at REAL
            );
            CREATE TABLE IF NOT EXISTS agent_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT, tool_sequence TEXT,
                success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0,
                updated_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_um ON user_memory(user_id);
            CREATE INDEX IF NOT EXISTS idx_th ON task_history(user_id);
        ''')

init_memory_db()


class UserMemory:
    def __init__(self, user_id: str):
        self.user_id = str(user_id)

    def remember(self, key: str, value: Any, source: str = 'agent'):
        now = time.time()
        with _db() as c:
            c.execute('''INSERT INTO user_memory (user_id,key,value,source,created_at,updated_at)
                         VALUES (?,?,?,?,?,?)
                         ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at''',
                      (self.user_id, key, json.dumps(value, ensure_ascii=False), source, now, now))

    def recall(self, key: str, default=None) -> Any:
        with _db() as c:
            r = c.execute('SELECT value FROM user_memory WHERE user_id=? AND key=?',
                          (self.user_id, key)).fetchone()
            if r:
                try: return json.loads(r['value'])
                except: return r['value']
            return default

    def recall_all(self) -> Dict[str, Any]:
        with _db() as c:
            rows = c.execute('SELECT key,value FROM user_memory WHERE user_id=? ORDER BY updated_at DESC LIMIT 50',
                             (self.user_id,)).fetchall()
            result = {}
            for row in rows:
                try: result[row['key']] = json.loads(row['value'])
                except: result[row['key']] = row['value']
            return result

    def forget(self, key: str):
        with _db() as c:
            c.execute('DELETE FROM user_memory WHERE user_id=? AND key=?', (self.user_id, key))

    def forget_all(self):
        with _db() as c:
            c.execute('DELETE FROM user_memory WHERE user_id=?', (self.user_id,))

    def to_context(self) -> str:
        mem = self.recall_all()
        if not mem: return ""
        lines = ["Что я знаю о пользователе:"]
        for k, v in list(mem.items())[:15]:
            lines.append(f"  • {k}: {str(v)[:100]}")
        return "\n".join(lines)

    def extract_from_message(self, text: str):
        import re
        m = re.search(r'меня зовут\s+(\w+)', text.lower())
        if m: self.remember('name', m.group(1), 'extracted')
        self.remember('last_message', text[:200], 'message')
        self.remember('last_seen', time.strftime('%Y-%m-%d %H:%M'), 'system')


class TaskHistory:
    def __init__(self, user_id: str):
        self.user_id = str(user_id)

    def add(self, task: str, plan: dict = None, result: str = '',
            tools: list = None, status: str = 'done', duration: float = 0):
        with _db() as c:
            c.execute('''INSERT INTO task_history
                (user_id,task,plan_json,result,tools_used,status,duration_s,created_at)
                VALUES (?,?,?,?,?,?,?,?)''',
                (self.user_id, task[:500],
                 json.dumps(plan, ensure_ascii=False) if plan else None,
                 result[:1000], json.dumps(tools or []), status, duration, time.time()))

    def recent(self, n: int = 10) -> List[dict]:
        with _db() as c:
            rows = c.execute('SELECT * FROM task_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?',
                             (self.user_id, n)).fetchall()
            return [dict(r) for r in rows]

    def to_context(self, n: int = 5) -> str:
        tasks = self.recent(n)
        if not tasks: return ""
        lines = ["Последние задачи:"]
        for t in tasks:
            ts = time.strftime('%m/%d %H:%M', time.localtime(t.get('created_at', 0)))
            lines.append(f"  [{ts}] {t['status']}: {t['task'][:80]}")
        return "\n".join(lines)


class AgentLearning:
    def record_success(self, pattern: str, tools: List[str]):
        seq = json.dumps(tools)
        with _db() as c:
            c.execute('INSERT OR IGNORE INTO agent_learning (pattern,tool_sequence,success_count,updated_at) VALUES (?,?,0,?)',
                      (pattern[:100], seq, time.time()))
            c.execute('UPDATE agent_learning SET success_count=success_count+1,updated_at=? WHERE pattern=? AND tool_sequence=?',
                      (time.time(), pattern[:100], seq))

    def record_fail(self, pattern: str, tools: List[str]):
        seq = json.dumps(tools)
        with _db() as c:
            c.execute('UPDATE agent_learning SET fail_count=fail_count+1 WHERE pattern=? AND tool_sequence=?',
                      (pattern[:100], seq))

    def suggest_tools(self, task: str) -> Optional[List[str]]:
        for word in task.lower().split()[:5]:
            with _db() as c:
                r = c.execute('SELECT tool_sequence FROM agent_learning WHERE pattern LIKE ? ORDER BY success_count DESC LIMIT 1',
                              (f'%{word}%',)).fetchone()
                if r:
                    try: return json.loads(r['tool_sequence'])
                    except: pass
        return None


class AgentMemory:
    def __init__(self, user_id: str):
        self.user_id = str(user_id)
        self.user    = UserMemory(user_id)
        self.history = TaskHistory(user_id)
        self.learning = AgentLearning()

    def build_context(self, task: str) -> str:
        parts = []
        mem = self.user.to_context()
        if mem: parts.append(mem)
        hist = self.history.to_context(5)
        if hist: parts.append(hist)
        self.user.extract_from_message(task)
        return "\n\n".join(parts)

    def after_task(self, task: str, tools_used: list, result: str,
                   status: str = 'done', duration: float = 0):
        self.history.add(task, tools=tools_used, result=result,
                        status=status, duration=duration)
        if status == 'done' and tools_used:
            self.learning.record_success(task[:50], tools_used)
        elif status == 'failed' and tools_used:
            self.learning.record_fail(task[:50], tools_used)
