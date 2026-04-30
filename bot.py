import os
import logging
import threading
import telebot
from telebot import types
from flask import Flask
from dotenv import load_dotenv
from vk_worker import send_to_vk_groups

# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_errors.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# === ПЕРЕМЕННЫЕ ===
TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    logger.critical("TG_TOKEN не найден в переменных окружения")
    raise ValueError("TG_TOKEN не найден")

bot = telebot.TeleBot(TG_TOKEN)
app = Flask(__name__)

# Хранилище состояний пользователей
user_data = {}

# === КЛАВИАТУРЫ ===
def get_start_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Отправить объявление"))
    return kb

def get_finish_photos_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Закончить отправку фото ✅"))
    return kb

def get_confirm_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Готово ☑️"), types.KeyboardButton("Изменить"))
    return kb

# === ОБРАБОТЧИКИ КОМАНД ===
@bot.message_handler(commands=['start', 'auto'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'photos': [], 'text': None}
    logger.info(f"Пользователь {chat_id} запустил бота")
    bot.send_message(
        chat_id,
        "Привет! Чтобы отправить объявление в ВК, нажми на кнопку ниже 👇",
        reply_markup=get_start_kb()
    )

@bot.message_handler(func=lambda m: m.text == "Отправить объявление")
def ask_photo(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'photos': [], 'text': None}
    logger.info(f"Пользователь {chat_id} начал процесс создания объявления")
    bot.send_message(
        chat_id,
        "Отправьте фотографию(ии) вашего объявления (до 10 шт.)",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {'photos': [], 'text': None}
        logger.warning(f"Пользователь {chat_id} отправил фото без инициализации")
    if len(user_data[chat_id]['photos']) < 10:
        file_id = message.photo[-1].file_id
        user_data[chat_id]['photos'].append(file_id)
        logger.info(f"Пользователь {chat_id} добавил фото {len(user_data[chat_id]['photos'])}/10")
        bot.send_message(
            chat_id,
            f"Фото получено ({len(user_data[chat_id]['photos'])}/10). Можете отправить еще или нажмите кнопку 👇",
            reply_markup=get_finish_photos_kb()
        )
    else:
        bot.send_message(chat_id, "Достигнут лимит 10 фото. Нажмите кнопку 👇", reply_markup=get_finish_photos_kb())

@bot.message_handler(func=lambda m: m.text == "Закончить отправку фото ✅")
def finish_photos_step(message):
    chat_id = message.chat.id
    if chat_id not in user_data or not user_data[chat_id]['photos']:
        bot.send_message(chat_id, "Вы не отправили ни одного фото!")
        logger.warning(f"Пользователь {chat_id} попытался завершить фото без отправленных фото")
        return
    logger.info(f"Пользователь {chat_id} завершил загрузку фото. Переход к тексту.")
    bot.send_message(chat_id, "Теперь отправьте текст к вашему объявлению", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_text)

def get_text(message):
    chat_id = message.chat.id
    if not message.text:
        bot.send_message(chat_id, "Нужен текст объявления!")
        logger.warning(f"Пользователь {chat_id} не ввел текст")
        bot.register_next_step_handler(message, get_text)
        return
    user_data[chat_id]['text'] = message.text
    logger.info(f"Пользователь {chat_id} добавил текст объявления")
    bot.send_message(
        chat_id,
        "Объявление готово! Вы уверены? Если нужно что-то изменить, нажмите кнопку ниже",
        reply_markup=get_confirm_kb()
    )

@bot.message_handler(func=lambda m: m.text in ["Готово ☑️", "Изменить"])
def confirm_step(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        logger.error(f"Пользователь {chat_id} подтвердил без данных в user_data")
        bot.send_message(chat_id, "Произошла ошибка. Начните заново /start", reply_markup=get_start_kb())
        return

    if message.text == "Изменить":
        logger.info(f"Пользователь {chat_id} решил изменить объявление")
        ask_photo(message)
        return

    logger.info(f"Пользователь {chat_id} подтвердил отправку объявления")
    bot.send_message(chat_id, "Начинаю процесс отправки в ВК... подождите.")

    paths = []
    try:
        data = user_data[chat_id]
        # Скачиваем фото
        for i, photo_id in enumerate(data['photos']):
            try:
                file_info = bot.get_file(photo_id)
                downloaded_file = bot.download_file(file_info.file_path)
                path = f"temp_{chat_id}_{i}.jpg"
                with open(path, 'wb') as f:
                    f.write(downloaded_file)
                paths.append(path)
                logger.info(f"Фото {i} для {chat_id} сохранено как {path}")
            except Exception as e:
                logger.error(f"Ошибка скачивания фото {i} для {chat_id}: {e}")
                raise

        # Отправка в VK
        report = send_to_vk_groups(data['text'], paths)
        logger.info(f"Результат отправки для {chat_id}: {report}")

        # Удаляем временные файлы
        for p in paths:
            if os.path.exists(p):
                os.remove(p)
                logger.info(f"Удалён временный файл {p}")

        bot.send_message(chat_id, report, reply_markup=get_start_kb())
        user_data[chat_id] = {'photos': [], 'text': None}

    except Exception as e:
        logger.error(f"Критическая ошибка при отправке объявления от {chat_id}: {e}")
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                    logger.info(f"Удалён временный файл {p} после ошибки")
                except:
                    pass
        bot.send_message(chat_id, f"Критическая ошибка: {e}\nОбратитесь к @Ivanka58", reply_markup=get_start_kb())

# === ФЛАСК ДЛЯ RENDER ===
@app.route('/')
def health():
    return "Bot is alive", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)

# === ЗАПУСК ===
if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Бот запущен и начал поллинг")
    bot.infinity_polling()
