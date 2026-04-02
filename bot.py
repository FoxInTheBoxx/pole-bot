import os
import pandas as pd
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# ⚙️ НАСТРОЙКИ
# =========================

TOKEN = "8724044213:AAHzltZdQnaSn_ou30Ohbd8v2rDtPpyuG1Q"
ADMIN_ID = 705855212  # ← ВСТАВЬ СВОЙ ID
ALLOWED_USERS = [ADMIN_ID]

# файл с программой
df = pd.read_excel("fox_pole_pro.xlsx")


# =========================
# 📅 ОПРЕДЕЛЕНИЕ НЕДЕЛИ
# =========================
def get_current_week():
    day = datetime.now().day
    return f"Неделя {min((day-1)//7 + 1, 4)}"


# =========================
# 📊 ПОЛУЧЕНИЕ ПРОГРАММЫ
# =========================
def get_program():
    week = get_current_week()
    rows = df[df["Неделя"] == week]

    program = {}

    program["Сила"] = (
        rows["Сила"]["Фит 1"].dropna().tolist(),
        rows["Сила"]["Фит 2"].dropna().tolist()
    )

    program["Гибкость"] = (
        rows["Гибкость"]["Фит 1"].dropna().tolist(),
        rows["Гибкость"]["Фит 2"].dropna().tolist()
    )

    program["Крутки"] = (
        rows["Крутки"]["Фит 1"].dropna().tolist(),
        rows["Крутки"]["Фит 2"].dropna().tolist()
    )

    program["Подкачка"] = (
        rows["Подкачка"]["Фит 1"].dropna().tolist(),
        rows["Подкачка"]["Фит 2"].dropna().tolist()
    )

    return program, week


# =========================
# 🧾 ФОРМАТ ТЕКСТА
# =========================
def format_category(category, f1, f2):
    text = f"<b>{category.upper()}</b>\n\n"

    text += "<b>Фит 1:</b>\n"
    for el in f1:
        text += f"— {el}\n"

    text += "\n<b>Фит 2:</b>\n"
    for el in f2:
        text += f"— {el}\n"

    return text


# =========================
# 📱 МЕНЮ
# =========================
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("📅 Программа недели", callback_data="week")],
        [InlineKeyboardButton("ℹ️ О программе", callback_data="info")]
    ]

    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("👑 Админ", callback_data="admin")])

    return InlineKeyboardMarkup(buttons)


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])


# =========================
# 🔐 ПРОВЕРКА ДОСТУПА
# =========================
def is_allowed(user_id):
    return user_id in ALLOWED_USERS


# =========================
# 🤖 СТАРТ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_allowed(user_id):
        await update.message.reply_text("⛔ У тебя нет доступа")
        return

    await update.message.reply_text(
        "Добро пожаловать в программу 💪",
        reply_markup=main_menu(user_id)
    )


# =========================
# 🔘 ОБРАБОТКА КНОПОК
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_allowed(user_id):
        await query.answer("Нет доступа")
        return

    await query.answer()
    data = query.data

    # =========================
    # 📅 МЕНЮ НЕДЕЛИ
    # =========================
    if data == "week":
        _, week = get_program()

        await query.edit_message_text(
            f"📅 <b>{week}</b>\n\nВыбери категорию:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💪 Сила", callback_data="cat_Сила")],
                [InlineKeyboardButton("🤸 Гибкость", callback_data="cat_Гибкость")],
                [InlineKeyboardButton("🔄 Крутки", callback_data="cat_Крутки")],
                [InlineKeyboardButton("🧱 Подкачка", callback_data="cat_Подкачка")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    # =========================
    # 📌 КАРТОЧКА КАТЕГОРИИ
    # =========================
    elif data.startswith("cat_"):
        category = data.split("_")[1]

        program, week = get_program()
        f1, f2 = program[category]

        await query.edit_message_text(
            format_category(category, f1, f2),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Назад", callback_data="week")],
                [InlineKeyboardButton("🔄 Обновить", callback_data=f"cat_{category}")]
            ])
        )

    # =========================
    # ℹ️ ИНФО
    # =========================
    elif data == "info":
        await query.edit_message_text(
            "Программа обновляется каждую неделю 📆",
            reply_markup=back_button()
        )

    # =========================
    # ⬅ НАЗАД
    # =========================
    elif data == "back":
        await query.edit_message_text(
            "Главное меню",
            reply_markup=main_menu(user_id)
        )

    # =========================
    # 👑 АДМИН
    # =========================
    elif data == "admin" and user_id == ADMIN_ID:
        users = "\n".join(str(u) for u in ALLOWED_USERS)

        await query.edit_message_text(
            f"👑 Админ-панель\n\nПользователи:\n{users}",
            reply_markup=back_button()
        )


# =========================
# 🚀 ЗАПУСК
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
