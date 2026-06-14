from flask import Flask, render_template_string, jsonify
import logging
from collections import deque
import time

app = Flask(__name__)

LOGS = deque(maxlen=500)

class WebLogHandler(logging.Handler):
    def emit(self, record):
        LOGS.appendleft({
            "time": time.strftime("%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage()
        })

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = WebLogHandler()
logger.addHandler(handler)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CricVerse Logs</title>
    <style>
        body { background: #0f172a; color: #e5e7eb; font-family: Consolas, monospace; padding: 20px; }
        h1 { color: #38bdf8; }
        .controls { margin-bottom: 10px; }
        input, select { padding: 6px; border-radius: 6px; border: none; margin-right: 6px; background: #1e293b; color: white; }
        .log-box { background: #020617; border-radius: 12px; padding: 15px; max-height: 80vh; overflow-y: auto; box-shadow: 0 0 30px rgba(56,189,248,0.15); }
        .log { padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }
        .INFO { color: #22c55e; }
        .WARNING { color: #facc15; }
        .ERROR { color: #ef4444; }
    </style>
</head>
<body>
    <h1>📡 CricVerse Live Logs</h1>
    <div class="controls">
        <select id="levelFilter"><option value="">ALL LEVELS</option><option value="INFO">INFO</option><option value="WARNING">WARNING</option><option value="ERROR">ERROR</option></select>
        <input type="text" id="search" placeholder="Search logs...">
    </div>
    <div class="log-box" id="logBox"></div>
    <script>
        async function loadLogs() {
            const level = document.getElementById("levelFilter").value;
            const search = document.getElementById("search").value.toLowerCase();
            try {
                const res = await fetch("/logs");
                if (!res.ok) return;
                const text = await res.text();
                if (!text || !text.trim()) return;
                const logs = JSON.parse(text);
                const box = document.getElementById("logBox");
                box.innerHTML = "";
                logs.forEach(log => {
                    if (level && log.level !== level) return;
                    if (search && !log.message.toLowerCase().includes(search)) return;
                    const div = document.createElement("div");
                    div.className = `log ${log.level}`;
                    div.textContent = `[${log.time}] ${log.level} • ${log.message}`;
                    box.appendChild(div);
                });
            } catch (e) { /* silently ignore transient fetch/parse errors */ }
        }
        setInterval(loadLogs, 2000);
        window.onload = loadLogs;
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/logs")
def get_logs():
    try:
        return jsonify(list(LOGS))
    except Exception:
        return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
