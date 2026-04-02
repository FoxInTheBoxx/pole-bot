import os
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

# =========================
# ⚙️ НАСТРОЙКИ
# =========================
TOKEN = "8724044213:AAHzltZdQnaSn_ou30Ohbd8v2rDtPpyuG1Q"
ADMIN_ID = 705855212

MAX_PLACES = 6
TRAINING_DAY = 3
TRAINING_HOUR = 21

# =========================
# 📊 ЗАГРУЗКА ПРОГРАММЫ
# =========================
df = pd.read_excel("fox_pole_pro.xlsx", header=[0, 1])
df.columns = df.columns.map(lambda x: (str(x[0]).strip(), str(x[1]).strip()))

# =========================
# 📁 БАЗА ЗАПИСИ
# =========================
BOOKINGS_FILE = "bookings.csv"

if not os.path.exists(BOOKINGS_FILE):
    pd.DataFrame(columns=["user_id", "status", "timestamp"]).to_csv(BOOKINGS_FILE, index=False)


def load_bookings():
    df = pd.read_csv(BOOKINGS_FILE)
    if not df.empty:
        df["user_id"] = df["user_id"].astype(str)
    return df


def save_bookings(df):
    df.to_csv(BOOKINGS_FILE, index=False)


# =========================
# 📅 ВРЕМЯ ТРЕНИРОВКИ
# =========================
def get_training_datetime():
    now = datetime.now()
    days_ahead = (TRAINING_DAY - now.weekday()) % 7
    training = now + timedelta(days=days_ahead)
    return training.replace(hour=TRAINING_HOUR, minute=0, second=0)


# =========================
# 📅 НЕДЕЛЯ
# =========================
def get_current_week():
    day = datetime.now().day
    return f"Неделя {min((day-1)//7 + 1, 4)}"


# =========================
# 📊 ПРОГРАММА (FIX)
# =========================
def get_program():
    week = get_current_week()

    # находим колонку "Неделя"
    week_col = [col for col in df.columns if col[0] == "Неделя"][0]

    rows = df[df[week_col] == week]

    def get(cat, fit):
        try:
            return rows[(cat, fit)].dropna().tolist()
        except:
            return []

    return {
        "Фит 1": {
            "Сила": get("Сила", "Фит 1"),
            "Гибкость": get("Гибкость", "Фит 1"),
            "Крутки": get("Крутки", "Фит 1"),
            "Подкачка": get("Подкачка", "Фит 1"),
        },
        "Фит 2": {
            "Сила": get("Сила", "Фит 2"),
            "Гибкость": get("Гибкость", "Фит 2"),
            "Крутки": get("Крутки", "Фит 2"),
            "Подкачка": get("Подкачка", "Фит 2"),
        }
    }, week


def format_program(data):
    text = ""
    for cat, items in data.items():
        text += f"<b>{cat}</b>\n"
        for i in items:
            text += f"— {i}\n"
        text += "\n"
    return text


# =========================
# 📱 МЕНЮ
# =========================
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("📅 Программа недели", callback_data="week")],
        [InlineKeyboardButton("✍️ Написать тренеру", url="https://t.me/@the_fox_on_pole")],
        [InlineKeyboardButton("📍 Записаться на занятие", callback_data="book")],
        [InlineKeyboardButton("ℹ️ О программе", callback_data="info")]
    ]

    df_b = load_bookings()
    user_id_str = str(user_id)

    if user_id_str in df_b["user_id"].values:
        if datetime.now() < get_training_datetime() - timedelta(hours=24):
            buttons.append([InlineKeyboardButton("❌ Выписаться", callback_data="cancel")])

    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("👑 Админ", callback_data="admin")])

    return InlineKeyboardMarkup(buttons)


def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back")]])


# =========================
# 🤖 СТАРТ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать 💪", reply_markup=main_menu(update.effective_user.id))


# =========================
# 🔧 SAFE EDIT (FIX)
# =========================
async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e


# =========================
# 🔘 ОБРАБОТКА
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data

    # =========================
    # ПРОГРАММА
    # =========================
    if data == "week":
        _, week = get_program()

        await safe_edit(query,
            f"<b>{week}</b>\nВыбери:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Фит 1", callback_data="fit1")],
                [InlineKeyboardButton("Фит 2", callback_data="fit2")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    elif data in ["fit1", "fit2"]:
        program, _ = get_program()
        key = "Фит 1" if data == "fit1" else "Фит 2"

        await safe_edit(query,
            format_program(program[key]),
            InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Назад", callback_data="week")]
            ])
        )

    # =========================
    # ЗАПИСЬ (FIX)
    # =========================
    elif data == "book":
        await safe_edit(query,
            "Выбери занятие:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Четверг 21:00", callback_data="thu")],
                [InlineKeyboardButton("Индивидуальное", url="https://t.me/@the_fox_on_pole")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    elif data == "thu":
        df_b = load_bookings()
        user_id_str = str(user_id)

        if user_id_str in df_b["user_id"].values:
            await query.answer("Ты уже записана (o˘◡˘o)", show_alert=True)
            return

        main = df_b[df_b["status"] == "main"]
        status = "main" if len(main) < MAX_PLACES else "queue"

        new = pd.DataFrame([[user_id_str, status, datetime.now()]], columns=df_b.columns)
        df_b = pd.concat([df_b, new])
        save_bookings(df_b)

        if status == "main":
            await safe_edit(query, "Ура! Жду на тренировке ＼(￣▽￣)／", back())
        else:
            pos = len(df_b[df_b["status"] == "queue"])
            await safe_edit(query, f"Ты в очереди №{pos}", back())

    elif data == "cancel":
        df_b = load_bookings()
        df_b = df_b[df_b["user_id"] != str(user_id)]
        save_bookings(df_b)

        await safe_edit(query, "Ты выписана(ಥ﹏ಥ) ", back())

    # =========================
    # АДМИН
    # =========================
    elif data == "admin" and user_id == ADMIN_ID:
        df_b = load_bookings()

        main = df_b[df_b["status"] == "main"]["user_id"].tolist()
        queue = df_b[df_b["status"] == "queue"]["user_id"].tolist()

        text = "👑 Запись:\n\nОсновной:\n"
        text += "\n".join(map(str, main)) or "нет"

        text += "\n\nОчередь:\n"
        text += "\n".join(map(str, queue)) or "нет"

        await safe_edit(query, text, back())

    elif data == "info":
        await safe_edit(query, "Это бот для тренировок у Лизы по цикличной программе 💪", back())

    elif data == "back":
        await safe_edit(query, "Главное меню", main_menu(user_id))


# =========================
# 🚀 ЗАПУСК
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
