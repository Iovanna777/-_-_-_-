import asyncio
import base64
import os
import requests
import time
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, BotCommand
from dotenv import load_dotenv

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    encoding="utf-8",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logger.info("Бот запущен")

# Загрузка переменных из .env
load_dotenv()

# Получение токенов и catalog_id из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")
YANDEX_CATALOG_ID = os.getenv("YANDEX_CATALOG_ID")

logger.info(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not set'}")
logger.info(f"YANDEX_API_TOKEN: {'Set' if YANDEX_API_TOKEN else 'Not set'}")
logger.info(f"YANDEX_CATALOG_ID: {'Set' if YANDEX_CATALOG_ID else 'Not set'}")

if not all([TELEGRAM_BOT_TOKEN, YANDEX_API_TOKEN, YANDEX_CATALOG_ID]):
    logger.error("Не все необходимые переменные окружения заданы в .env")
    raise ValueError("Не все необходимые переменные окружения заданы в .env")

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)
logger.info("Бот и диспетчер инициализированы")

# Определение состояний для FSM
class ImageGeneration(StatesGroup):
    waiting_for_description = State()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    await message.answer("Привет от старых штиблет! Жми /pic, чтобы создать изображение. Качество не гарантирую. Трах тибидох!")

# Обработчик команды /pic
@dp.message(Command("pic"))
async def cmd_picture(message: types.Message, state: FSMContext):
    logger.info(f"Получена команда /pic от пользователя {message.from_user.id}")
    await message.answer("Введите описание для изображения:")
    await state.set_state(ImageGeneration.waiting_for_description)

# Обработчик ввода описания изображения
@dp.message(ImageGeneration.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text
    logger.info(f"Получено описание изображения: {description}")
    await message.answer("Генерирую изображение, пожалуйста, подождите...")

    image_path = None
    try:
        # Генерируем случайный seed от 1 до 1,000,000
        seed = random.randint(1, 1000000)

        # Параметры для Yandex Cloud API
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync"
        headers = {
            "Authorization": f"Bearer {YANDEX_API_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"art://{YANDEX_CATALOG_ID}/yandex-art/latest",
            "generationOptions": {
                "seed": seed,
                "aspectRatio": {
                    "widthRatio": 2,
                    "heightRatio": 1
                }
            },
            "messages": [
                {
                    "weight": 1,
                    "text": description
                }
            ]
        }

        logger.info("Отправка запроса на генерацию изображения...")
        # Отправка запроса на генерацию
        response = requests.post(url, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        request_id = response.json()['id']
        logger.info(f"Запрос на генерация отправлен, request_id: {request_id}")

        # Ожидание результата
        max_wait_time = 60
        start_time = time.time()
        url = f"https://llm.api.cloud.yandex.net/operations/{request_id}"

        while time.time() - start_time < max_wait_time:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            result = response.json()
            if result.get('done', False):
                if 'response' in result and 'image' in result['response']:
                    image_base64 = result['response']['image']
                    image_data = base64.b64decode(image_base64)

                    # Сохранение изображения
                    image_path = f"image_{request_id}.jpeg"
                    with open(image_path, 'wb') as file:
                        file.write(image_data)

                    # Отправка изображения пользователю
                    photo = FSInputFile(image_path)
                    await message.answer_photo(photo=photo, caption=f"Вот ваше изображение! (Seed: {seed})")
                    logger.info("Изображение успешно отправлено пользователю")

                    break
                else:
                    await message.answer("Ошибка: Ответ не содержит изображения")
                    logger.error("Ответ от Yandex API не содержит изображения")
                    break
            else:
                await asyncio.sleep(5)
        else:
            await message.answer("Превышено время ожидания результата")
            logger.error("Превышено время ожидания результата от Yandex API")

    except requests.RequestException as e:
        await message.answer(f"Ошибка запроса к API: {e}")
        logger.error(f"Ошибка запроса к Yandex API: {e}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
        logger.error(f"Произошла ошибка: {e}")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Временный файл {image_path} удалён")
        await state.clear()
        logger.info("Состояние FSM очищено")

# Установка команд бота (для синхронизации с BotFather)
async def set_commands():
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="pic", description="Сгенерировать изображение")
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")

# Запуск бота
async def main():
    logger.info("Запуск polling...")
    try:
        await set_commands()
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске polling: {e}")
        raise
    finally:
        logger.info("Polling остановлен")

if __name__ == "__main__":
    asyncio.run(main())