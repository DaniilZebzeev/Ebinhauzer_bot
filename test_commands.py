#!/usr/bin/env python3
"""
Тест конкретных команд бота
"""
import asyncio
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = '8203884714:AAHDI2IimFQHL7-LDUhjNRFkb6hZCvxTe2U'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'  # Используем SQLite для теста
os.environ['DEBUG'] = 'True'

async def test_schedule_command():
    """Тест команды schedule без реального запуска бота"""
    print("=" * 50)
    print("Тестирование команды /schedule")
    print("=" * 50)
    
    # Создаем тестовую команду
    from telegram import Update, User, Message, Chat
    from unittest.mock import AsyncMock, MagicMock
    
    # Мокаем Update объект
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    
    # Создаем контекст
    context = MagicMock()
    
    try:
        # Импортируем бота
        from app.bot import EbbinghausBot
        
        # Создаем экземпляр бота без запуска
        bot = EbbinghausBot()
        
        # Вызываем команду schedule
        await bot.schedule_command(update, context)
        
        # Проверяем, что был вызван reply_text
        if update.message.reply_text.called:
            args = update.message.reply_text.call_args
            if args:
                message = args[0][0] if args[0] else args[1].get('text', '')
                print("✅ Команда /schedule выполнена успешно!")
                print(f"Ответ бота:\n{message[:500]}...")
            else:
                print("✅ Команда выполнена, но без текста ответа")
        else:
            print("❌ Команда не вызвала reply_text")
            
    except Exception as e:
        print(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)

async def test_repetitions_alias():
    """Проверка что /repetitions работает как алиас"""
    print("\nПроверка алиаса /repetitions...")
    
    try:
        from app.bot import EbbinghausBot
        bot = EbbinghausBot()
        
        # Проверяем, что обработчики настроены правильно
        handlers = bot.application.handlers
        
        schedule_handler = None
        repetitions_handler = None
        
        for group in handlers.values():
            for handler in group:
                if hasattr(handler, 'commands'):
                    if 'schedule' in handler.commands:
                        schedule_handler = handler
                    if 'repetitions' in handler.commands:
                        repetitions_handler = handler
        
        if schedule_handler and repetitions_handler:
            # Проверяем, что они указывают на один и тот же метод
            if schedule_handler.callback == repetitions_handler.callback:
                print("✅ /repetitions правильно настроен как алиас для /schedule")
            else:
                print("❌ /repetitions и /schedule указывают на разные методы")
        else:
            print(f"❌ Не найдены обработчики: schedule={schedule_handler is not None}, repetitions={repetitions_handler is not None}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке алиаса: {e}")

async def test_reminder_buttons():
    """Тест обработки кнопок напоминаний"""
    print("\n" + "=" * 50)
    print("Тестирование кнопок напоминаний")
    print("=" * 50)
    
    from telegram import Update, CallbackQuery, User
    from unittest.mock import AsyncMock, MagicMock
    
    # Мокаем CallbackQuery
    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 123456
    query.data = "reminder_success_short_term"
    
    # Мокаем Update
    update = MagicMock(spec=Update)
    update.callback_query = query
    update.effective_user = query.from_user
    
    context = MagicMock()
    
    try:
        from app.bot import EbbinghausBot
        bot = EbbinghausBot()
        
        # Вызываем обработчик callback
        await bot.handle_callback(update, context)
        
        # Проверяем результат
        if query.edit_message_text.called:
            message = query.edit_message_text.call_args[0][0]
            print("✅ Кнопка напоминания обработана!")
            print(f"Ответ: {message[:200]}...")
            
            if "успешно выполнил" in message.lower():
                print("✅ Результат правильно сохранен как успешный")
            else:
                print("⚠️ Проверьте текст ответа")
        else:
            print("❌ Кнопка не вызвала edit_message_text")
            
    except Exception as e:
        print(f"❌ Ошибка при обработке кнопки: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)

async def main():
    """Запуск всех тестов"""
    print("\n🔧 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ БОТА\n")
    
    # Тест команды schedule
    await test_schedule_command()
    
    # Тест алиаса repetitions
    await test_repetitions_alias()
    
    # Тест кнопок напоминаний
    await test_reminder_buttons()
    
    print("\n✅ Все тесты завершены!")
    print("\nДля полного тестирования запустите бота:")
    print("  python simple_bot.py  # без БД")
    print("  python run_local.py   # с БД")

if __name__ == "__main__":
    asyncio.run(main())
