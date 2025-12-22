#!/usr/bin/env python3
"""
Скрипт для локального запуска бота в режиме polling (без webhook)
Удобно для разработки и тестирования
"""
import asyncio
import logging
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.bot import bot_instance
from app.scheduler import start_scheduler, stop_scheduler
from app.database.connection import sync_engine
from app.database.models import Base

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_tables():
    """Создание таблиц в БД если их нет"""
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


async def main():
    """Основная функция для локального запуска"""
    logger.info("Starting Ebbinghaus Bot in polling mode...")
    
    if not settings.bot_token:
        logger.error("BOT_TOKEN not provided! Set it in .env file or environment variables")
        sys.exit(1)
    
    try:
        # Создаем таблицы
        await create_tables()
        
        # Запускаем планировщик
        await start_scheduler()
        logger.info("Scheduler started")
        
        # Инициализация бота
        await bot_instance.application.initialize()
        
        # Удаляем webhook если был установлен
        await bot_instance.application.bot.delete_webhook()
        logger.info("Webhook deleted, starting polling...")
        
        # Запускаем polling
        await bot_instance.application.start()
        await bot_instance.application.updater.start_polling()
        
        logger.info("Bot is running in polling mode! Press Ctrl+C to stop.")
        
        # Ожидаем сигнал остановки
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        # Очистка ресурсов
        try:
            await bot_instance.application.updater.stop()
            await bot_instance.application.stop()
            await bot_instance.application.shutdown()
            await stop_scheduler()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
