#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправленного функционала
"""
import os
import asyncio
import logging
import sys

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = '8203884714:AAHDI2IimFQHL7-LDUhjNRFkb6hZCvxTe2U'
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/ebbinghaus_db'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['DEBUG'] = 'True'

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bot():
    """Тест бота с фиктивной БД для проверки логики"""
    from app.bot import bot_instance
    
    logger.info("Инициализация бота...")
    
    try:
        # Инициализация
        await bot_instance.application.initialize()
        
        # Удаляем webhook
        await bot_instance.application.bot.delete_webhook()
        logger.info("Webhook удален, запускаем polling...")
        
        # Регистрируем команды
        await bot_instance.register_commands()
        logger.info("Команды зарегистрированы")
        
        # Запускаем polling
        await bot_instance.application.start()
        await bot_instance.application.updater.start_polling()
        
        logger.info("="*50)
        logger.info("БОТ ЗАПУЩЕН!")
        logger.info("Найди @UchimNavsegdaBot в Telegram")
        logger.info("Проверь следующие команды:")
        logger.info("  /start - начать работу")
        logger.info("  /schedule - посмотреть расписание повторений")
        logger.info("  /repetitions - алиас для /schedule")
        logger.info("  /stats - статистика обучения")
        logger.info("  /help - справка")
        logger.info("")
        logger.info("Затем отправь любой текст для создания материала")
        logger.info("И проверь кнопки при получении напоминаний")
        logger.info("="*50)
        logger.info("Нажми Ctrl+C для остановки")
        
        # Ждем
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
    finally:
        try:
            await bot_instance.application.updater.stop()
            await bot_instance.application.stop() 
            await bot_instance.application.shutdown()
            logger.info("Бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot())
