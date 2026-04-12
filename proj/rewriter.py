"""
rewriter.py — переписывает новость через LLM, используя текущий стиль из promts.py.
"""
import os
from llm_client import call_llm
from promts import STYLES

def _get_system_prompt() -> str:
    """Возвращает системный промт для текущего стиля."""
    style_key = os.environ.get('REWRITE_STYLE', 'troll').lower().strip()
    style = STYLES.get(style_key)
    if not style:
        style = STYLES['troll']  # fallback
    prompt = style.get('system', '')
    if not prompt:
        # Если «custom» ещё не настроен — откатываемся к troll
        prompt = STYLES['troll']['system']
    return prompt

def rewrite(title: str, content: str, source: str) -> str:
    system = _get_system_prompt()
    lang_note = " (переведи с английского)" if source == 'cnn' else ""
    prompt = f"""\
Перепиши эту новость в своём фирменном стиле{lang_note}.

Заголовок: {title}
Текст: {content[:2000]}

Только твой текст:"""
    try:
        return call_llm(prompt, system)
    except Exception as e:
        print(f"  ❌ LLM: {e}")
        return f"{title}. {content[:300]}"
