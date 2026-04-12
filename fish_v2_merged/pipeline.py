from database import get_unprocessed, update_news
from rewriter import rewrite
from tts_engine import synthesize
from telegram_client import send_message, send_audio, send_document
import os

def process_item(row):
    news_id, source, title, url, content = row
    tag = f"[{source.upper()}] {title[:60]}"
    print(f"\n  ⚙️  {tag}")

    send_message(f"✍️ Переписываю...\n<b>{title[:120]}</b>\n🔗 {url}")
    rewritten = rewrite(title, content, source)
    update_news(news_id, rewritten=rewritten)

    txt_path = os.path.join('output', f'news_{news_id}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"Source: {source}\nURL: {url}\n\n"
                f"=== ORIGINAL ===\n{title}\n{content}\n\n"
                f"=== REWRITTEN ===\n{rewritten}")

    mp3_path = synthesize(rewritten, f'news_{news_id}.mp3')
    update_news(news_id, mp3_path=mp3_path)

    caption = f"🎙 <b>{source.upper()}</b>\n{title[:200]}"
    ok_audio = send_audio(mp3_path, caption=caption)
    send_document(txt_path, caption="📄 Текст")

    update_news(news_id, sent=1 if ok_audio else 0)
    print(f"  ✅ Готово: {tag}")

def run_pipeline():
    items = get_unprocessed()
    if not items:
        print("  📭 Нет необработанных новостей")
        return 0
    print(f"\n🚀 Обрабатываю {len(items)} новостей...")
    ok = 0
    for row in items:
        try:
            process_item(row)
            ok += 1
        except Exception as e:
            print(f"  ❌ #{row[0]}: {e}")
    return ok
