import atexit
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TOKEN
from about_text import about_text
import os
import aiofiles
import json
import random
import string
import logging
import datetime

content_directory = "content"
os.makedirs(content_directory, exist_ok=True)
log_file_path = os.path.join(content_directory, "log.txt")
games_file_path = os.path.join(content_directory, "games.txt")
reviews_file_path = os.path.join(content_directory, "reviews.txt")

logging.basicConfig(level=logging.INFO, filename='content/log.txt', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(TOKEN)
dp = Dispatcher(bot)

WORDS = [
    "молоко",
    "космос",
    "библиотека",
    "программирование",
    "дипломат",
    "виноград",
    "фестиваль",
    "инструмент",
    "чемпионат",
    "метаморфоза",
    "экспедиция",
    "лабиринт",
    "кибернетика",
    "престиж",
    "аквариум",
    "биосфера",
    "галактика",
    "демократия",
    "живопись",
    "зоопарк",
    "изоляция",
    "квант",
    "литература",
    "мифология",
    "нейрон",
    "океан",
    "пирамида",
    "рубрика",
    "симфония",
    "телескоп",
    "философия",
    "хроника",
    "цитадель",
    "шахматы",
    "электричество",
    "юмор",
    "ягода"
]
games = {}
reviews = {}


def log_divider():
    logger.info("__________ Program is finished __________")


atexit.register(log_divider)


def log_message(user, message_text):
    username = f"@{user.username}" if user.username else user.first_name
    logger.info(f"Message from {username}: {message_text}")

async def truncate_log_file(log_file_path, max_lines=1000, leave_lines=500):
    # Подсчет строк в файле
    with open(log_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    lines_count = len(lines)
    if lines_count > max_lines:
        # Оставляем только последние leave_lines строк
        with open(log_file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines[-leave_lines:])

class HangmanGame:
    def __init__(self, secret_word):
        self.secret_word = secret_word.upper()
        self.guessed_letters = set()
        self.attempts = len(secret_word) + 3

    def guess_letter(self, letter):
        letter = letter.upper()
        if letter in self.guessed_letters:
            return "already_guessed"
        elif letter in self.secret_word:
            self.guessed_letters.add(letter)
            return "correct"
        else:
            self.attempts -= 1
            return "incorrect"

    def get_display_word(self):
        return ' '.join(letter if letter in self.guessed_letters else '_' for letter in self.secret_word)

    def is_game_over(self):
        return self.attempts <= 0 or all(letter in self.guessed_letters for letter in self.secret_word)

    def is_victory(self):
        return all(letter in self.guessed_letters for letter in self.secret_word)


def rating_keyboard():
    keyboard = InlineKeyboardMarkup()
    for i in range(1, 6):
        keyboard.add(InlineKeyboardButton(f"{i} ⭐️", callback_data=f"rate_{i}"))
    return keyboard


def generate_game_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Сдаться", callback_data="surrender"))
    keyboard.add(InlineKeyboardButton("Помощь", callback_data="help"))
    return keyboard


async def save_games_async():
    games_data = [game_code + ":" + json.dumps({'user_id': game_info['user_id'],
                                                'secret_word': game_info['game'].secret_word,
                                                'guessed_letters': list(game_info['game'].guessed_letters),
                                                'attempts': game_info['game'].attempts,
                                                'finished': game_info['game'].is_game_over()}, ensure_ascii=False)
                  for game_code, game_info in games.items()]
    async with aiofiles.open(games_file_path, 'w', encoding='utf-8') as file:
        await file.write('\n'.join(games_data))


# Функция для загрузки сохраненных игр из файла
def load_games():
    try:
        with open(games_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                game_code, json_data = line.strip().split(':', 1)
                game_info = json.loads(json_data)
                loaded_game = HangmanGame(game_info['secret_word'])
                loaded_game.guessed_letters = set(game_info['guessed_letters'])
                loaded_game.attempts = game_info['attempts']
                # Добавьте loaded_game.finished если нужно обрабатывать завершенные игры
                games[game_code] = {'game': loaded_game, 'user_id': game_info['user_id']}
    except FileNotFoundError:
        pass  # Если файл не найден, пропускаем загрузку


# Обработчик команды /review
@dp.message_handler(commands=['review'])
async def review_command(message: types.Message):
    log_message(message.from_user, message.text)
    await message.answer("Оцените бота от 1 до 5 звезд:", reply_markup=rating_keyboard())


# Обработчик команды /surrender
@dp.callback_query_handler(lambda c: c.data == 'surrender')
async def process_surrender(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    game_code = next((code for code, game in games.items() if game['user_id'] == user_id), None)
    if game_code:
        game = games[game_code]
        await bot.send_message(user_id,
                               f"Вы сдались. Правильное слово было: `{game['game'].secret_word}`. Не отчаивайтесь и попробуйте снова! /start для новой игры.",
                               parse_mode='Markdown')
        del games[game_code]  # Удаление игры после сдачи
    else:
        await bot.send_message(user_id, "Кажется, у вас нет активных игр. Используйте /start, чтобы начать новую игру.")
    await bot.answer_callback_query(callback_query.id)


# Обработчик выбора рейтинга
@dp.callback_query_handler(lambda c: c.data.startswith('rate_'))
async def process_rating(callback_query: types.CallbackQuery):
    rate = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id  # Используем user_id для ключа в reviews
    username = f"@{callback_query.from_user.username}" if callback_query.from_user.username else callback_query.from_user.first_name
    reviews[user_id] = {'rate': rate, 'text': None,
                        'username': username}  # Сохраняем username здесь для последующего использования
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user_id, "Спасибо за вашу оценку! Напишите, пожалуйста, ваш отзыв.")


@dp.message_handler(lambda message: message.from_user.id in reviews and reviews[message.from_user.id]['text'] is None)
async def handle_review_text(message: types.Message):
    user_id = message.from_user.id
    review_info = reviews[user_id]
    review_info['text'] = message.text
    try:
        with open(reviews_file_path, 'a', encoding='utf-8') as file:
            file.write(
                f"{str(datetime.datetime.now())[:-7]} - UserID: {review_info['username']}, Rating: {review_info['rate']}, Review: {message.text}\n")
        await message.answer("Ваш отзыв успешно сохранен! Спасибо за обратную связь.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении отзыва: {e}")
        await message.answer("Произошла ошибка при сохранении вашего отзыва. Пожалуйста, попробуйте снова.")


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    log_message(message.from_user, message.text)
    help_text = ("Команды бота:\n"
                 "/start - начать новую игру\n"
                 "/setword - загадать слово для друга\n"
                 "/social - связаться с автором бота\n"
                 "/review - оставить отзыв\n"
                 "/about - о боте\n"
                 "/support - поддержать проект пожертвованием\n"
                 "/help - показать эту справку\n"
                 "Чтобы сделать предположение, отправьте код игры и букву или слово (например, ABCDE питон).")
    await message.reply(help_text)


@dp.message_handler(commands=['start', 'restart'])
async def start_game(message: types.Message):
    user_id = message.from_user.id
    game_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    secret_word = random.choice(WORDS)
    games[game_code] = {'game': HangmanGame(secret_word), 'user_id': user_id}
    await save_games_async()
    await message.reply(
        f"Игра 'Виселица' началась! Угадайте букву, отправив ее. Ваш код игры: `{game_code}`. У вас {len(secret_word) + 3} попыток. Используйте кнопку ниже, чтобы сдаться.",
        parse_mode='Markdown', reply_markup=generate_game_keyboard())


@dp.message_handler(commands=['about'])
async def about_command(message: types.Message):
    await message.answer(about_text, parse_mode='Markdown')


@dp.message_handler(commands=['setword'])
async def set_word(message: types.Message):
    log_message(message.from_user, message.text)
    args = message.get_args().split()
    if len(args) != 1:
        await message.reply("Пожалуйста, используйте команду в формате: /setword <слово>")
        return
    secret_word = args[0]
    if not secret_word.isalpha():
        await message.reply("Слово должно состоять только из букв.")
        return
    user_id = message.from_user.id
    game_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    games[game_code] = {'game': HangmanGame(secret_word), 'user_id': user_id}  # Исправление здесь
    await save_games_async()  # Убедитесь, что это асинхронный вызов в асинхронной функции
    await message.reply(
        f"Слово для игры установлено. Код игры: `{game_code}`. Используйте этот код для игры. У вас {len(secret_word) + 3} попыток.",
        parse_mode='Markdown', reply_markup=generate_game_keyboard())


@dp.callback_query_handler(lambda c: c.data == 'set_word')
async def process_set_word_callback_query(callback_query: types.CallbackQuery):
    log_message(callback_query.from_user, callback_query.data)
    await callback_query.message.reply("Отправьте слово в формате /setword <слово>")


@dp.callback_query_handler(lambda c: c.data == 'help')
async def process_help_callback_query(callback_query: types.CallbackQuery):
    log_message(callback_query.from_user, callback_query.data)
    await help_command(callback_query.message)


@dp.message_handler(commands=['support'])
async def support_command(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Поддержать", url="https://www.donationalerts.com/r/underkassq"))
    await message.reply(
        "Если вы хотите поддержать мою работу, не стесняйтесь делать пожертвования. Любая сумма помогает и очень ценится!",
        reply_markup=keyboard)


@dp.message_handler(commands=['social'])
async def social_command(message: types.Message):
    log_message(message.from_user, message.text)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Telegram", url="https://t.me/swizzy_ed"))
    keyboard.add(InlineKeyboardButton("Steam", url="https://steamcommunity.com/profiles/76561199070099207/"))
    keyboard.add(InlineKeyboardButton("Github", url="https://github.com/megafortniter49"))
    await message.reply("Связаться с автором бота:", reply_markup=keyboard)


async def process_guess_logic(game, guess, message, is_word=False):
    if not is_word:
        correct = game.guess_letter(guess)
    else:
        correct = guess.upper() == game.secret_word
        if correct:
            game.guessed_letters = set(game.secret_word)  # Считаем все буквы угаданными
    if correct:
        if game.is_victory():
            await message.answer(f"Поздравляем! Вы угадали слово: `{game.secret_word}`. /start чтобы начать заново.",
                                 parse_mode='Markdown')
            return
    else:
        if game.is_game_over():
            await message.answer(f"Игра окончена! Слово было: `{game.secret_word}`. /start чтобы начать заново.",
                                 parse_mode='Markdown')
            return
    await message.answer(f"{game.get_display_word()} Осталось попыток: {game.attempts}",
                         reply_markup=generate_game_keyboard())


@dp.message_handler()
async def guess_letter(message: types.Message):
    log_message(message.from_user, message.text)
    parts = message.text.strip().upper().split(maxsplit=1)
    if len(parts) == 2:
        game_code, guess = parts
        if game_code in games and games[game_code]['user_id'] == message.from_user.id:
            await save_games_async()
            game = games[game_code]['game']
            if len(guess) == 1:
                guess_result = game.guess_letter(guess)
                if guess_result == "already_guessed":
                    await message.reply(f"Вы уже пытались угадать букву {guess}. Попробуйте другую.")
                elif guess_result == "correct":
                    if game.is_victory():
                        await message.answer(
                            f"Поздравляем! Вы угадали слово: `{game.secret_word}`. /start чтобы начать заново.",
                            parse_mode='Markdown')
                        del games[game_code]
                    else:
                        await message.answer(f"{game.get_display_word()} Осталось попыток: {game.attempts}",
                                             reply_markup=generate_game_keyboard())
                elif guess_result == "incorrect":
                    if game.is_game_over():
                        await message.answer(
                            f"Игра окончена! Слово было: `{game.secret_word}`. /start чтобы начать заново.",
                            parse_mode='Markdown')
                        del games[game_code]
                    else:
                        await message.answer(f"Неверно. Осталось попыток: {game.attempts}",
                                             reply_markup=generate_game_keyboard())
            else:  # Если ввод целого слова
                await process_guess_logic(game, guess, message, is_word=True)
        else:
            await message.reply("Код игры неверный или игра не найдена.")
    else:
        await message.reply("Пожалуйста, отправьте код игры и букву или слово для угадывания (например, ABCDE Б).")

if __name__ == '__main__':
    load_games()
    executor.start_polling(dp, skip_updates=True)
