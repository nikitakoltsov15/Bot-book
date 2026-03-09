import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

# ==== Настройки ====
TOKEN = os.environ.get("BOT_TOKEN")      # токен из переменной окружения
ADMIN_ID = int(os.environ.get("ADMIN_ID"))  # твой Telegram ID
PDF_FOLDER = "pdfs"

# ==== Папка для PDF ====
os.makedirs(PDF_FOLDER, exist_ok=True)

# ==== Инициализация бота ====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ==== База данных ====
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    file_path TEXT
)
""")
conn.commit()

# ==== Главное меню пользователей ====
def get_books_keyboard():
    cursor.execute("SELECT id, name FROM books")
    books = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for book_id, name in books:
        keyboard.add(InlineKeyboardButton(text=name, callback_data=f"get_{book_id}"))
    return keyboard

# ==== Админ-панель ====
def admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton(text="➕ Добавить PDF", callback_data="admin_addpdf"))
    return keyboard

# ==== /start ====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Панель администратора:", reply_markup=admin_panel_keyboard())
    else:
        await message.reply("Выберите книгу:", reply_markup=get_books_keyboard())

# ==== Обработка нажатий кнопок ====
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    if data.startswith("get_"):
        book_id = int(data.split("_")[1])
        cursor.execute("SELECT file_path FROM books WHERE id = ?", (book_id,))
        result = cursor.fetchone()
        if result:
            await bot.send_document(callback_query.from_user.id, InputFile(result[0]))
        await bot.answer_callback_query(callback_query.id)
    elif data == "admin_addpdf":
        await bot.send_message(callback_query.from_user.id,
                               "Пришлите PDF в ответ на это сообщение и напишите команду:\n"
                               "/addpdf Название книги")
        await bot.answer_callback_query(callback_query.id)

# ==== Добавление PDF (только админ) ====
@dp.message_handler(commands=['addpdf'])
async def add_pdf(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("У вас нет прав на добавление PDF.")
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("Ответьте на сообщение с PDF файлом командой /addpdf Название книги")
        return
    pdf = message.reply_to_message.document
    name = " ".join(message.text.split()[1:])
    if not name:
        await message.reply("Укажите название книги после команды.")
        return
    file_path = os.path.join(PDF_FOLDER, pdf.file_name)
    await pdf.download(destination_file=file_path)
    cursor.execute("INSERT OR IGNORE INTO books(name, file_path) VALUES(?, ?)", (name, file_path))
    conn.commit()
    await message.reply(f"PDF '{name}' успешно добавлен!")

# ==== /list ====
@dp.message_handler(commands=['list'])
async def list_pdfs(message: types.Message):
    await message.reply("Выберите книгу:", reply_markup=get_books_keyboard())

# ==== Запуск бота ====
if __name__ == "__main__":
    print("Бот с кнопками запущен...")
    executor.start_polling(dp, skip_updates=True)
