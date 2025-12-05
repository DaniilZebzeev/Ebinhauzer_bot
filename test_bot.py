#!/usr/bin/env python3
"""
Простой тест бота в режиме polling
"""
import asyncio
import logging
import os
import sys

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.bot import bot_instance
from app.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота в режиме polling"""
    logger.info("Starting bot in polling mode...")
    
    if not settings.bot_token:
        logger.error("BOT_TOKEN not found!")
        return
    
    try:
        # Инициализация
        await bot_instance.application.initialize()
        
        # Удаляем webhook
        await bot_instance.application.bot.delete_webhook()
        logger.info("Webhook deleted")
        
        # Запускаем polling
        await bot_instance.application.start()
        await bot_instance.application.updater.start_polling()
        
        logger.info("Bot is running! Send /start to test. Press Ctrl+C to stop.")
        
        # Ждем
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        try:
            await bot_instance.application.updater.stop()
            await bot_instance.application.stop()
            await bot_instance.application.shutdown()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
