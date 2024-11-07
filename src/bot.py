import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers import register_all_handlers
from middlewares import register_all_middlewares

logger = logging.getLogger(__name__)

async def set_commands(bot: Bot, config):
    # Базовые команды для всех пользователей
    basic_commands = [
        types.BotCommand("start", "Запустить бота")
    ]
    
    # Дополнительные команды для админа
    admin_commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("users", "Список всех пользователей"),
        types.BotCommand("pending", "Пользователи в ожидании")
    ]
    
    # Установка обычных команд для всех пользователей
    await bot.set_my_commands(basic_commands)
    
    # Установка расширенных команд для админа
    await bot.set_my_commands(
        admin_commands,
        scope=types.BotCommandScopeChat(chat_id=int(config.tg_bot.admin_id))
    )

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация бота и диспетчера
    storage = MemoryStorage()
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher(bot, storage=storage)

    # Инициализация базы данных
    db = Database()
    await db.create_tables()
    
    # Регистрация middleware и обработчиков
    register_all_middlewares(dp, db)
    register_all_handlers(dp)

    # Установка команд бота
    await set_commands(bot, config)

    # Запуск бота
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")