import asyncio
import logging
import sqlite3
import re
import uuid
import sys
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions
from pyrogram.errors import (
    PeerIdInvalid, UsernameInvalid, UserNotParticipant, 
    ChatAdminRequired, FloodWait, ChannelInvalid, 
    ChannelPrivate, UsernameNotOccupied
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация бота
app = Client(
    "SHARK_bot",
    api_id=23258474,
    api_hash="f5dd3f52675030a650ca2259f9fb79ce",
    bot_token="8484896113:AAFWaHofoLQWr4eLAu0KdHy0sb0uym77Dvk",
    sleep_threshold=30
)

# Владельцы бота
OWNERS = {
    "BACHHIRA": {
        "id": "7279068300",
        "username": "BachiraOFFICIAL"
    },
    "дед мороз": {
        "id": "67676767",
        "username": "XYI"
    }
}

OWNER_PHOTO_PATH = "owner_card.png"

# Изображения для ролей
ROLE_IMAGES = {
    "Нет в базе": "https://i.ibb.co/TDYJz0Jg/1000036395.jpg",
    "Проверен гарантом": "https://i.ibb.co/7tV1B8RX/1000036402.jpg",
    "Скаммер": "https://i.ibb.co/CsQXwGxs/1000036406.jpg",
    "Возможно скаммер": "https://i.ibb.co/7dYZVrx5/IMG-20251215-180030-247.jpg",
    "Гарант": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Стажер": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Админ": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Директор": "https://i.ibb.co/0y4wmkGD/IMG-20251215-180030-188.jpg",
    "Президент": "https://i.ibb.co/4Zdx3sKL/IMG-20251215-180029-804.jpg",
    "Создатель": "https://i.ibb.co/4R6nWfbL/1000036399.jpg",
    "Заместитель": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Кодер": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Модератор": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg",
    "Дизайнер": "https://i.ibb.co/35vfpZ4c/IMG-20251215-180029-911.jpg"
}

SCAM_RATING_OPTIONS = {
    1: {"text": "1 - Возможно скам", "chance": "70-80%", "role_name": "Возможно скаммер"},
    2: {"text": "2 - Сомнительная репутация", "chance": "59-65%", "role_name": "Возможно скаммер"},
    3: {"text": "3 - Петух", "chance": "90-99%", "role_name": "Скаммер"},
    4: {"text": "4 - СКАММЕР", "chance": "100%", "role_name": "Скаммер"},
}

# Лимиты и кэши
RATE_LIMITS = {}
CHECK_LIMIT_SECONDS = 5
PENDING_SCAM_ENTRIES = {}
MENTOR_REQUESTS = {}

STAFF_CACHE = {
    'admins': [], 'coders': [], 'employees': [], 'volunteers': [], 
    'moderators': [], 'directors': [], 'presidents': [], 'designers': []
}
USER_INFO_CACHE = {}

# Инициализация базы данных
def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect('SHARK_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Создание таблиц
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scammers (
            user_id TEXT PRIMARY KEY, 
            reason TEXT, 
            proof_link TEXT, 
            scam_rating INTEGER DEFAULT 4
        )
    """)

    cursor.execute("CREATE TABLE IF NOT EXISTS presidents (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS directors (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS trusted (user_id TEXT PRIMARY KEY, guarantor_id TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS volunteers (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS coders (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS employees (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS moderators (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS designers (user_id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS reputation (user_id TEXT PRIMARY KEY, count INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id TEXT PRIMARY KEY, country TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS reprimands (user_id TEXT PRIMARY KEY, count INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS mentorship (volunteer_id TEXT PRIMARY KEY, mentor_id TEXT)")
    
    conn.commit()
    return conn, cursor

# Глобальные переменные для БД
conn, cursor = init_database()

# Вспомогательные функции
def get_russian_date():
    """Возвращает текущую дату на русском языке"""
    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    now = datetime.now()
    return f"{now.day} {months[now.month - 1]} {now.year} | {now.strftime('%H:%M')}"

def get_clean_id(text):
    """Очищает идентификатор от @ и лишних пробелов"""
    if text:
        return text.lstrip("@").strip()
    return ""

def is_owner(user_id, username):
    """Проверяет, является ли пользователь владельцем"""
    user_id_str = str(user_id)
    username_lower = username.lower() if username else None
    
    # Проверка по ID
    for owner_name, owner_data in OWNERS.items():
        if owner_data["id"] == user_id_str:
            return True
    
    # Проверка по username
    if username_lower:
        for owner_name, owner_data in OWNERS.items():
            if owner_data["username"] and owner_data["username"].lower() == username_lower:
                return True
    
    return False

def is_president(user_id):
    cursor.execute("SELECT 1 FROM presidents WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_director(user_id):
    cursor.execute("SELECT 1 FROM directors WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_admin(user_id):
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_coder(user_id):
    cursor.execute("SELECT 1 FROM coders WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_employee(user_id):
    cursor.execute("SELECT 1 FROM employees WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_moderator(user_id): 
    cursor.execute("SELECT 1 FROM moderators WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_designer(user_id):
    cursor.execute("SELECT 1 FROM designers WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def is_volunteer(user_id):
    cursor.execute("SELECT 1 FROM volunteers WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None

def get_all_moderators():
    cursor.execute("SELECT user_id FROM moderators")
    return [row[0] for row in cursor.fetchall()]

def is_full_staff(user_id, username):
    """Проверяет полный доступ (владелец, президент, кодер, админ)"""
    if is_owner(user_id, username): 
        return True
    if is_president(user_id): 
        return True
    if is_coder(user_id): 
        return True
    return is_admin(user_id)

def can_moderate(user_id, username):
    """Проверяет права на модерацию"""
    if is_full_staff(user_id, username): 
        return True
    if is_director(user_id): 
        return True
    return is_employee(user_id)

def can_temp_moderate(user_id, username):
    """Проверяет временные права на модерацию"""
    if can_moderate(user_id, username): 
        return True
    if is_volunteer(user_id): 
        return True
    return is_moderator(user_id)

def is_any_staff(user_id, username=None):
    """Проверяет, является ли пользователь любым сотрудником"""
    if username and is_owner(user_id, username): 
        return True
    if is_president(user_id): 
        return True
    if is_director(user_id): 
        return True
    if is_admin(user_id) or is_coder(user_id) or is_employee(user_id) or is_moderator(user_id) or is_volunteer(user_id) or is_designer(user_id):
        return True
    return False

def get_reputation(user_id):
    cursor.execute("SELECT count FROM reputation WHERE user_id = ?", (str(user_id),))
    res = cursor.fetchone()
    return res[0] if res else 0

def db_increment_reputation(user_id):
    cursor.execute("""
        INSERT INTO reputation (user_id, count) VALUES (?, 1) 
        ON CONFLICT(user_id) DO UPDATE SET count = count + 1
    """, (str(user_id),))
    conn.commit()

def set_mentor(volunteer_id, mentor_id):
    cursor.execute("INSERT OR REPLACE INTO mentorship (volunteer_id, mentor_id) VALUES (?, ?)", 
                   (str(volunteer_id), str(mentor_id)))
    conn.commit()

def get_mentor_id(volunteer_id):
    cursor.execute("SELECT mentor_id FROM mentorship WHERE volunteer_id = ?", (str(volunteer_id),))
    res = cursor.fetchone()
    return res[0] if res else None

def get_reprimands_count(user_id):
    cursor.execute("SELECT count FROM reprimands WHERE user_id = ?", (str(user_id),))
    res = cursor.fetchone()
    return res[0] if res else 0

def add_reprimand(user_id):
    cursor.execute("""
        INSERT INTO reprimands (user_id, count) VALUES (?, 1) 
        ON CONFLICT(user_id) DO UPDATE SET count = count + 1
    """, (str(user_id),))
    conn.commit()
    return get_reprimands_count(user_id)

def clear_reprimands(user_id):
    cursor.execute("DELETE FROM reprimands WHERE user_id = ?", (str(user_id),))
    conn.commit()

def remove_all_staff_roles(user_id):
    """Удаляет все роли сотрудника"""
    tables = ['presidents', 'directors', 'admins', 'coders', 'moderators', 'employees', 'volunteers', 'designers']
    for table in tables:
        cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (str(user_id),))
    conn.commit()

def db_set_country(user_id, country_text):
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, country) VALUES (?, ?)", 
                   (str(user_id), country_text))
    conn.commit()

def db_get_country(user_id):
    cursor.execute("SELECT country FROM user_settings WHERE user_id = ?", (str(user_id),))
    res = cursor.fetchone()
    return res[0] if res else "Unknown"

def db_add_scammer_final(user_id, reason, proof_link, scam_rating):
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO scammers (user_id, reason, proof_link, scam_rating) 
            VALUES (?, ?, ?, ?)
        """, (str(user_id), reason, proof_link, scam_rating))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении скаммера: {e}")
        return False

def db_delete(table, user_id):
    cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (str(user_id),))
    conn.commit()
    return cursor.rowcount > 0

async def get_message_link(client, message):
    """Генерирует ссылку на сообщение"""
    try:
        chat_id = message.chat.id
        message_id = message.id
        if message.chat.username:
            return f"https://t.me/{message.chat.username}/{message_id}"
        else:
            raw_chat_id = str(chat_id).replace('-100', '')
            return f"https://t.me/c/{raw_chat_id}/{message_id}"
    except Exception as e:
        logger.error(f"Ошибка получения ссылки на сообщение: {e}")
        return f"(Ссылка недоступна, ID чата: {message.chat.id})"

async def get_guarantor_link(client, target_id):
    """Получает ссылку на гаранта"""
    cursor.execute("SELECT guarantor_id FROM trusted WHERE user_id = ?", (str(target_id),))
    res = cursor.fetchone()
    if not res or not res[0]:
        return None
    
    guarantor_id = res[0]
    try:
        guarantor_info = await client.get_users(int(guarantor_id))
        name = guarantor_info.first_name
        username = guarantor_info.username
        
        if username:
            link = f"https://t.me/{username}"
            display_name = f"**{name}** (@{username})"
        else:
            link = f"tg://user?id={guarantor_id}"
            display_name = f"**{name}** (ID: {guarantor_id})"
        
        return f"💠 **Проверен гарантом:** [Гарант {display_name}]({link})"
    except Exception as e:
        logger.error(f"Ошибка получения информации о гаранте: {e}")
        return None

async def get_mentor_link(client, volunteer_id):
    """Получает ссылку на куратора"""
    mentor_id = get_mentor_id(volunteer_id)
    if not mentor_id:
        return None
    
    try:
        mentor_info = await client.get_users(int(mentor_id))
        name = mentor_info.first_name
        username = mentor_info.username
        
        if username:
            link = f"https://t.me/{username}"
            display_name = f"**{name}** (@{username})"
        else:
            link = f"tg://user?id={mentor_id}"
            display_name = f"**{name}** (ID: {mentor_id})"

        return f"\n🎓 **Куратор:** [Куратор {display_name}]({link})"
    except Exception as e:
        logger.error(f"Ошибка получения информации о кураторе: {e}")
        return None

def determine_user_role(user_id, username):
    """Определяет роль пользователя для выбора изображения"""
    if is_owner(user_id, username):
        return "Создатель"
    elif is_president(user_id):
        return "Президент"
    elif is_director(user_id):
        return "Директор"
    elif is_admin(user_id):
        return "Админ"
    elif is_coder(user_id):
        return "Кодер"
    elif is_designer(user_id):
        return "Дизайнер"
    elif is_employee(user_id):
        return "Заместитель"
    elif is_moderator(user_id):
        return "Модератор"
    elif is_volunteer(user_id):
        return "Стажер"
    elif cursor.execute("SELECT 1 FROM trusted WHERE user_id = ?", (str(user_id),)).fetchone():
        return "Проверен гарантом"
    elif cursor.execute("SELECT 1 FROM scammers WHERE user_id = ?", (str(user_id),)).fetchone():
        scam_data = cursor.execute("SELECT scam_rating FROM scammers WHERE user_id = ?", (str(user_id),)).fetchone()
        if scam_data and scam_data[0] is not None:
            rating = scam_data[0]
            if rating in [3, 4]:
                return "Скаммер"
            elif rating in [1, 2]:
                return "Возможно скаммер"
    return "Нет в базе"

def generate_card_text(t_id, t_username, t_name, guarantor_link=None, mentor_link=None):
    """Генерирует текст карточки пользователя"""
    t_id = str(t_id)
    country = db_get_country(t_id)
    is_owner_flag = is_owner(t_id, t_username)
    is_president_flag = is_president(t_id)
    is_coder_flag = is_coder(t_id)
    is_director_flag = is_director(t_id)
    is_admin_flag = is_admin(t_id)
    is_employee_flag = is_employee(t_id)
    is_moderator_flag = is_moderator(t_id)
    is_volunteer_flag = is_volunteer(t_id)
    is_designer_flag = is_designer(t_id)
    
    staff_label = ""
    reprimand_text = ""
    trusted_label = ""
    mentor_label = ""

    if is_any_staff(t_id, t_username):
        count = get_reprimands_count(t_id)
        reprimand_text = f"\n⚠️ **Количество выговоров:** {count}/3"
    
    scam_data = cursor.execute("SELECT reason, proof_link, scam_rating FROM scammers WHERE user_id = ?", (t_id,)).fetchone()
    
    if scam_data:
        reason = scam_data[0] or "Мошенничество"
        proof_link = scam_data[1]
        scam_rating = scam_data[2] if scam_data[2] is not None else 4
        rating_info = SCAM_RATING_OPTIONS.get(scam_rating, SCAM_RATING_OPTIONS[4])
        status, chance, color, footer = rating_info["text"], rating_info["chance"], "❌", f"⚠️ ПРИЧИНА: {reason}"
        if proof_link:
            footer += f"\n🔗 **ДОКАЗАТЕЛЬСТВА:** [Нажмите, чтобы увидеть пруфы]({proof_link})"
    elif is_owner_flag:
        # Определяем имя владельца для отображения
        owner_name = None
        for name, data in OWNERS.items():
            if data["id"] == t_id or (data["username"] and data["username"].lower() == str(t_username).lower()):
                owner_name = name
                break
        
        status, chance, color, footer = "Владелец 👑", "0%", "✅", "Доверенный владелец SHARK."
        t_name = owner_name or t_name
        t_id = OWNERS.get(owner_name, {}).get("id", t_id)
    elif is_president_flag:
        status, chance, color, footer = "Президент 👑", "0%", "✅", "Высшая административная должность."
    elif is_coder_flag:
        status, chance, color, footer = "Кодер 💻", "0%", "✅", "Разработчик платформы."
    elif is_designer_flag:
        status, chance, color, footer = "Дизайнер 🎨", "0%", "✅", "Дизайнер платформы."
    elif is_director_flag:
        status, chance, color, footer = "Директор 🎯", "0%", "✅", "Руководитель проекта."
    elif is_admin_flag:
        status, chance, color, footer = "Гарант SHARK 🛡", "0%", "✅", "Официальный гарант сервиса SHARK."
    elif is_employee_flag:
        status, chance, color, footer = "Сотрудник SHARK 💼", "1-5%", "✅", "Сотрудник сервиса, имеет право модерации."
        staff_label = " ✅ [Персонал базы]"
    elif is_moderator_flag:
        status, chance, color, footer = "Модератор SHARK 🔨", "15-30%", "✅", "Сотрудник, следящий за порядком в чатах."
        staff_label = " ✅ [Персонал базы]"
    elif is_volunteer_flag:
        status, chance, color, footer = "Волонтер (Стажер) 🎩", "5-15%", "✅", "Официальный волонтер сервиса."
        staff_label = " ✅ [Персонал базы]"
    elif cursor.execute("SELECT 1 FROM trusted WHERE user_id = ?", (t_id,)).fetchone():
        status, chance, color, footer = "Проверен гарантом 💠", "10-25%", "✅", "Пользователь имеет доверие сервиса."
        if guarantor_link:
            trusted_label = f"\n{guarantor_link}"
    else:
        status, chance, color, footer = "Не найден в базе 👤", "40-50%", "⚠️", "Человека нет в базе (Риск присутствует)."

    if is_volunteer_flag and mentor_link:
        mentor_label = mentor_link

    leaked = get_reputation(t_id)
    display_link = f"@{t_username}" if t_username else "Нет юзернейма"
    
    if is_owner_flag and country == "Unknown":
        country = "Azerbaijan 🇦🇿"
    
    id_display = f"[`{t_id}`]"

    text = (
        f"👤 **{t_name}** | {display_link} | {id_display}\n\n"
        f"{color} **Статус:** {status}\n"
        f"📉 **Шанс скама:** {chance}{staff_label}{reprimand_text}{trusted_label}{mentor_label}\n"
        f"🌍 **Страна:** {country}\n"
        f"🚫 **Скаммеров слито:** {leaked}\n\n"
        f"{footer}\n"
        f"Всегда идите через гарантов **SHARK**, чтобы сделки проходили безопасно.\n\n"
        f"📅 {get_russian_date()} | 🤖 @SHARKBOT_ANTISCAMBOT"
    )
    
    # Определяем роль для изображения
    role = determine_user_role(t_id, t_username)
    image_url = ROLE_IMAGES.get(role, ROLE_IMAGES["Нет в базе"])
    
    # Добавляем скрытую ссылку на изображение в начало текста
    text_with_image = f"[⁠]({image_url})" + text
    
    return text_with_image, is_owner_flag, role

def get_profile_keyboard(user_id, username):
    """Создает клавиатуру с ссылкой на профиль"""
    if username:
        url = f"https://t.me/{username}"
    else:
        url = f"tg://user?id={user_id}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Профиль пользователя", url=url)]])

async def find_target(client, message, arg_text=None):
    """Находит цель по ID или юзернейму"""
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            return message.reply_to_message.from_user, None
        
        if not arg_text:
            return None, None
        
        clean = get_clean_id(arg_text)
        if clean.lower() in ["ми", "me", "я"]:
            return message.from_user, None

        # Проверка кэша
        if clean.isdigit() and str(clean) in USER_INFO_CACHE:
            cached_info = USER_INFO_CACHE[str(clean)]
            class CachedUser:
                id = cached_info['id']
                username = cached_info.get('username')
                first_name = cached_info['name']
                is_bot = False
            return CachedUser(), None

        # Попытка найти пользователя
        try:
            if clean.isdigit():
                chat = await client.get_users(int(clean))
            else:
                # Убираем @ если есть
                username_clean = clean.lstrip('@')
                chat = await client.get_users(username_clean)
            
            if chat:
                USER_INFO_CACHE[str(chat.id)] = {
                    'id': str(chat.id),
                    'name': chat.first_name,
                    'username': chat.username
                }
            
            return chat, None
        except (UsernameInvalid, UsernameNotOccupied):
            return None, clean
        except (PeerIdInvalid, ChannelInvalid, ChannelPrivate):
            return None, clean
        except Exception as e:
            logger.error(f"Ошибка поиска цели: {e}")
            return None, clean
            
    except Exception as e:
        logger.error(f"Ошибка в функции find_target: {e}")
        return None, None

# Клавиатуры
def main_menu_keyboard():
    """Главное меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Мой профиль ℹ️", callback_data="my_profile")],
        [
            InlineKeyboardButton("Слить скаммера 😡", callback_data="report_scam"),
            InlineKeyboardButton("Частые вопросы ❓", callback_data="faq")
        ],
        [
            InlineKeyboardButton("Гаранты 🔥", callback_data="list_admins"),
            InlineKeyboardButton("Директора 🎯", callback_data="list_directors"),
            InlineKeyboardButton("Президенты 👑", callback_data="list_presidents"),
            InlineKeyboardButton("Сотрудники 💼", callback_data="list_employees")
        ],
        [
            InlineKeyboardButton("Модераторы 🔨", callback_data="list_moderators"),
            InlineKeyboardButton("Волонтёры 🌴", callback_data="list_volunteers"),
            InlineKeyboardButton("Дизайнеры 🎨", callback_data="list_designers")
        ],
        [
            InlineKeyboardButton("Статистика 📊", callback_data="stats"),
            InlineKeyboardButton("Премиум 🌸", callback_data="premium")
        ]
    ])

def select_country_keyboard():
    """Клавиатура выбора страны"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇷🇺 Россия", callback_data="country_Russia 🇷🇺"),
            InlineKeyboardButton("🇺🇦 Украина", callback_data="country_Ukraine 🇺🇦")
        ],
        [
            InlineKeyboardButton("🇧🇾 Беларусь", callback_data="country_Belarus 🇧🇾"),
            InlineKeyboardButton("🇰🇿 Казахстан", callback_data="country_Kazakhstan 🇰🇿")
        ],
        [
            InlineKeyboardButton("🇩🇪 Германия", callback_data="country_Germany 🇩🇪"),
            InlineKeyboardButton("🇫🇷 Франция", callback_data="country_France 🇫🇷")
        ],
        [
            InlineKeyboardButton("🇵🇱 Польша", callback_data="country_Poland 🇵🇱"),
            InlineKeyboardButton("🇺🇸 США", callback_data="country_USA 🇺🇸")
        ],
        [
            InlineKeyboardButton("🇦🇿 Азербайджан", callback_data="country_Azerbaijan 🇦🇿"),
            InlineKeyboardButton("🏳️ Скрыть", callback_data="country_Unknown")
        ],
        [InlineKeyboardButton("🔙 Назад в профиль", callback_data="my_profile")]
    ])

def back_to_menu_keyboard():
    """Кнопка возврата в меню"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]])

def get_scam_rating_keyboard():
    """Клавиатура выбора рейтинга скама"""
    buttons = []
    for rating, data in SCAM_RATING_OPTIONS.items():
        buttons.append([InlineKeyboardButton(f"{data['text']} ({data['chance']})", 
                       callback_data=f"set_scam_rating_{rating}")])
    return InlineKeyboardMarkup(buttons)

def staff_list_keyboard():
    """Клавиатура для списков персонала"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Президенты", callback_data="list_presidents"),
            InlineKeyboardButton("🎯 Директора", callback_data="list_directors")
        ],
        [
            InlineKeyboardButton("🔥 Гаранты", callback_data="list_admins"),
            InlineKeyboardButton("💼 Сотрудники", callback_data="list_employees")
        ],
        [
            InlineKeyboardButton("🔨 Модераторы", callback_data="list_moderators"),
            InlineKeyboardButton("🌴 Волонтеры", callback_data="list_volunteers")
        ],
        [
            InlineKeyboardButton("💻 Кодеры", callback_data="list_coders"),
            InlineKeyboardButton("🎨 Дизайнеры", callback_data="list_designers")
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    ])

async def fetch_staff_info():
    """Загружает информацию о персонале"""
    staff_tables = ['admins', 'coders', 'employees', 'volunteers', 
                   'moderators', 'directors', 'presidents', 'designers']
    
    for table in staff_tables:
        cursor.execute(f"SELECT user_id FROM {table}")
        user_ids = [row[0] for row in cursor.fetchall()]
        STAFF_CACHE[table] = []

        for user_id in user_ids:
            try:
                user_info = await app.get_users(int(user_id))
                info = {
                    'id': user_id,
                    'name': user_info.first_name,
                    'username': user_info.username
                }
                STAFF_CACHE[table].append(info)
                USER_INFO_CACHE[user_id] = info
            except Exception as e:
                logger.error(f"Ошибка получения информации о пользователе {user_id}: {e}")
                STAFF_CACHE[table].append({
                    'id': user_id,
                    'name': f"ID: {user_id}",
                    'username': None
                })

def parse_time(time_str):
    """Парсит время в формате 30m, 2h, 1d"""
    if not time_str:
        return None, "Не указано время."
    
    time_str = time_str.lower()
    match = re.match(r"(\d+)([smhd])", time_str)
    if not match:
        return None, "Ошибка формата. Используйте: 30s, 5m, 2h, 1d"
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 's':
        delta = timedelta(seconds=value)
    elif unit == 'm':
        delta = timedelta(minutes=value)
    elif unit == 'h':
        delta = timedelta(hours=value)
    elif unit == 'd':
        delta = timedelta(days=value)
    else:
        return None, "Неизвестная единица времени."
    
    return datetime.now() + delta, None

# Команды бота
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    """Обработчик команды /start"""
    await message.reply(
        "👋 **Добро пожаловать в SHARK AntiScam!**\n\n"
        "Я помогу тебе проверить пользователей на честность. Выбери действие:",
        reply_markup=main_menu_keyboard()
    )

@app.on_message(filters.command("mms"))
async def mms_cmd(client, message):
    """Команда для вывода списка гарантов"""
    admins_data = STAFF_CACHE.get('admins', [])
    
    if not admins_data:
        await message.reply("⚠️ **Гаранты не найдены.** Список пуст или не был загружен при запуске бота.")
        return

    text = "🔥 **Официальные Гаранты SHARK AntiScam:**\n\n"
    buttons = []
    
    for i, info in enumerate(admins_data, 1):
        name = info.get('name', f"ID: {info['id']}")
        username = info.get('username')
        
        text += f"{i}. 🛡️ **{name}** (@{username or 'Нет юзернейма'})\n"
        
        profile_url = f"https://t.me/{username}" if username else f"tg://user?id={info['id']}"
        buttons.append([InlineKeyboardButton(f"Профиль {name}", url=profile_url)])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply(text, reply_markup=reply_markup)

@app.on_message(filters.regex(r"^[!/]?модеры$", re.IGNORECASE) & filters.group)
async def moderator_call_cmd(client, message):
    """Вызов модераторов в чате"""
    caller = message.from_user
    moderator_ids = get_all_moderators()
    
    try:
        chat_link = await get_message_link(client, message)
    except Exception as e:
        logger.error(f"Не удалось сгенерировать ссылку на чат: {e}")
        chat_link = f"(Не удалось получить ссылку на чат)"

    if moderator_ids:
        notification_text = (
            f"🚨 **ВЫЗОВ МОДЕРАТОРОВ!**\n\n"
            f"👤 **Вызов от:** {caller.first_name} (@{caller.username or 'ID:' + str(caller.id)})\n"
            f"📢 **Чат:** {message.chat.title}\n"
            f"🔗 **Перейти к сообщению:** [Нажмите, чтобы ответить]({chat_link})"
        )
        
        for mod_id in moderator_ids:
            try:
                await client.send_message(int(mod_id), notification_text, disable_web_page_preview=True)
            except Exception as e:
                logger.warning(f"Не удалось уведомить модератора {mod_id}: {e}")

    await message.reply("✅ **Я вызвал модераторов!** Они получили уведомление в личные сообщения.")

@app.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    """Обработчик callback-запросов"""
    data = callback_query.data
    user = callback_query.from_user
    
    try:
        if data.startswith("approve_scam_"):
            req_id = data.split("_")[-1]
            request_data = MENTOR_REQUESTS.get(req_id)
            
            if not request_data:
                await callback_query.answer("❌ Запрос устарел или не найден.", show_alert=True)
                try:
                    await callback_query.message.delete()
                except:
                    pass
                return
            
            target_id = request_data['target_id']
            reason = request_data['reason']
            proof_link = request_data['proof_link']
            rating = request_data['rating']
            volunteer_id = request_data['volunteer_id']
            
            if db_add_scammer_final(target_id, reason, proof_link, rating):
                db_increment_reputation(volunteer_id)
                del MENTOR_REQUESTS[req_id]
                await callback_query.answer("✅ Запрос одобрен!")
                await callback_query.message.edit_text(f"✅ **Вы одобрили занесение!**\nID скамера: `{target_id}`")
                
                try:
                    await client.send_message(
                        int(volunteer_id),
                        f"✅ Ваш куратор **одобрил** ваш запрос на добавление пользователя `{target_id}` в базу!"
                    )
                except:
                    pass
            else:
                await callback_query.answer("Ошибка базы данных.", show_alert=True)

        elif data.startswith("reject_scam_"):
            req_id = data.split("_")[-1]
            request_data = MENTOR_REQUESTS.get(req_id)
            if request_data:
                volunteer_id = request_data['volunteer_id']
                del MENTOR_REQUESTS[req_id]
                await callback_query.answer("❌ Запрос отклонен.")
                await callback_query.message.edit_text("❌ **Вы отклонили запрос.**")
                
                try:
                    await client.send_message(
                        int(volunteer_id),
                        f"❌ Ваш куратор **отклонил** ваш запрос на добавление пользователя в базу."
                    )
                except:
                    pass
            else:
                await callback_query.answer("Запрос не найден.", show_alert=True)

        elif data.startswith("set_scam_rating_"):
            rating = int(data.split("_")[-1])
            if user.id not in PENDING_SCAM_ENTRIES:
                await callback_query.answer("❌ Срок ожидания команды истек.", show_alert=True)
                return
            
            target_id, reason, proof_link = PENDING_SCAM_ENTRIES.pop(user.id)
            
            is_regular_staff = can_moderate(user.id, user.username)
            
            if is_volunteer(user.id) and not is_regular_staff:
                mentor_id = get_mentor_id(user.id)
                if not mentor_id:
                    await callback_query.message.edit_text(
                        "❌ **Ошибка:** Вы волонтер, но у вас нет куратора. "
                        "Вы не можете заносить в базу самостоятельно."
                    )
                    return
                
                req_id = str(uuid.uuid4())[:8]
                MENTOR_REQUESTS[req_id] = {
                    'target_id': target_id,
                    'reason': reason,
                    'proof_link': proof_link,
                    'rating': rating,
                    'volunteer_id': user.id
                }
                
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_scam_{req_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_scam_{req_id}")
                    ]
                ])
                
                try:
                    await client.send_message(
                        int(mentor_id),
                        f"📩 **Запрос от подопечного** {user.first_name} (@{user.username})\n\n"
                        f"⚠️ Ваш подопечный хочет **занести в базу** пользователя:\n"
                        f"👤 **Скамер:** `{target_id}`\n"
                        f"📝 **Причина:** {reason}\n"
                        f"📊 **Рейтинг:** {SCAM_RATING_OPTIONS[rating]['text']}\n"
                        f"🔗 **Пруфы:** {proof_link}",
                        reply_markup=kb
                    )
                    await callback_query.message.edit_text("✅ **Запрос отправлен вашему куратору!** Ожидайте решения.")
                except Exception as e:
                    await callback_query.message.edit_text(
                        f"❌ Ошибка отправки куратору: {e}. Возможно, у него закрыта личка."
                    )
                return

            if db_add_scammer_final(target_id, reason, proof_link, rating):
                db_increment_reputation(user.id)
                rating_text = SCAM_RATING_OPTIONS[rating]['text']
                await callback_query.message.edit_text(
                    f"✅ **Пользователь добавлен в базу!**\n"
                    f"ID: `{target_id}`\n"
                    f"Рейтинг: **{rating_text}**\n"
                    f"Причина: `{reason}`"
                )
            else:
                await callback_query.answer("❌ Ошибка при сохранении.", show_alert=True)
            
            await callback_query.answer()
            return
        
        elif data == "my_profile":
            text, _, _ = generate_card_text(user.id, user.username, user.first_name)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏳️ Выбрать страну", callback_data="set_country")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ])
            await callback_query.message.edit_text(text, reply_markup=kb)
        
        elif data in ["list_admins", "list_volunteers", "list_employees", "list_coders", 
                      "list_moderators", "list_directors", "list_presidents", "list_designers"]:
            await callback_query.answer("Загружаю список...")
            role_map = {
                "list_presidents": ("presidents", "Президенты 👑", "👑"),
                "list_admins": ("admins", "Гаранты 🔥", "🛡"),
                "list_employees": ("employees", "Сотрудники 💼", "💼"),
                "list_coders": ("coders", "Кодеры 💻", "💻"),
                "list_moderators": ("moderators", "Модераторы 🔨", "🔨"),
                "list_directors": ("directors", "Директора 🎯", "🎯"),
                "list_volunteers": ("volunteers", "Волонтёры 🌴", "🎩"),
                "list_designers": ("designers", "Дизайнеры 🎨", "🎨"),
            }
            role_table, role_name, role_emoji = role_map.get(data)
            staff_list_text = f"✨ **Список {role_name}:**\n\n"
            staff_data = STAFF_CACHE.get(role_table, [])
            
            for i, info in enumerate(staff_data, 1):
                name = info.get('name', f"ID: {info['id']}")
                username = info.get('username')
                if username:
                    staff_list_text += f"{i}. {role_emoji} **{name}** (@{username})\n"
                else:
                    staff_list_text += f"{i}. {role_emoji} **{name}** (Контакт скрыт)\n"
            
            if not staff_data:
                staff_list_text += "Список пуст."
            
            await callback_query.message.edit_text(staff_list_text, reply_markup=back_to_menu_keyboard())
        
        elif data == "report_scam":
            await callback_query.message.edit_text(
                "😡 **Как слить скаммера?**\n\n"
                "Используйте команду: `/scam @username Причина СсылкаНаПруфы`.\n"
                "Доступно Персоналу SHARK.",
                reply_markup=back_to_menu_keyboard()
            )
        
        elif data == "faq":
            text = (
                "❓ **Частые вопросы (FAQ)**\n\n"
                "**Как проверить?** Напиши `Чек @username`.\n"
                "**Как стать Гарантом?** Статус выдает Владелец/Президент.\n"
                "**Как добавить скаммера?** Команда `/scam` доступна персоналу.\n"
                "**Как установить страну?** В профиле нажми 'Выбрать страну'."
            )
            await callback_query.message.edit_text(text, reply_markup=back_to_menu_keyboard())
        
        elif data == "stats":
            total_scammers = cursor.execute("SELECT COUNT(user_id) FROM scammers").fetchone()[0]
            total_presidents = cursor.execute("SELECT COUNT(user_id) FROM presidents").fetchone()[0]
            total_directors = cursor.execute("SELECT COUNT(user_id) FROM directors").fetchone()[0]
            total_admins = cursor.execute("SELECT COUNT(user_id) FROM admins").fetchone()[0]
            total_volunteers = cursor.execute("SELECT COUNT(user_id) FROM volunteers").fetchone()[0]
            total_coders = cursor.execute("SELECT COUNT(user_id) FROM coders").fetchone()[0]
            total_employees = cursor.execute("SELECT COUNT(user_id) FROM employees").fetchone()[0]
            total_moderators = cursor.execute("SELECT COUNT(user_id) FROM moderators").fetchone()[0]
            total_designers = cursor.execute("SELECT COUNT(user_id) FROM designers").fetchone()[0]
            total_rep = cursor.execute("SELECT IFNULL(SUM(count), 0) FROM reputation").fetchone()[0]
            
            text = (
                f"📊 **Статистика SHARK AntiScam**\n\n"
                f"⛔ Скамеров в базе: **{total_scammers}**\n"
                f"👑 Президентов: **{total_presidents}**\n"
                f"🎯 Директоров: **{total_directors}**\n"
                f"🛡 Гарантов: **{total_admins}**\n"
                f"💻 Кодеров: **{total_coders}**\n"
                f"🎨 Дизайнеров: **{total_designers}**\n"
                f"💼 Сотрудников: **{total_employees}**\n"
                f"🔨 Модераторов: **{total_moderators}**\n"
                f"🎩 Волонтеров (Стажеров): **{total_volunteers}**\n"
                f"🤝 Общая репутация (слито): **{total_rep}**\n"
            )
            await callback_query.message.edit_text(text, reply_markup=back_to_menu_keyboard())

        elif data == "premium":
            await callback_query.message.edit_text(
                "🌸 **Премиум-доступ**\n\n"
                "Функция находится в разработке. Скоро появится!",
                reply_markup=back_to_menu_keyboard()
            )
        
        elif data == "back_to_menu":
            await callback_query.message.edit_text(
                "👋 **Главное меню**\nВыбери действие:",
                reply_markup=main_menu_keyboard()
            )
        
        elif data == "set_country":
            await callback_query.answer()
            await callback_query.message.edit_text(
                "🌍 **Выберите вашу страну из списка:**",
                reply_markup=select_country_keyboard()
            )
        
        elif data.startswith("country_"):
            selected_country = data.split("_", 1)[1]
            db_set_country(user.id, selected_country)
            text, _, _ = generate_card_text(user.id, user.username, user.first_name)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏳️ Выбрать страну", callback_data="set_country")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ])
            await callback_query.answer(f"✅ Страна установлена: {selected_country}")
            await callback_query.message.edit_text(text, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике callback: {e}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте позже.")
        except:
            pass

# Команды управления персоналом
@app.on_message(filters.command("курировать"))
async def curate_cmd(client, message):
    """Назначение куратора для волонтера"""
    try:
        sender_id = message.from_user.id
        
        if not (is_president(sender_id) or is_director(sender_id) or is_owner(sender_id, message.from_user.username)):
            await message.reply("❌ Курировать могут только Президенты, Директора и Владельцы.")
            return

        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        
        if not target or not str(target.id).isdigit():
            await message.reply("⚠️ Пример: `/курировать @username`")
            return
        
        if not is_volunteer(target.id):
            await message.reply("❌ Курировать можно ТОЛЬКО волонтеров.")
            return

        set_mentor(target.id, sender_id)
        await message.reply(f"🎓 Вы назначены куратором для **{target.first_name}**!")
        try:
            await client.send_message(target.id, f"🎓 **{message.from_user.first_name}** назначен вашим куратором!")
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка в команде курировать: {e}")
        await message.reply("❌ Произошла ошибка при выполнении команды.")

@app.on_message(filters.command("выговор"))
async def reprimand_cmd(client, message):
    """Выдача выговора персоналу"""
    try:
        sender_id = message.from_user.id
        sender_username = message.from_user.username
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)

        if not target or not str(target.id).isdigit():
            await message.reply("⚠️ Пример: `/выговор @username` или ответьте на сообщение.")
            return
        
        t_id = target.id
        if t_id == sender_id:
            await message.reply("❌ Нельзя выдать выговор самому себе.")
            return
        if not is_any_staff(t_id, target.username):
            await message.reply("❌ Выговоры можно выдавать только персоналу.")
            return

        can_reprimand = False
        
        if is_owner(sender_id, sender_username) or is_coder(sender_id):
            can_reprimand = True
        elif is_president(sender_id):
            if is_director(t_id) or is_employee(t_id) or is_volunteer(t_id) or is_moderator(t_id):
                can_reprimand = True
            else:
                await message.reply("❌ Президент не может выдавать выговор вышестоящим или равным.")
                return
        elif is_director(sender_id):
            if is_employee(t_id) or is_volunteer(t_id) or is_moderator(t_id):
                can_reprimand = True
            else:
                await message.reply("❌ Директор может наказывать только Сотрудников, Волонтеров и Модераторов.")
                return
        else:
            await message.reply("❌ У вас недостаточно прав для выдачи выговоров.")
            return

        if can_reprimand:
            new_count = add_reprimand(t_id)
            
            if new_count >= 3:
                remove_all_staff_roles(t_id)
                clear_reprimands(t_id)
                await fetch_staff_info()
                await message.reply(
                    f"🚫 **УВОЛЬНЕНИЕ!**\n\n"
                    f"👤 Пользователь: **{target.first_name}**\n"
                    f"❗️ Достигнут лимит выговоров (3/3).\n"
                    f"❌ Все должности сняты автоматически."
                )
            else:
                await message.reply(
                    f"⚠️ **Выдан выговор!**\n\n"
                    f"👤 Пользователь: **{target.first_name}**\n"
                    f"🔢 Всего выговоров: **{new_count}/3**\n"
                    f"При достижении 3-х выговоров роль будет снята."
                )
    except Exception as e:
        logger.error(f"Ошибка в команде выговор: {e}")
        await message.reply("❌ Произошла ошибка при выполнении команды.")

@app.on_message(filters.command("мут") & filters.group)
async def mute_cmd(client, message):
    """Мут пользователя в группе"""
    try:
        if not can_temp_moderate(message.from_user.id, message.from_user.username):
            await message.reply("🛡 У вас нет прав.")
            return
        
        target_user = None
        time_str = None
        reason = "Без причины"
        
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            args = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else ""
            parts = args.split(maxsplit=1)
            time_str = parts[0] if parts else None
            reason = parts[1] if len(parts) > 1 else reason
        elif len(message.command) >= 3:
            target_str = message.command[1]
            time_str = message.command[2]
            reason = " ".join(message.command[3:]) if len(message.command) > 3 else reason
            try:
                target_user, _ = await find_target(client, message, target_str)
            except:
                pass
        
        if not target_user:
            await message.reply("⚠️ Пример: `/мут @username 30m` или ответьте на сообщение.")
            return
        
        if time_str:
            until_date, error = parse_time(time_str)
            if error:
                return await message.reply(f"❌ {error}")
        else:
            until_date = datetime.now() + timedelta(days=366)

        try:
            await client.restrict_chat_member(
                message.chat.id, 
                target_user.id, 
                ChatPermissions(), 
                until_date=until_date
            )
            await message.reply(f"🔨 Мут **{target_user.first_name}** на {time_str or 'навсегда'}. Причина: {reason}")
        except ChatAdminRequired:
            await message.reply("❌ У меня нет прав для мута в этом чате.")
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Ошибка в команде мут: {e}")
        await message.reply("❌ Произошла ошибка при выполнении команды.")

# Команды проверки
@app.on_message(filters.regex(r"(?i)^(чек|check|/check)\b"))
async def check_handler(client, message):
    """Обработчик команды проверки"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        current_time = datetime.now()
        is_staff_member = can_moderate(user_id, username)

        if not is_staff_member:
            if user_id in RATE_LIMITS:
                if (current_time - RATE_LIMITS[user_id]).total_seconds() < CHECK_LIMIT_SECONDS:
                    await message.reply("⏰ Подождите перед следующим чеком.")
                    return
            RATE_LIMITS[user_id] = current_time
        
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, not_found = await find_target(client, message, args)
        
        if not target:
            if not_found:
                await message.reply(f"❌ Пользователь `{not_found}` не найден.")
            else:
                await message.reply("⚠️ Пример: `Чек @username` или ответьте на сообщение.")
            return
        
        guarantor_link = None
        if cursor.execute("SELECT 1 FROM trusted WHERE user_id = ?", (str(target.id),)).fetchone():
            guarantor_link = await get_guarantor_link(client, target.id)

        mentor_link = None
        if is_volunteer(target.id):
            mentor_link = await get_mentor_link(client, target.id)

        text, is_owner_flag, _ = generate_card_text(
            target.id, target.username, target.first_name, 
            guarantor_link, mentor_link
        )
        profile_kb = get_profile_keyboard(target.id, target.username)
        
        if is_owner_flag:
            try:
                await client.send_photo(
                    message.chat.id, 
                    OWNER_PHOTO_PATH, 
                    caption=text, 
                    reply_markup=profile_kb
                )
            except:
                await message.reply(text, reply_markup=profile_kb)
        else:
            await message.reply(text, reply_markup=profile_kb)
    except Exception as e:
        logger.error(f"Ошибка в команде чек: {e}")
        await message.reply("❌ Произошла ошибка при проверке пользователя.")

# Команды добавления/удаления ролей
@app.on_message(filters.regex(r"(?i)^\+президент"))
async def add_president(client, message):
    try:
        if not is_owner(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target and str(target.id).isdigit():
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO presidents (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"👑 **{target.first_name}** назначен Президентом!")
    except Exception as e:
        logger.error(f"Ошибка в команде +президент: {e}")

@app.on_message(filters.regex(r"(?i)^\-президент"))
async def remove_president(client, message):
    try:
        if not is_owner(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target and str(target.id).isdigit():
            if cursor.execute("DELETE FROM presidents WHERE user_id = ?", (str(target.id),)).rowcount > 0:
                conn.commit()
                await fetch_staff_info()
                await message.reply(f"👑 **{target.first_name}** снят с поста Президента.")
            else: 
                await message.reply("ℹ️ Не был Президентом.")
    except Exception as e:
        logger.error(f"Ошибка в команде -президент: {e}")

@app.on_message(filters.regex(r"(?i)^\+директор"))
async def add_director(client, message):
    try:
        if not (is_owner(message.from_user.id, message.from_user.username) or is_president(message.from_user.id)): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO directors (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎯 **{target.first_name}** назначен Директором!")
    except Exception as e:
        logger.error(f"Ошибка в команде +директор: {e}")

@app.on_message(filters.regex(r"(?i)^\-директор"))
async def remove_director(client, message):
    try:
        if not (is_owner(message.from_user.id, message.from_user.username) or is_president(message.from_user.id)): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM directors WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎯 **{target.first_name}** снят с Директора.")
    except Exception as e:
        logger.error(f"Ошибка в команде -директор: {e}")

@app.on_message(filters.regex(r"(?i)^\+кодер"))
async def add_coder(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO coders (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"💻 **{target.first_name}** назначен Кодером!")
    except Exception as e:
        logger.error(f"Ошибка в команде +кодер: {e}")

@app.on_message(filters.regex(r"(?i)^\-кодер"))
async def remove_coder(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM coders WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"💻 **{target.first_name}** снят с Кодера.")
    except Exception as e:
        logger.error(f"Ошибка в команде -кодер: {e}")

@app.on_message(filters.regex(r"(?i)^\+дизайнер"))
async def add_designer(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO designers (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎨 **{target.first_name}** назначен Дизайнером!")
    except Exception as e:
        logger.error(f"Ошибка в команде +дизайнер: {e}")

@app.on_message(filters.regex(r"(?i)^\-дизайнер"))
async def remove_designer(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM designers WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎨 **{target.first_name}** снят с Дизайнера.")
    except Exception as e:
        logger.error(f"Ошибка в команде -дизайнер: {e}")

@app.on_message(filters.regex(r"(?i)^\+гарант"))
async def add_guarantor(client, message):
    try:
        if not (is_owner(message.from_user.id, message.from_user.username) or is_president(message.from_user.id)): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO admins (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🛡 **{target.first_name}** назначен Гарантом!")
    except Exception as e:
        logger.error(f"Ошибка в команде +гарант: {e}")

@app.on_message(filters.regex(r"(?i)^\-гарант"))
async def remove_guarantor(client, message):
    try:
        if not (is_owner(message.from_user.id, message.from_user.username) or is_president(message.from_user.id)): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🛡 **{target.first_name}** снят с Гаранта.")
    except Exception as e:
        logger.error(f"Ошибка в команде -гарант: {e}")

@app.on_message(filters.regex(r"(?i)^\+сотрудник"))
async def add_employee(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO employees (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"💼 **{target.first_name}** назначен Сотрудником!")
    except Exception as e:
        logger.error(f"Ошибка в команде +сотрудник: {e}")

@app.on_message(filters.regex(r"(?i)^\-сотрудник"))
async def remove_employee(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM employees WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"💼 **{target.first_name}** снят с Сотрудника.")
    except Exception as e:
        logger.error(f"Ошибка в команде -сотрудник: {e}")

@app.on_message(filters.regex(r"(?i)^\+модератор"))
async def add_moderator(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO moderators (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🔨 **{target.first_name}** назначен Модератором!")
    except Exception as e:
        logger.error(f"Ошибка в команде +модератор: {e}")

@app.on_message(filters.regex(r"(?i)^\-модератор"))
async def remove_moderator(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM moderators WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🔨 **{target.first_name}** снят с Модератора.")
    except Exception as e:
        logger.error(f"Ошибка в команде -модератор: {e}")

@app.on_message(filters.regex(r"(?i)^(\+волонтер|\+стажер|\/volunteer)"))
async def add_volunteer(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            remove_all_staff_roles(target.id)
            cursor.execute("INSERT OR REPLACE INTO volunteers (user_id) VALUES (?)", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎩 **{target.first_name}** назначен Волонтером!")
    except Exception as e:
        logger.error(f"Ошибка в команде +волонтер: {e}")

@app.on_message(filters.regex(r"(?i)^(\-волонтер|\-стажер)"))
async def remove_volunteer(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            cursor.execute("DELETE FROM volunteers WHERE user_id = ?", (str(target.id),))
            conn.commit()
            await fetch_staff_info()
            await message.reply(f"🎩 **{target.first_name}** снят с поста.")
    except Exception as e:
        logger.error(f"Ошибка в команде -волонтер: {e}")

# Команды доверия и репутации
@app.on_message(filters.command("trust") | filters.regex(r"(?i)^/траст"))
async def add_trust(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        
        sender_id = str(message.from_user.id)
        
        if target and str(target.id).isdigit():
            cursor.execute("INSERT OR REPLACE INTO trusted (user_id, guarantor_id) VALUES (?, ?)", 
                           (str(target.id), sender_id))
            conn.commit()
            await message.reply(f"💠 **{target.first_name}** получил статус 'Проверен гарантом'!")
    except Exception as e:
        logger.error(f"Ошибка в команде trust: {e}")

@app.on_message(filters.regex(r"(?i)^\-траст"))
async def remove_trust(client, message):
    try:
        if not is_full_staff(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            if cursor.execute("DELETE FROM trusted WHERE user_id = ?", (str(target.id),)).rowcount > 0:
                conn.commit()
                await message.reply(f"💠 **{target.first_name}** лишен статуса 'Проверен гарантом'.")
            else: 
                await message.reply("ℹ️ У пользователя не было этого статуса.")
    except Exception as e:
        logger.error(f"Ошибка в команде -траст: {e}")

@app.on_message(filters.regex(r"(?i)^\+спасибо") | filters.regex(r"(?i)^\+rep"))
async def add_rep(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        target, _ = await find_target(client, message, args)
        if target:
            if target.id == message.from_user.id: 
                return
            cursor.execute("""
                INSERT INTO reputation (user_id, count) VALUES (?, 1) 
                ON CONFLICT(user_id) DO UPDATE SET count = count + 1
            """, (str(target.id),))
            conn.commit()
            await message.reply(f"🤝 Репутация **{target.first_name}** повышена!")
    except Exception as e:
        logger.error(f"Ошибка в команде +rep: {e}")

# Команды скама
@app.on_message(filters.command(["scam", "скам"]))
async def add_scam_cmd(client, message):
    try:
        if not (can_moderate(message.from_user.id, message.from_user.username) or is_volunteer(message.from_user.id)):
            return
        
        if len(message.command) < 4:
            await message.reply("⚠️ Пример: `/scam @username Причина Ссылка`")
            return
        
        target_str = message.command[1]
        target, not_found = await find_target(client, message, target_str)
        
        if not target or not str(target.id).isdigit():
            if not_found:
                await message.reply(f"❌ Пользователь `{not_found}` не найден.")
            else:
                await message.reply("❌ Пользователь не найден.")
            return
        
        if is_any_staff(target.id, target.username):
            await message.reply("❌ Нельзя скам сотрудника.")
            return
        
        proof_link = message.command[-1]
        reason = " ".join(message.command[2:-1])
        save_id = str(target.id)
        PENDING_SCAM_ENTRIES[message.from_user.id] = [save_id, reason, proof_link]
        await message.reply(f"✅ Заносим **{target.first_name}**. Выберите рейтинг:", reply_markup=get_scam_rating_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в команде scam: {e}")
        await message.reply("❌ Произошла ошибка при выполнении команды.")

@app.on_message(filters.command("unscam"))
async def un_scam_cmd(client, message):
    try:
        if not can_moderate(message.from_user.id, message.from_user.username): 
            return
        
        if len(message.command) < 2:
            await message.reply("⚠️ Пример: `/unscam @username`")
            return
        
        target_str = message.command[1]
        target, not_found = await find_target(client, message, target_str)
        
        if not target: 
            if not_found:
                await message.reply(f"❌ Пользователь `{not_found}` не найден.")
            return
        
        save_id = str(target.id)
        if cursor.execute("DELETE FROM scammers WHERE user_id = ?", (save_id,)).rowcount > 0:
            conn.commit()
            await message.reply(f"✅ **{target_str}** удален из базы скамеров.")
        else: 
            await message.reply("ℹ️ Пользователь не был в базе скамеров.")
    except Exception as e:
        logger.error(f"Ошибка в команде unscam: {e}")

# Общие сообщения
@app.on_message(filters.text & filters.private & ~filters.regex(r"^\/"))
async def general_private_message_handler(client, message):
    """Обработчик общих сообщений в личке"""
    try:
        if len(message.text) > 50: 
            return
        if re.match(r"(?i)^(чек|check)\b", message.text.split()[0]): 
            return
        await message.reply("Нажми /start для начала работы.", reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в обработчике личных сообщений: {e}")

# Запуск бота
async def main():
    """Основная функция запуска"""
    try:
        print("🚀 Бот SHARK запускается...")
        
        await app.start()
        
        # Загружаем информацию о персонале
        await fetch_staff_info()
        
        print("🚀 Бот SHARK запущен и готов к работе!")
        print("Владельцы:")
        for name, data in OWNERS.items():
            print(f"  - {name} (ID: {data['id']}, Username: {data['username'] or 'нет'})")
        
        # Ожидаем сообщения
        await idle()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        print(f"❌ Ошибка запуска: {e}")
    finally:
        try:
            await app.stop()
        except:
            pass
        conn.close()
        print("✅ Ресурсы освобождены.")

if __name__ == "__main__":
    # Для корректной работы в различных окружениях
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена.")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
