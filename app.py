from flask import Flask, render_template_string
import logging
from collections import deque
import time

app = Flask(__name__)

# ───────────── LOG STORAGE ─────────────
LOGS = deque(maxlen=300)  # keep last 300 logs

class WebLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        LOGS.appendleft(f"[{time.strftime('%H:%M:%S')}] {log_entry}")

# ───────────── LOGGER SETUP ─────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = WebLogHandler()
handler.setFormatter(logging.Formatter("%(levelname)s • %(message)s"))
logger.addHandler(handler)

# ───────────── WEB UI ─────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Nexora Bot Logs</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body {
            background: #0f172a;
            color: #e5e7eb;
            font-family: Consolas, monospace;
            padding: 20px;
        }
        h1 {
            color: #38bdf8;
        }
        .log-box {
            background: #020617;
            border-radius: 12px;
            padding: 15px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 0 30px rgba(56,189,248,0.15);
        }
        .log {
            padding: 4px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .INFO { color: #22c55e; }
        .WARNING { color: #facc15; }
        .ERROR { color: #ef4444; }
    </style>
</head>
<body>
    <h1>📡 Nexora Live Logs</h1>
    <div class="log-box">
        {% for log in logs %}
            <div class="log {{ log.split(' ')[1] }}">{{ log }}</div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route("/")
def logs_page():
    return render_template_string(HTML_TEMPLATE, logs=list(LOGS))

# ───────────── TEST LOGS ─────────────
@app.route("/test")
def test_logs():
    logging.info("Bot heartbeat OK")
    logging.warning("Sample warning triggered")
    logging.error("Sample error occurred")
    return "Logs added!"

if __name__ == "__main__":
    logging.info("Flask log viewer started")
    app.run(host="0.0.0.0", port=5000)
