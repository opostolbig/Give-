import telebot
from telebot import types
import json
import random
import string
import requests
import time
from datetime import datetime, timedelta
from aiocryptopay import AioCryptoPay, Networks
import asyncio

# Инициализация бота
API_TOKEN = '7795536845:AAGvBiDeTm2UHNpe-SI_QXz0NrdXBb2QB5o'
bot = telebot.TeleBot(API_TOKEN)

# Токен CryptoPay
CRYPTO_PAY_TOKEN = '7788959684:AAFM4UkDux1O-7eaNnmS8BkQiyMBkdnKC7c'
crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

# Создаем новый event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Инициализация базы данных
DATABASE_FILE = 'database.json'

def load_database():
    try:
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_database(data):
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Загрузка базы данных
user_database = load_database()

def get_address_from_coordinates(latitude, longitude):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': float(latitude),
        'lon': float(longitude),
        'format': 'json',
        'addressdetails': 1,
        'accept-language': 'ru'
    }
    headers = {
        'User-Agent': 'YourBotName/1.0 (your_email@example.com)'
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('display_name', 'Адрес не найден')
        else:
            print(f"Ошибка: {response.status_code}, {response.text}")
            return 'Ошибка при получении адреса'
    except requests.RequestException as e:
        print(f"Исключение: {e}")
        return 'Ошибка при подключении к серверу'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.chat.id)
    if user_id not in user_database or 'location' not in user_database[user_id]:
        markup = types.InlineKeyboardMarkup()
        agreement_button = types.InlineKeyboardButton(
            text='🔒Соглашение', url='https://telegra.ph/Soglashenie-01-11-3'
        )
        send_location_button = types.InlineKeyboardButton(
            text='🌍 Отправить', callback_data='send_location'
        )
        markup.add(agreement_button, send_location_button)

        bot.send_message(
            message.chat.id,
            '<blockquote>📢 Для использования бота, пожалуйста, ознакомьтесь с соглашением и отправьте свою геопозицию.</blockquote>',
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        bot.send_message(
            message.chat.id,
            '<b>Вы уже отправляли свою геопозицию.</b> 📚 Введите /main_menu для работы с ботом.',
            parse_mode='HTML'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'send_location')
def request_location(call):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    location_button = types.KeyboardButton(text='🌍 Отправить геопозицию', request_location=True)
    markup.add(location_button)

    bot.send_message(
        call.message.chat.id,
        '<b>Пожалуйста, нажмите кнопку ниже</b>, чтобы отправить свою геопозицию:',
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.message_handler(content_types=['location'])
def save_location(message):
    if message.location:
        user_id = str(message.chat.id)
        if user_id not in user_database or 'location' not in user_database[user_id]:
            user_database[user_id] = user_database.get(user_id, {})
            user_database[user_id]['location'] = {
                'latitude': message.location.latitude,
                'longitude': message.location.longitude
            }
            save_database(user_database)

            bot.send_message(
                message.chat.id,
                '📃 <b>Ваше местоположение сохранено.</b> Введите /main_menu для продолжения.',
                parse_mode='HTML'
            )
        else:
            bot.send_message(
                message.chat.id,
                'ℹ️ Вы уже отправляли свою геопозицию. Введите /main_menu для работы с ботом.',
                parse_mode='HTML'
            )

@bot.message_handler(commands=['main_menu'])
def main_menu(message):
    user_id = str(message.chat.id)
    markup = types.InlineKeyboardMarkup()
    find_button = types.InlineKeyboardButton(
        text='🔍 Найти пользователя', callback_data='find_user'
    )
    markup.add(find_button)
    
    if not user_database.get(user_id, {}).get('banned', False):
        support_button = types.InlineKeyboardButton(
            text='🆘 Поддержка', callback_data='support'
        )
        markup.add(support_button)
    
    if not user_database.get(user_id, {}).get('white_list', False):
        white_list_button = types.InlineKeyboardButton(
            text='💎 Купить White List', callback_data='buy_white_list'
        )
        markup.add(white_list_button)

    bot.send_message(
        message.chat.id,
        '<b>🔧 Главное меню:</b>\n<blockquote> - Нажмите "Найти пользователя", чтобы получить информацию о местоположении пользователя по ID.\n - Нажмите "Поддержка", если вам нужна помощь.\n - Нажмите "Купить White List" для защиты вашей геопозиции.</blockquote>',
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'find_user')
def find_user(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='<b>Введите ID пользователя</b>, чтобы найти его геопозицию:',
        parse_mode='HTML'
    )

    bot.register_next_step_handler(call.message, search_user_location)

def search_user_location(message):
    user_id = message.text
    searcher_id = str(message.chat.id)

    try:
        sticker = bot.send_sticker(
            message.chat.id,
            'CAACAgEAAxkBAAELhBJngfqlUCjpMwxz79UjV6GPO12PdAACxQIAAkeAGUTTk7G7rIZ7GjYE'
        )

        time.sleep(2)

        bot.delete_message(message.chat.id, sticker.message_id)

        if user_id in user_database and 'location' in user_database[user_id]:
            if user_database[user_id].get('white_list', False):
                bot.send_message(
                    message.chat.id,
                    "🔒 Данные скрыты. У пользователя активирован White List.",
                    parse_mode='HTML'
                )

                markup = types.InlineKeyboardMarkup()
                user_profile_button = types.InlineKeyboardButton(
                    text="Профиль интересующегося",
                    url=f"https://t.me/{message.from_user.username}"
                )
                markup.add(user_profile_button)

                bot.send_message(
                    user_id,
                    f"📩 Пользователь с ID {searcher_id} интересовался вашей геопозицией, но она защищена White List.",
                    reply_markup=markup
                )
            else:
                location = user_database[user_id]['location']
                latitude = location["latitude"]
                longitude = location["longitude"]

                address = get_address_from_coordinates(latitude, longitude)

                bot.send_message(
                    message.chat.id,
                    f'<b>🔍 Геопозиция пользователя <code>{user_id}</code> найдена:</b>\n\n'
                    f'<blockquote>Широта: {latitude}\n'
                    f'Долгота: {longitude}\n\n'
                    f'Адрес:<code> {address}</code></blockquote>\n\n'
                    f'<a href="https://www.google.com/maps?q={latitude},{longitude}">Открыть в Google Maps</a>',
                    parse_mode='HTML'
                )

                bot.send_message(
                    user_id,
                    f"🔎 <b>Вашей геопозицией интересовался пользователь:</b> <code>{searcher_id}</code>",
                    parse_mode='HTML'
                )
        else:
            bot.send_message(message.chat.id, '🔍 Пользователь не найден или его геопозиция отсутствует.', parse_mode='HTML')

    except Exception as e:
        print(f"Error sending sticker: {e}")
        bot.send_message(message.chat.id, '⚠️ Произошла ошибка при отправке стикера. Попробуйте позже.', parse_mode='HTML')

# Переменная для отслеживания аптайма
bot_start_time = time.time()

# Проверка на ID администратора
ADMIN_ID = '721151979'

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.chat.id) == ADMIN_ID:
        total_users = len(user_database)
        white_list_count = sum(1 for user in user_database.values() if user.get('white_list', False))
        uptime = time.time() - bot_start_time
        uptime_formatted = str(time.strftime('%H:%M:%S', time.gmtime(uptime)))

        admin_info = f"""
        <b>⚙ Admin Panel</b>

        <blockquote>
        <b>Кол-во людей:</b> <code>{total_users}</code>
        <b>Кол-во White List:</b> <code>{white_list_count}</code>
        <b>Аптайм:</b> <code>{uptime_formatted}</code>
        </blockquote>
        """

        markup = types.InlineKeyboardMarkup()
        send_broadcast_button = types.InlineKeyboardButton(text="✉️ Рассылка", callback_data="send_broadcast")
        markup.add(send_broadcast_button)

        bot.send_message(
            message.chat.id,
            admin_info,
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "⚠️ Доступ запрещен. Эта команда доступна только администратору.")

@bot.callback_query_handler(func=lambda call: call.data == "send_broadcast")
def send_broadcast(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="✉️ <b>Введите текст для рассылки:</b>",
        parse_mode='HTML'
    )

    bot.register_next_step_handler(call.message, process_broadcast_text)

def process_broadcast_text(message):
    broadcast_text = message.text

    confirmation_text = f"""
    ✉️ <b>Ваше сообщение:</b>
    <blockquote>{broadcast_text}</blockquote>
    """

    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text="✅ Отправить", callback_data=f"confirm_broadcast|{broadcast_text}")
    cancel_button = types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_broadcast")
    markup.add(confirm_button, cancel_button)

    bot.send_message(
        message.chat.id,
        confirmation_text,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_broadcast"))
def confirm_broadcast(call):
    broadcast_text = call.data.split("|")[1]

    for user_id in user_database:
        try:
            bot.send_message(user_id, broadcast_text)
        except Exception as e:
            print(f"Ошибка отправки рассылки пользователю {user_id}: {e}")

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="✅ Рассылка завершена."
    )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def cancel_broadcast(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ Рассылка отменена."
    )

@bot.message_handler(commands=['White'])
def white_list_command(message):
    if str(message.chat.id) != ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "⚠️ У вас нет прав для выдачи White List."
        )
        return

    args = message.text.split()

    if len(args) < 2:
        bot.send_message(
            message.chat.id,
            "⚠️ Пожалуйста, укажите ID пользователя, например: /White 123456789"
        )
        return

    user_id = args[1]

    if user_id in user_database:
        if user_database[user_id].get('white_list', False):
            bot.send_message(
                message.chat.id,
                f"❗ Пользователь {user_id} уже имеет White List. Геопозиция скрыта."
            )
            return

        markup = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton(text="✅ Подтвердить выдачу White List", callback_data=f"confirm_white_list_{user_id}")
        markup.add(confirm_button)

        bot.send_message(
            message.chat.id,
            f'<b>💎 Выдача White List </b>\n\n'
            f'👤<b>Пользователь:</b> <code>{user_id}</code>\n'
            f'🗂<b>Бд:</b> <code>Нет</code>\n\n'
            '<blockquote>Для выдачи White List нажмите кнопку ниже.</blockquote>',
            parse_mode='HTML',
            reply_markup=markup
        )

    else:
        bot.send_message(
            message.chat.id,
            f"🔍 Пользователь с ID {user_id} не найден в базе данных."
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_white_list_"))
def confirm_white_list(call):
    user_id = call.data.split("_")[-1]
    if user_id in user_database:
        user_database[user_id]['white_list'] = True
        save_database(user_database)

        bot.send_message(
            user_id,
            "💎 Вам был выдан White List! Ваша геопозиция теперь скрыта при поиске."
        )

        bot.send_message(
            call.message.chat.id,
            f"✅ White List успешно выдан пользователю {user_id}. Теперь его геопозиция скрыта."
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"<b>💎 Выдача White List </b>\n\n"
                 f'👤<b>Пользователь:</b> <code>{user_id}</code>\n'
                 f'🗂<b>Бд:</b> <code>Есть</code>\n\n'
                 "<blockquote>Пользователь успешно получил White List. Его геопозиция теперь скрыта при поиске.</blockquote>",
            parse_mode='HTML'
        )
    else:
        bot.send_message(call.message.chat.id, f"🔍 Пользователь с ID {user_id} не найден.")

@bot.callback_query_handler(func=lambda call: call.data == 'support')
def support_menu(call):
    user_id = str(call.message.chat.id)
    if user_database.get(user_id, {}).get('banned', False):
        bot.answer_callback_query(call.id, "Вы заблокированы и не можете использовать поддержку.")
        return

    markup = types.InlineKeyboardMarkup()
    support_button = types.InlineKeyboardButton(text="Поддержка", url="t.me/alleexxanddeerr")
    chat_button = types.InlineKeyboardButton(text="Чат", callback_data="open_support_chat")
    markup.add(support_button, chat_button)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Пожалуйста, выберите вариант подходящий вам 😁",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'open_support_chat')
def open_support_chat(call):
    chat_id = str(call.message.chat.id)
    if user_database.get(chat_id, {}).get('banned', False):
        bot.answer_callback_query(call.id, "Вы заблокированы и не можете использовать поддержку.")
        return

    ticket_number = random.randint(1000, 9999)
    user_database[chat_id] = user_database.get(chat_id, {})
    user_database[chat_id]['support_chat'] = True
    user_database[chat_id]['ticket_number'] = ticket_number
    save_database(user_database)

    markup = types.InlineKeyboardMarkup()
    end_chat_button = types.InlineKeyboardButton(text="Завершить диалог", callback_data="end_support_chat")
    markup.add(end_chat_button)

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"👋 Вы открыли чат с поддержкой {ticket_number}\n\n"
             "> Задайте любой вопрос касающийся бота и поддержка постарается ответить на него",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: user_database.get(str(message.chat.id), {}).get('support_chat', False))
def handle_support_message(message):
    user_id = str(message.chat.id)
    admin_id = ADMIN_ID

    markup = types.InlineKeyboardMarkup()
    ban_button = types.InlineKeyboardButton(text="Забанить", callback_data=f"ban_user_{user_id}")
    markup.add(ban_button)

    bot.send_message(
        admin_id,
        f"Пользователь - @{message.from_user.username} | {user_id}\n\n"
        f"Сообщение - {message.text}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('ban_user_'))
def ban_user(call):
    user_id = call.data.split('_')[2]
    user_database[user_id] = user_database.get(user_id, {})
    user_database[user_id]['banned'] = True
    save_database(user_database)
    bot.answer_callback_query(call.id, "Пользователь забанен")
    
    # Завершаем чат с поддержкой для забаненного пользователя
    end_support_chat_for_user(user_id)
    
    bot.send_message(user_id, "Вы были забанены администратором. Ваш доступ к боту ограничен.")

def end_support_chat_for_user(user_id):
    if user_id in user_database:
        user_database[user_id]['support_chat'] = False
        user_database[user_id]['ticket_number'] = None
        save_database(user_database)
        bot.send_message(user_id, "Чат с поддержкой завершен.")

@bot.callback_query_handler(func=lambda call: call.data == 'end_support_chat')
def end_support_chat(call):
    chat_id = str(call.message.chat.id)
    end_support_chat_for_user(chat_id)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="Чат с поддержкой завершен."
    )

@bot.callback_query_handler(func=lambda call: call.data == 'buy_white_list')
def buy_white_list(call):
    bot.answer_callback_query(call.id)
    
    async def create_invoice():
        invoice = await crypto.create_invoice(asset='USDT', amount='1.5')
        return invoice

    invoice = loop.run_until_complete(create_invoice())
    
    markup = types.InlineKeyboardMarkup()
    pay_button = types.InlineKeyboardButton(text="🔗 Оплатить", url=invoice.pay_url)
    check_button = types.InlineKeyboardButton(text="♻️ Проверить оплату", callback_data=f"check_payment_{invoice.invoice_id}")
    markup.add(pay_button, check_button)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="💎 Покупка подписки на White List\n\n"
             "Цена - <code>1.5 USDT</code>\n\n"
             "⭐ Преимущество\n"
             "<blockquote>Вашу геопозицию могут найти, White List скроет её и пришлет уведомление, оформите подписку.</blockquote>",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_payment_'))
def check_payment(call):
    bot.answer_callback_query(call.id)
    invoice_id = int(call.data.split('_')[2])
    
    async def get_invoice():
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        return invoices[0] if invoices else None

    invoice = loop.run_until_complete(get_invoice())

    if invoice:
        if invoice.status == 'active':
            markup = types.InlineKeyboardMarkup()
            check_again_button = types.InlineKeyboardButton(text="🔄 Проверить снова", callback_data=f"check_payment_{invoice_id}")
            new_invoice_button = types.InlineKeyboardButton(text="🆕 Создать новый счет", callback_data="buy_white_list")
            main_menu_button = types.InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
            markup.add(check_again_button, new_invoice_button, main_menu_button)

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❗ Оплата не обнаружена. Пожалуйста, выберите действие:",
                reply_markup=markup
            )
        elif invoice.status == 'paid':
            user_id = str(call.from_user.id)
            user_database[user_id]['white_list'] = True
            save_database(user_database)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ Оплата прошла успешно! White List активирован для вашего аккаунта.",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data="main_menu")
                )
            )
    else:
        bot.answer_callback_query(call.id, f"Счёт {invoice_id} не найден.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def return_to_main_menu(call):
    bot.answer_callback_query(call.id)
    main_menu(call.message)

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)