from flask import Flask, jsonify, render_template_string
import requests
import re
import os
import time
import threading

app = Flask(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8501492191:AAGzlwCiAnaXOeDxUjTTWE3oAW4RZ8824rU')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '6333310184')

otps = []
last_id = 0

def fetch_messages():
    global last_id
    if not BOT_TOKEN or not CHAT_ID:
        return []
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        r = requests.get(url, params={'offset': last_id + 1}, timeout=10)
        data = r.json()
        if not data.get('ok'):
            return []
        messages = []
        for update in data.get('result', []):
            last_id = update['update_id']
            if 'message' in update:
                msg = update['message']
                if str(msg.get('chat', {}).get('id')) == str(CHAT_ID):
                    text = msg.get('text', '')
                    otp = re.search(r'\b\d{4,6}\b', text)
                    if otp:
                        messages.append({
                            'otp': otp.group(),
                            'text': text[:100],
                            'time': time.strftime('%H:%M:%S')
                        })
        return messages
    except Exception as e:
        print(e)
        return []

def process():
    global otps
    for msg in fetch_messages():
        if not any(o['otp'] == msg['otp'] for o in otps):
            otps.insert(0, msg)
            if len(otps) > 50:
                otps.pop()

def background():
    while True:
        try:
            process()
        except:
            pass
        time.sleep(5)

if BOT_TOKEN and CHAT_ID:
    threading.Thread(target=background, daemon=True).start()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram OTP Monitor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #0088cc, #2c3e50);
            padding: 20px;
            margin: 0;
            min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 { color: #0088cc; margin: 0 0 10px 0; font-size: 24px; }
        .status {
            background: #f3f4f6;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .otp-item {
            background: #f9fafb;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .otp-code {
            font-size: 24px;
            font-weight: bold;
            color: #0088cc;
            font-family: monospace;
            cursor: pointer;
        }
        .otp-time { color: #6b7280; font-size: 12px; }
        .empty { text-align: center; padding: 40px; color: #9ca3af; }
        button {
            background: #0088cc;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover { background: #006699; }
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1f2937;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            z-index: 1000;
        }
        @media (max-width: 600px) {
            .otp-code { font-size: 18px; }
            .otp-item { flex-direction: column; align-items: flex-start; gap: 8px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📱 Telegram OTP Monitor</h1>
            <div class="status">Status: <span id="statusText">🟢 Active</span></div>
            <div id="otps"><div class="empty">No OTPs yet. Send OTP to Telegram group!</div></div>
            <button onclick="refresh()">🔄 Refresh</button>
        </div>
    </div>
    <script>
        function showToast(msg) {
            let t = document.createElement('div');
            t.className = 'toast';
            t.innerHTML = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2000);
        }
        async function load() {
            try {
                let res = await fetch('/api/otps');
                let data = await res.json();
                let container = document.getElementById('otps');
                if (data.length === 0) {
                    container.innerHTML = '<div class="empty">No OTPs yet. Send OTP to Telegram group!</div>';
                } else {
                    let html = '';
                    for (let o of data) {
                        html += `<div class="otp-item"><div><div class="otp-code" onclick="copy('${o.otp}')">📋 ${o.otp}</div><div class="otp-time">${o.time}</div></div><div style="font-size:12px;color:#6b7280;">${o.text.substring(0,40)}</div></div>`;
                    }
                    container.innerHTML = html;
                }
            } catch(e) {}
        }
        async function refresh() {
            await fetch('/api/refresh', {method: 'POST'});
            load();
            showToast('✅ Refreshed');
        }
        function copy(otp) {
            navigator.clipboard.writeText(otp);
            showToast(`📋 Copied: ${otp}`);
        }
        load();
        setInterval(load, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/otps')
def get_otps():
    return jsonify(otps)

@app.route('/api/refresh', methods=['POST'])
def refresh():
    process()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
