#!/usr/bin/env python3
"""
Простой бот для тестирования без базы данных
"""
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SimpleBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        self._setup_commands()
    
    def _setup_handlers(self):
        """Настройка обработчиков"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def _setup_commands(self):
        """Настройка команд бота для отображения в меню"""
        self.commands = [
            BotCommand("start", "🚀 Начать работу с ботом"),
            BotCommand("help", "❓ Справка по командам")
        ]
    
    async def register_commands(self):
        """Зарегистрировать команды в Telegram"""
        try:
            await self.application.bot.set_my_commands(self.commands)
            logger.info("Команды бота успешно зарегистрированы")
        except Exception as e:
            logger.error(f"Ошибка регистрации команд: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_text = """
Привет! 👋 Я помогу тебе выучить материал по методу Эббингауза.

📈 Кривая забывания Эббингауза показывает, что мы забываем:
• 50% информации через 20 минут
• 70% через день  
• 90% через неделю

Но если повторять материал в определенные интервалы, информация закрепится в долговременной памяти навсегда!

🔬 Интервалы повторений:
📝 Сразу → ⏰ 20-30 мин → 🌆 Вечером → 📅 +1 день → 📅 +3 дня → 📅 +7 дней → 📅 +14 дней → 📅 +30 дней

💡 В полной версии я буду напоминать о повторениях каждое утро в 07:00!
        """
        
        keyboard = [[InlineKeyboardButton("Ознакомлен ✅", callback_data="acknowledged")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
🔧 Доступные команды:

/start - Начать работу с ботом
/help - Показать эту справку

📝 Как использовать (в полной версии):
1. Отправь мне текст с вопросами/темами, которые изучил
2. Я создам расписание повторений по методу Эббингауза
3. Каждое утро в 07:00 получай напоминания
4. Отмечай результат повторений кнопками ✅/❌

🎯 Цель: закрепить знания в долговременной памяти!

⚠️ Сейчас работает тестовая версия без базы данных.
        """
        await update.message.reply_text(help_text)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "acknowledged":
            await query.edit_message_text(
                "Отлично! 🎉\n\n"
                "Теперь отправь мне любой текст, и я покажу как работает метод Эббингауза!\n\n"
                "📝 Например, напиши: 'Изучил формулы производных'"
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        content = update.message.text.strip()
        
        response = f"""
✅ Материал принят!

📚 Содержимое: {content[:100]}{'...' if len(content) > 100 else ''}

📅 По методу Эббингауза тебе нужно повторить этот материал:

📝 Сейчас (сразу)
⏰ Через 20-30 минут  
🌆 Вечером сегодня
📅 Завтра
📅 Через 3 дня
📅 Через неделю
📅 Через 2 недели
📅 Через месяц

🎯 В полной версии с базой данных я буду автоматически напоминать о каждом повторении!

Попробуй команды:
/start - начать заново
/help - справка
        """
        
        await update.message.reply_text(response)


async def main():
    """Запуск бота"""
    logger.info("Запуск простого тест-бота...")
    
    bot = SimpleBot()
    
    try:
        # Инициализация
        await bot.application.initialize()
        
        # Регистрируем команды бота
        await bot.register_commands()
        
        # Удаляем webhook
        await bot.application.bot.delete_webhook()
        logger.info("Webhook удален, запускаем polling...")
        
        # Запускаем polling
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        logger.info("🤖 Бот запущен! Найди @UchimNavsegdaBot в Telegram и отправь /start")
        logger.info("Нажми Ctrl+C для остановки")
        
        # Ждем
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    finally:
        try:
            await bot.application.updater.stop()
            await bot.application.stop() 
            await bot.application.shutdown()
            logger.info("Бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")


if __name__ == "__main__":
    asyncio.run(main())
